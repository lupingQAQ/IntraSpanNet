# Changelog

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
