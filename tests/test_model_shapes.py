import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("fla")


def test_model_output_shapes():
    from intraspannet.model import DualHeadClassifier

    model = DualHeadClassifier(num_software=18, num_types=10, num_tiers=3, num_malicious=11)
    x = torch.zeros(2, 1600, dtype=torch.long)
    out = model(x)
    assert out["software"].shape == (2, 18)
    assert out["type_"].shape == (2, 10)
    assert out["tier"].shape == (2, 3)
    assert out["malicious"].shape == (2, 11)
    assert out["features"].shape == (2, 256)
