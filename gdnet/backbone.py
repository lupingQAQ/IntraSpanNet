"""Byte-level GDN backbone used by GDNet V5.

The architecture follows the byte-level Mamba/GDN encoder used by
MambaNetBurst (https://github.com/gayanku/MambaNetBurst). The code here is a
trimmed, GDN-only implementation so the released checkpoints can be loaded
without the other mixer families.

GDN reference: "Gated Delta Networks: Improving Mamba2 with the Delta Rule",
arXiv:2412.06464. The layer itself comes from flash-linear-attention (fla).
"""

from __future__ import annotations

import torch
import torch.nn as nn

try:
    from fla.layers.gated_deltanet import GatedDeltaNet
except ImportError:  # pragma: no cover - exercised only without the dependency
    GatedDeltaNet = None


class ByteEmbed(nn.Module):
    """Learned byte embedding with a residual MLP projection."""

    def __init__(self, vocab_size: int = 256, embed_dim: int = 256, proj_hidden: int = 512):
        super().__init__()
        self.byte_embed = nn.Embedding(vocab_size, embed_dim)
        self.proj = nn.Sequential(
            nn.Linear(embed_dim, proj_hidden),
            nn.GELU(),
            nn.Linear(proj_hidden, embed_dim),
        )
        self.norm = nn.LayerNorm(embed_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.byte_embed(x)
        x = x + self.proj(x)
        return self.norm(x)


class GDNBlock(nn.Module):
    """Pre-norm residual Gated DeltaNet block."""

    def __init__(
        self,
        d_model: int,
        head_dim: int = 64,
        expand_v: float = 2.0,
        conv_size: int = 4,
    ):
        super().__init__()
        if GatedDeltaNet is None:
            raise ImportError(
                "GDNet requires flash-linear-attention. "
                "Install it with: pip install flash-linear-attention"
            )
        key_dim_target = 0.75 * d_model
        num_heads = int(round(key_dim_target / head_dim))
        if num_heads < 1 or abs(num_heads * head_dim - key_dim_target) > 1e-6:
            raise ValueError(
                f"d_model={d_model} is incompatible with head_dim={head_dim}: "
                f"num_heads * head_dim must equal 0.75 * d_model"
            )
        self.norm = nn.LayerNorm(d_model)
        self.gdn = GatedDeltaNet(
            hidden_size=d_model,
            expand_v=expand_v,
            head_dim=head_dim,
            num_heads=num_heads,
            mode="chunk",
            use_gate=True,
            use_short_conv=True,
            conv_size=conv_size,
            conv_bias=False,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.gdn(self.norm(x))[0]


class NetMambaEncoder(nn.Module):
    """Stack of GDN blocks with a final layer norm."""

    def __init__(
        self,
        baseblock: str = "gdn",
        d_model: int = 256,
        num_layers: int = 4,
        d_state: int = 16,
        dropout: float = 0.1,
    ):
        super().__init__()
        if baseblock != "gdn":
            raise ValueError(f"this release only supports baseblock='gdn', got {baseblock!r}")
        self.norm = nn.LayerNorm(d_model)
        self.blocks = nn.ModuleList([GDNBlock(d_model) for _ in range(num_layers)])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        for block in self.blocks:
            x = block(x)
        return self.norm(x)
