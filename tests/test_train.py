"""Training-hook tests.

The released backbone needs `fla` (Triton kernels) which is not available in
every CI image. These tests therefore exercise the loss and RL math against a
stub that reproduces the classifier's output contract, so the hooks are covered
even when the backbone cannot be imported.
"""

import pytest

torch = pytest.importorskip("torch")
nn = torch.nn


class StubClassifier(nn.Module):
    """Same output contract as DualHeadClassifier, without the GDN backbone."""

    def __init__(self, n_software=18, n_types=10, n_tiers=3, n_mal=11, n_domains=4, d=32):
        super().__init__()
        self.emb = nn.Embedding(256, d)
        self.software_head = nn.Linear(d, n_software)
        self.type_head = nn.Linear(d, n_types)
        self.tier_head = nn.Linear(d, n_tiers)
        self.malicious_head = nn.Linear(d, n_mal)
        self.domain_head = nn.Linear(d, n_domains)
        self.proj_head = nn.Linear(d, 8)

    def forward(self, x, grl_alpha: float = 0.0):
        feat = self.emb(x).mean(dim=1)
        out = {
            "features": feat,
            "software": self.software_head(feat),
            "type_": self.type_head(feat),
            "tier": self.tier_head(feat),
            "malicious": self.malicious_head(feat),
            "projection": self.proj_head(feat),
        }
        if grl_alpha > 0:
            out["domain"] = self.domain_head(feat)
        return out


def _batch(n=4):
    return {
        "x": torch.randint(0, 256, (n, 1600), dtype=torch.long),
        "y_software": torch.randint(0, 18, (n,)),
        "y_type": torch.randint(0, 10, (n,)),
        "y_tier": torch.randint(0, 3, (n,)),
        "y_malicious": torch.randint(0, 11, (n,)),
        "y_domain": torch.randint(0, 4, (n,)),
    }


def test_sft_loss_terms_and_backprop():
    from quietspan.train import SFTConfig, compute_sft_loss

    model = StubClassifier()
    cfg = SFTConfig(lda=0.5, hardneg=1.0, w_domain=0.1)
    prior = torch.ones(18) / 18
    terms = compute_sft_loss(model, _batch(), cfg, class_prior=prior, grl_alpha=0.3)

    for key in ("software", "type", "tier", "malicious", "contrast", "domain", "total"):
        assert key in terms, key
        assert torch.isfinite(terms[key]), key
    terms["total"].backward()
    assert model.software_head.weight.grad is not None


def test_sft_loss_without_optional_inputs():
    from quietspan.train import SFTConfig, compute_sft_loss

    model = StubClassifier()
    terms = compute_sft_loss(model, _batch(), SFTConfig())
    assert "domain" not in terms
    assert torch.isfinite(terms["total"])


def test_rl_loss_reward_range_and_grad():
    from quietspan.train import RLConfig, compute_rl_loss

    model = StubClassifier()
    terms = compute_rl_loss(model, _batch(), RLConfig())
    assert torch.isfinite(terms["total"])
    assert 0.0 <= float(terms["reward"]) <= 2.5
    terms["total"].backward()
    assert model.software_head.weight.grad is not None


def test_trainer_updates_weights():
    from quietspan.train import SFTConfig, Trainer

    model = StubClassifier()
    trainer = Trainer(model, torch.optim.SGD(model.parameters(), lr=1e-2))
    before = model.software_head.weight.detach().clone()
    stats = trainer.step_sft(_batch(), SFTConfig())
    assert "total" in stats
    assert not torch.equal(before, model.software_head.weight.detach())
