"""IntraSpanNet dual-head classifier.

Checkpoint compatibility: the module names and nesting here match the
released stage3_*.pth files. Keep them unchanged when editing.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .backbone import ByteEmbed, NetMambaEncoder
from .labels import PRODUCT_TO_TIER, PRODUCT_TO_TYPE


class GradientReversal(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, alpha):
        ctx.alpha = alpha
        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output):
        return -ctx.alpha * grad_output, None


def grad_reverse(x, alpha: float = 1.0):
    return GradientReversal.apply(x, alpha)


class ByteEncoder(nn.Module):
    """bytes(1600) -> ByteEmbed -> [bytes, CLS] -> GDN x4 -> CLS."""

    def __init__(
        self,
        d_model: int = 256,
        num_layers: int = 4,
        d_state: int = 16,
        dropout: float = 0.1,
        seq_len: int = 1600,
        backend: str = "auto",
    ):
        super().__init__()
        self.seq_len = seq_len
        self.embed = ByteEmbed(vocab_size=256, embed_dim=d_model)
        self.cls_token = nn.Parameter(torch.randn(1, 1, d_model))
        self.pos_embed = nn.Parameter(torch.randn(1, seq_len + 1, d_model))
        self.encoder = NetMambaEncoder("gdn", d_model, num_layers, d_state, dropout, backend=backend)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b = x.shape[0]
        x_emb = self.embed(x.reshape(b, -1))
        cls_tokens = self.cls_token.expand(b, -1, -1)
        x = torch.cat([x_emb, cls_tokens], dim=1)
        x = x + self.pos_embed[:, : x.shape[1], :]
        x_enc = self.encoder(x)
        return x_enc[:, -1]


class DualHeadClassifier(nn.Module):
    def __init__(
        self,
        num_software: int = 18,
        num_types: int = 10,
        num_tiers: int = 3,
        num_malicious: int = 11,
        num_domains: int = 8,
        d_model: int = 256,
        num_layers: int = 4,
        d_state: int = 16,
        mlp_hidden: int = 512,
        dropout: float = 0.1,
        backend: str = "auto",
    ):
        super().__init__()
        self.encoder = ByteEncoder(d_model, num_layers, d_state, dropout, backend=backend)

        def head(n_out: int, hidden: int = mlp_hidden) -> nn.Sequential:
            return nn.Sequential(
                nn.LayerNorm(d_model),
                nn.Dropout(dropout),
                nn.Linear(d_model, hidden),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, n_out),
            )

        self.software_head = head(num_software)
        self.type_head = head(num_types)
        self.tier_head = nn.Sequential(nn.LayerNorm(d_model), nn.Linear(d_model, num_tiers))
        self.malicious_head = head(num_malicious)
        self.domain_head = head(num_domains, hidden=256)
        self.proj_head = nn.Sequential(nn.Linear(d_model, 128), nn.ReLU(), nn.Linear(128, 64))

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)

    def forward(self, x: torch.Tensor, grl_alpha: float = 0.0) -> dict[str, torch.Tensor]:
        feat = self.encode(x)
        out = {
            "features": feat,
            "software": self.software_head(feat),
            "type_": self.type_head(feat),
            "tier": self.tier_head(feat),
            "malicious": self.malicious_head(feat),
            "projection": self.proj_head(feat),
        }
        if grl_alpha > 0:
            out["domain"] = self.domain_head(grad_reverse(feat, grl_alpha))
        return out

    @staticmethod
    def prototype_distance(feat_norm: torch.Tensor, prototypes_norm: torch.Tensor) -> torch.Tensor:
        """Minimum cosine distance to any prototype."""
        return 1.0 - (feat_norm @ prototypes_norm.t()).max()

    @torch.no_grad()
    def infer(
        self,
        x: torch.Tensor,
        prototypes: torch.Tensor | None = None,
        openset_threshold: float | None = None,
    ) -> list[dict]:
        out = self.forward(x)
        feat = F.normalize(out["features"], dim=-1)
        soft_p = F.softmax(out["software"], dim=-1)
        mal_p = F.softmax(out["malicious"], dim=-1)
        s_conf, s_pred = soft_p.max(-1)
        m_conf, m_pred = mal_p.max(-1)
        type_pred = out["type_"].argmax(-1)
        tier_pred = out["tier"].argmax(-1)

        results = []
        for i in range(len(s_pred)):
            row = {
                "software_id": int(s_pred[i]),
                "software_conf": float(s_conf[i]),
                "type_id": int(type_pred[i]),
                "tier_id": int(tier_pred[i]),
                "malicious_id": int(m_pred[i]),
                "malicious_conf": float(m_conf[i]),
                "is_malicious": bool(m_pred[i] > 0),
                "unknown": False,
                "prototype_dist": None,
            }
            if prototypes is not None and openset_threshold is not None:
                d = self.prototype_distance(feat[i : i + 1], prototypes)
                row["prototype_dist"] = float(d)
                row["unknown"] = bool(d > openset_threshold)
            results.append(row)
        return results


def compute_prototypes(
    model: DualHeadClassifier,
    x: torch.Tensor,
    y: torch.Tensor,
    device: str = "cuda",
    batch: int = 256,
    k: int = 1,
) -> torch.Tensor:
    """Per-class prototypes. k > 1 uses KMeans sub-prototypes."""
    model.eval()
    feats = []
    with torch.no_grad():
        for i in range(0, len(x), batch):
            xb = x[i : i + batch].long().to(device)
            feats.append(F.normalize(model.encode(xb), dim=-1).cpu())
    feats = torch.cat(feats)
    yt = y.cpu()
    n_classes = int(yt.max()) + 1
    if k > 1:
        from sklearn.cluster import KMeans

        rows = []
        for c in range(n_classes):
            m = feats[yt == c]
            if len(m) == 0:
                continue
            kk = min(k, len(m))
            if kk == 1:
                rows.append(F.normalize(m.mean(0, keepdim=True), dim=-1))
            else:
                km = KMeans(n_clusters=kk, n_init=3, random_state=0).fit(m.numpy())
                rows.append(F.normalize(torch.tensor(km.cluster_centers_, dtype=torch.float32), dim=-1))
        return torch.cat(rows)
    protos = torch.zeros(n_classes, feats.shape[1])
    for c in range(n_classes):
        m = feats[yt == c]
        if len(m) > 0:
            protos[c] = F.normalize(m.mean(0, keepdim=True), dim=-1)
    return protos


def calibrate_threshold(
    model: DualHeadClassifier,
    x: torch.Tensor,
    prototypes: torch.Tensor,
    device: str = "cuda",
    percentile: float = 95,
    batch: int = 256,
) -> float:
    model.eval()
    dists = []
    with torch.no_grad():
        for i in range(0, len(x), batch):
            xb = x[i : i + batch].long().to(device)
            f = F.normalize(model.encode(xb), dim=-1).cpu()
            sim = f @ prototypes.t()
            dists.extend((1.0 - sim.max(dim=-1).values).tolist())
    return float(torch.quantile(torch.tensor(dists), percentile / 100.0))


__all__ = [
    "ByteEncoder",
    "DualHeadClassifier",
    "compute_prototypes",
    "calibrate_threshold",
    "grad_reverse",
    "PRODUCT_TO_TIER",
    "PRODUCT_TO_TYPE",
]
