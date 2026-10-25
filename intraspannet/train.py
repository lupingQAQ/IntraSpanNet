"""Fine-tuning and reinforcement-learning hooks.

The released checkpoints were produced by a three-stage pipeline that also
depended on a laboratory data layout, which is why the full pipeline is not
shipped. The parts that a user needs in order to adapt the model to their own
labels are shipped here and are stable API:

    * :class:`SFTConfig`            weights for every supervised term
    * :func:`compute_sft_loss`      multi-task supervised loss (stage 2)
    * :func:`compute_rl_loss`       REINFORCE objective on three rewards (stage 3)
    * :class:`Trainer`              minimal step driver for both stages

Both functions take a plain dict of tensors, so the caller keeps ownership of
data loading. Nothing here reads a fixed directory layout.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import torch
import torch.nn.functional as F

from .model import DualHeadClassifier

__all__ = [
    "SFTConfig",
    "RLConfig",
    "compute_sft_loss",
    "compute_rl_loss",
    "Trainer",
]


@dataclass
class SFTConfig:
    """Loss weights for the supervised stage.

    Defaults follow the recipes used for the released arms: ``lda`` of 0 gives
    the S0 variant, ``lda`` above 0 gives the LDA variant, ``hardneg`` above 0
    gives the HN variant.
    """

    w_software: float = 1.0
    w_type: float = 0.5
    w_tier: float = 0.3
    w_malicious: float = 0.3
    w_contrast: float = 0.2
    w_domain: float = 0.1
    lda: float = 0.0
    hardneg: float = 0.0
    hardneg_temp: float = 0.1
    label_smoothing: float = 0.0


@dataclass
class RLConfig:
    """Reward weights for the REINFORCE stage."""

    reward_product: float = 1.0
    reward_type: float = 0.5
    reward_abstain: float = 1.0
    threshold: float = 0.1041
    baseline_decay: float = 0.9
    entropy_bonus: float = 0.0
    baseline: float = field(default=0.0, init=False)


def _logit_adjust(logits: torch.Tensor, prior: torch.Tensor, weight: float) -> torch.Tensor:
    if weight == 0.0:
        return logits
    return logits + weight * torch.log(prior.clamp_min(1e-8)).to(logits.device)


def _supcon_hardneg(proj: torch.Tensor, labels: torch.Tensor, cfg: SFTConfig) -> torch.Tensor:
    """Supervised contrastive loss with extra weight on hard negatives."""
    z = F.normalize(proj, dim=-1)
    sim = z @ z.t() / cfg.hardneg_temp
    n = z.shape[0]
    eye = torch.eye(n, dtype=torch.bool, device=z.device)
    pos = labels[:, None].eq(labels[None, :]) & ~eye
    if not pos.any():
        return z.sum() * 0.0
    log_prob = sim - torch.logsumexp(sim.masked_fill(eye, float("-inf")), dim=1, keepdim=True)
    weights = torch.ones_like(sim)
    if cfg.hardneg > 0:
        # negatives that are already close receive the extra weight
        neg = ~pos & ~eye
        weights = torch.where(neg, 1.0 + cfg.hardneg * sim.softmax(dim=1), weights)
    mask = pos.float() * weights
    return -(log_prob * mask).sum() / mask.sum().clamp_min(1.0)


def compute_sft_loss(
    model: DualHeadClassifier,
    batch: dict[str, torch.Tensor],
    cfg: SFTConfig | None = None,
    class_prior: torch.Tensor | None = None,
    grl_alpha: float = 0.0,
) -> dict[str, torch.Tensor]:
    """One supervised step (stage 2).

    ``batch`` keys: ``x`` (B, 1600 long), ``y_software``, ``y_type``,
    ``y_tier``, ``y_malicious``, and optionally ``y_domain``.
    ``class_prior`` is the training-set frequency per product class; it is only
    used when ``cfg.lda > 0``.
    """
    cfg = cfg or SFTConfig()
    out = model(batch["x"], grl_alpha=grl_alpha)

    sw = _logit_adjust(out["software"], class_prior, cfg.lda) if class_prior is not None else out["software"]

    terms = {
        "software": F.cross_entropy(sw, batch["y_software"], label_smoothing=cfg.label_smoothing),
        "type": F.cross_entropy(out["type_"], batch["y_type"], label_smoothing=cfg.label_smoothing),
        "tier": F.cross_entropy(out["tier"], batch["y_tier"], label_smoothing=cfg.label_smoothing),
        "malicious": F.cross_entropy(out["malicious"], batch["y_malicious"], label_smoothing=cfg.label_smoothing),
        "contrast": _supcon_hardneg(out["projection"], batch["y_software"], cfg),
    }
    total = (
        cfg.w_software * terms["software"]
        + cfg.w_type * terms["type"]
        + cfg.w_tier * terms["tier"]
        + cfg.w_malicious * terms["malicious"]
        + cfg.w_contrast * terms["contrast"]
    )
    if grl_alpha > 0 and "domain" in out and "y_domain" in batch:
        terms["domain"] = F.cross_entropy(out["domain"], batch["y_domain"])
        total = total + cfg.w_domain * terms["domain"]

    terms["total"] = total
    return terms


def compute_rl_loss(
    model: DualHeadClassifier,
    batch: dict[str, torch.Tensor],
    cfg: RLConfig | None = None,
    prototypes: torch.Tensor | None = None,
) -> dict[str, torch.Tensor]:
    """One REINFORCE step (stage 3).

    The policy is the product softmax. Reward is the sum of three terms:
    correct product, correct type, and an abstain bonus when the prototype
    distance exceeds the threshold on a sample the model would otherwise label.
    A running mean serves as the baseline.
    """
    cfg = cfg or RLConfig()
    out = model(batch["x"])

    logits = out["software"]
    dist = F.softmax(logits, dim=-1)
    log_dist = F.log_softmax(logits, dim=-1)

    with torch.no_grad():
        action = torch.multinomial(dist, 1).squeeze(1)
        reward = cfg.reward_product * action.eq(batch["y_software"]).float()
        reward = reward + cfg.reward_type * out["type_"].argmax(-1).eq(batch["y_type"]).float()
        if prototypes is not None:
            feat = F.normalize(out["features"], dim=-1)
            d = 1.0 - (feat @ prototypes.t()).max(dim=-1).values
            reward = reward + cfg.reward_abstain * d.gt(cfg.threshold).float()

        cfg.baseline = cfg.baseline_decay * cfg.baseline + (1 - cfg.baseline_decay) * reward.mean().item()
        advantage = reward - cfg.baseline

    logp = log_dist.gather(1, action[:, None]).squeeze(1)
    loss = -(advantage * logp).mean()
    if cfg.entropy_bonus:
        entropy = -(dist * log_dist).sum(-1).mean()
        loss = loss - cfg.entropy_bonus * entropy
    return {"total": loss, "reward": reward.mean()}


class Trainer:
    """Minimal step driver. The caller owns the optimizer and the data loader."""

    def __init__(self, model: DualHeadClassifier, optimizer: torch.optim.Optimizer | None = None):
        self.model = model
        self.optimizer = optimizer or torch.optim.AdamW(model.parameters(), lr=1e-4)

    def _apply(self, terms: dict[str, torch.Tensor]) -> dict[str, float]:
        self.optimizer.zero_grad(set_to_none=True)
        terms["total"].backward()
        self.optimizer.step()
        return {k: float(v.detach()) for k, v in terms.items()}

    def step_sft(self, batch: dict[str, torch.Tensor], cfg: SFTConfig | None = None, **kw) -> dict[str, float]:
        self.model.train()
        return self._apply(compute_sft_loss(self.model, batch, cfg, **kw))

    def step_rl(self, batch: dict[str, torch.Tensor], cfg: RLConfig | None = None, **kw) -> dict[str, float]:
        self.model.train()
        return self._apply(compute_rl_loss(self.model, batch, cfg, **kw))
