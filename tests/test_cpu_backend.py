"""CPU backend tests.

The Triton GDN kernel needs a CUDA GPU. `intraspannet._gdn_cpu` reproduces the
same block in plain PyTorch with identical parameter names, which is what makes
`pip install intraspannet` usable on a laptop. These tests keep that path
working and keep the parameter names in sync with the released checkpoints.
"""

import pytest

torch = pytest.importorskip("torch")
nn = torch.nn


def test_cpu_block_forward_shape_and_finite():
    from intraspannet.backbone import GDNBlock

    block = GDNBlock(d_model=32, head_dim=8, backend="cpu")
    x = torch.randn(2, 48, 32)
    y = block(x)
    assert y.shape == x.shape
    assert torch.isfinite(y).all()


def test_cpu_block_parameter_names_match_release():
    from intraspannet._gdn_cpu import GatedDeltaNetCPU

    block = GatedDeltaNetCPU(hidden_size=64, head_dim=16, num_heads=3)
    keys = set(block.state_dict())
    for expected in (
        "q_proj.weight",
        "k_proj.weight",
        "v_proj.weight",
        "a_proj.weight",
        "b_proj.weight",
        "g_proj.weight",
        "o_proj.weight",
        "q_conv1d.weight",
        "k_conv1d.weight",
        "v_conv1d.weight",
        "o_norm.weight",
        "A_log",
        "dt_bias",
    ):
        assert expected in keys, expected


def test_cpu_recurrence_is_causal():
    """Changing a later byte must not change earlier outputs."""
    from intraspannet._gdn_cpu import GatedDeltaNetCPU

    block = GatedDeltaNetCPU(hidden_size=32, head_dim=8, num_heads=3)
    block.eval()
    a = torch.randn(1, 24, 32)
    b = a.clone()
    b[:, 12:] += 1.0
    with torch.no_grad():
        ya = block(a)
        yb = block(b)
    assert torch.allclose(ya[:, :12], yb[:, :12], atol=1e-5)


def test_classifier_builds_on_cpu_backend():
    from intraspannet.model import DualHeadClassifier

    model = DualHeadClassifier(num_software=18, backend="cpu")
    assert all(block.backend == "cpu" for block in model.encoder.encoder.blocks)
    x = torch.zeros(1, 64, dtype=torch.long)
    with torch.no_grad():
        out = model(x)
    assert out["software"].shape == (1, 18)
