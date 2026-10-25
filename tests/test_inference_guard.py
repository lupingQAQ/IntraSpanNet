import pytest

torch = pytest.importorskip("torch")


def test_cpu_is_allowed_and_warns(tmp_path):
    """CPU runs through the PyTorch reference path; it warns instead of refusing."""
    from intraspannet.inference import Ensemble

    with pytest.warns(RuntimeWarning, match="CPU device"):
        with pytest.raises(FileNotFoundError):  # empty dir: no checkpoints to load
            Ensemble(str(tmp_path), device="cpu")


def test_cpu_can_still_be_refused_explicitly(tmp_path):
    from intraspannet.inference import Ensemble

    with pytest.raises(RuntimeError, match="allow_cpu"):
        Ensemble(str(tmp_path), device="cpu", allow_cpu=False)
