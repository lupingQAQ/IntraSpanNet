# Changelog

## 0.1.0 - 2026-10-24, updated 2026-10-26

Initial release.

- Four-arm ensemble for 18 security products and services.
- Open-set rejection with a calibrated prototype-distance threshold.
- Portable inference package, CLI, and HTTP service for FLW1 records.
- pcap/pcapng preprocessing with IPv4 masking.
- Evaluation and public-split audit scripts.
- Model card, results summary, benchmark audit, and deployment notes.
- Released weights: six classifier arms, six prototype matrices, two contrastive encoders, one distilled student.
- Further-training API: `SFTConfig`, `compute_sft_loss`, `RLConfig`, `compute_rl_loss`, `Trainer`, and `load_backbone` for warm starts across a changed label set.
- Runnable training examples: `examples/train_sft.py`, `examples/train_rl.py`, driven by a JSONL manifest.
- Training guide in English and Chinese: `docs/TRAINING.md`, `docs/TRAINING.zh-CN.md`.
- Both READMEs rewritten with a language switch between them.

Known limitations:

- `stunnel` recall is zero in the acceptance set.
- CPU inference is not supported.
- Timing rescue is not included.
- Stage-1 contrastive pretraining is not included. Stages 2 and 3 are, as an API.
