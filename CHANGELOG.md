# Changelog

## 0.1.0 - 2026-10-24

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
