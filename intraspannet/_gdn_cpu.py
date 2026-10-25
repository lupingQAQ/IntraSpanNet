"""CPU fallback for the Gated DeltaNet block.

The released checkpoints were trained with ``fla.layers.GatedDeltaNet`` in
``mode="chunk"``, which compiles Triton kernels and therefore needs a CUDA GPU.
This module reproduces the same computation in plain PyTorch so the checkpoints
can be evaluated on a machine without one.

Parameter names, shapes and the forward order match ``fla`` exactly, so a
checkpoint loads with no remapping. The recurrence is the one published with
Gated Delta Networks (arXiv:2412.06464) and is the same loop as
``fla.ops.gated_delta_rule.naive.naive_recurrent_gated_delta_rule``:

    h_t = h_{t-1} * exp(g_t)
    v_t = (v_t - h_{t-1} k_t) * beta_t
    h_t = h_t + k_t v_t^T
    o_t = q_t^T h_t

with ``g = -exp(A_log) * softplus(a + dt_bias)``, L2-normalised q and k, and
q scaled by ``1 / sqrt(head_k_dim)``.

This path is slower than the Triton kernel by two to three orders of magnitude.
It exists so the model can be inspected on a laptop; it is not the deployment
path.
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

__all__ = ["GatedDeltaNetCPU", "ShortConv"]


class ShortConv(nn.Conv1d):
    """Causal depthwise convolution followed by SiLU, as in ``fla.modules.ShortConvolution``."""

    def __init__(self, channels: int, kernel_size: int):
        super().__init__(
            in_channels=channels,
            out_channels=channels,
            kernel_size=kernel_size,
            groups=channels,
            bias=False,
            padding=kernel_size - 1,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, C) -> conv over time -> first T steps -> SiLU
        y = F.conv1d(
            x.transpose(1, 2),
            self.weight,
            self.bias,
            padding=self.kernel_size[0] - 1,
            groups=self.groups,
        )
        y = y[..., : x.shape[1]]
        return F.silu(y.transpose(1, 2))


class GatedRMSNorm(nn.Module):
    """RMSNorm over the value dimension, multiplied by ``SiLU(gate)``."""

    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps

    def forward(self, x: torch.Tensor, gate: torch.Tensor) -> torch.Tensor:
        rms = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return self.weight * rms * F.silu(gate)


class GatedDeltaNetCPU(nn.Module):
    """Parameter-compatible replacement for ``fla.layers.GatedDeltaNet``.

    Only the configuration used by this release is supported: gate on, short
    convolution on, no negative eigenvalues, no attention mask.
    """

    def __init__(
        self,
        hidden_size: int = 256,
        head_dim: int = 64,
        num_heads: int = 3,
        expand_v: float = 2.0,
        conv_size: int = 4,
        norm_eps: float = 1e-6,
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.head_k_dim = head_dim
        self.head_v_dim = int(head_dim * expand_v)
        self.num_heads = num_heads
        self.key_dim = num_heads * self.head_k_dim
        self.value_dim = num_heads * self.head_v_dim

        self.q_proj = nn.Linear(hidden_size, self.key_dim, bias=False)
        self.k_proj = nn.Linear(hidden_size, self.key_dim, bias=False)
        self.v_proj = nn.Linear(hidden_size, self.value_dim, bias=False)
        self.a_proj = nn.Linear(hidden_size, num_heads, bias=False)
        self.b_proj = nn.Linear(hidden_size, num_heads, bias=False)
        self.g_proj = nn.Linear(hidden_size, self.value_dim, bias=False)
        self.o_proj = nn.Linear(self.value_dim, hidden_size, bias=False)

        self.q_conv1d = ShortConv(self.key_dim, conv_size)
        self.k_conv1d = ShortConv(self.key_dim, conv_size)
        self.v_conv1d = ShortConv(self.value_dim, conv_size)

        self.o_norm = GatedRMSNorm(self.head_v_dim, eps=norm_eps)

        self.A_log = nn.Parameter(torch.zeros(num_heads))
        self.dt_bias = nn.Parameter(torch.zeros(num_heads))

    def _decay(self, a: torch.Tensor) -> torch.Tensor:
        """g = -exp(A_log) * softplus(a + dt_bias), shape (B, T, H)."""
        return -self.A_log.exp() * F.softplus(a + self.dt_bias)

    @staticmethod
    def _l2norm(x: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
        return x / x.norm(dim=-1, keepdim=True).clamp_min(eps)

    def recurrence(
        self,
        q: torch.Tensor,
        k: torch.Tensor,
        v: torch.Tensor,
        beta: torch.Tensor,
        g: torch.Tensor,
    ) -> torch.Tensor:
        """Gated delta rule, recurrent form. q,k: (B,T,H,K); v: (B,T,H,V)."""
        b, t, h, kdim = k.shape
        vdim = v.shape[-1]
        dtype = torch.float32

        q, k, v = q.to(dtype), k.to(dtype), v.to(dtype)
        beta, g = beta.to(dtype), g.to(dtype)
        q = self._l2norm(q) * (1.0 / math.sqrt(kdim))
        k = self._l2norm(k)

        state = torch.zeros(b, h, kdim, vdim, dtype=dtype)
        out = torch.zeros(b, t, h, vdim, dtype=dtype)
        for i in range(t):
            state = state * g[:, i].exp()[..., None, None]
            kv = (state * k[:, i].unsqueeze(-1)).sum(-2)
            delta = (v[:, i] - kv) * beta[:, i].unsqueeze(-1)
            state = state + k[:, i].unsqueeze(-1) * delta.unsqueeze(-2)
            out[:, i] = torch.einsum("bhd,bhdm->bhm", q[:, i], state)
        return out

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, t, _ = x.shape
        h, hk, hv = self.num_heads, self.head_k_dim, self.head_v_dim

        q = self.q_conv1d(self.q_proj(x)).reshape(b, t, h, hk)
        k = self.k_conv1d(self.k_proj(x)).reshape(b, t, h, hk)
        v = self.v_conv1d(self.v_proj(x)).reshape(b, t, h, hv)

        beta = self.b_proj(x).sigmoid()
        g = self._decay(self.a_proj(x))

        o = self.recurrence(q, k, v, beta, g)

        gate = self.g_proj(x).reshape(b, t, h, hv)
        o = self.o_norm(o, gate)
        return self.o_proj(o.reshape(b, t, h * hv))
