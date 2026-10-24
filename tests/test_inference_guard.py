import pytest

torch = pytest.importorskip("torch")


def test_cpu_is_rejected_without_override(tmp_path):
    from gdnet.inference import Ensemble

    with pytest.raises(RuntimeError, match="CUDA"):
        Ensemble(str(tmp_path), device="cpu")
