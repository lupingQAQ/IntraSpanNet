# Changelog

## 0.2.0 - 2026-10-26

CPU support. The model now runs on a machine without a GPU; no weight, label, or threshold change.

- `intraspannet._gdn_cpu` implements the Gated DeltaNet block in plain PyTorch with the same parameter names, so released checkpoints load unchanged. It follows the published recurrence and fla's reference implementation.
- `backend="cpu"|"fla"|"auto"` on `GDNBlock`, `NetMambaEncoder`, `ByteEncoder`, and `DualHeadClassifier`.
- `Ensemble` runs on CPU by default and warns about the speed; `allow_cpu=False` keeps the old hard refusal.
- `flash-linear-attention` moved to the `gpu` extra, so `pip install intraspannet` works on a laptop.
- CLI: `--arms` and `--gate` for a quick single-arm run; UTF-8 console output on Windows, which used to abort the table on the Chinese tier names.
- `scripts/verify_cpu_backend.py` measures the CPU port against labelled captures.
- Measured: 9/10 on labelled lab captures with the CPU path, ~2 s per flow per arm.

## 0.1.1 - 2026-10-26

Packaging release for the 0.1.0 model. No weight, label, or threshold change.

- `load_backbone` warm-starts a model across a changed label set by keeping the tensors whose shapes match.
- `examples/train_sft.py` and `examples/train_rl.py`, driven by a JSONL manifest.
- Training guide in English and Chinese: `docs/TRAINING.md`, `docs/TRAINING.zh-CN.md`.
- README and README.zh-CN.md link to each other; both carry the training usage.
- `pip install "intraspannet[train]"` pulls scikit-learn for k > 1 sub-prototypes.

## 0.1.0 - 2026-10-24, updated 2026-10-26

Initial release.

- Four-arm ensemble for 18 security products and services.
- Open-set rejection with a calibrated prototype-distance threshold.
- Portable inference package, CLI, and HTTP service for FLW1 records.
- pcap/pcapng preprocessing with IPv4 masking.
- Evaluation and public-split audit scripts.
- Model card, results summary, benchmark audit, and deployment notes.
- Released weights: six classifier arms, six prototype matrices, two contrastive encoders, one distilled student.

Known limitations:

- `stunnel` recall is zero in the acceptance set.
- CPU inference is not supported.
- Timing rescue is not included.
- Training code is not included in this release.
