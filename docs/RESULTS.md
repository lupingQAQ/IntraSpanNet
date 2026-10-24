# GDNet results

This document summarizes the evaluation protocol and the released numbers. It is self-contained; the internal experiment log is not part of the release.

## Scope

Target: PCs, servers, and internal network devices. The model identifies security products and services from encrypted or unencrypted traffic. Mobile and IoT benchmarks are out of scope.

## Released system

- Classifier arms: `b_s0`, `a_lda`, `b_lda`, `a_s0`
- Gate arms: `a_lda`, `b_lda`
- Open-set threshold: `0.1041`
- Input: first 5 packets, 320 bytes per packet, IPv4 addresses masked
- Parameters: 2.86M per arm, 11.44M for the ensemble
- Weights: about 46 MB for the ensemble

## Splits

The product dataset contains 18 classes and 40,283 labeled flows across lab capture sessions. The validation set contains 1,006 flows from 14 held-out sessions. The validation set is split at the flow level into dev (503 flows) and test (503 flows). Threshold calibration, ensemble selection, and checkpoint selection use dev only. Test is used once for the final numbers.

This is a flow-level split, not a session-level split. Each class has one held-out session. The absolute numbers therefore describe performance on flows from those sessions, not generalization to new organizations.

## Product and tier accuracy

| Metric | Test (503) | All validation (1006) |
|---|---:|---:|
| Product accuracy | 0.8787 | 0.8817 |
| Tier accuracy | 0.9245 | 0.9334 |
| Macro-F1, supported classes | 0.7621 | 0.8240 |
| Gate AUROC | 0.9784 | 0.9820 (dev) |

The test-half macro-F1 is pulled down by classes with one or two test flows (`wireguard` has one). The all-validation value is the more stable reference.

## Open-set behavior

- Unknown-product bins: 18 bins from products not present in training.
- Rejection rate at the fixed threshold: 100%.
- Stable operating range: q=0.64 to q=0.75.
- Gate AUROC: 0.9784 on test, 0.9820 on dev.

The acceptance demo uses 264 product bins. The raw ensemble accepts 8 of 10 products. A timing-rescue rule raises this to 9 of 10. The timing rule is not part of v0.1.0, so the released model reproduces the 8/10 result.

`stunnel` is the only product with zero recall (0/30) in the acceptance demo. `wireguard` has two bins and is treated as sample noise.

## Malicious detection

The malicious head is a secondary output. On the deduplicated USTC-TFC2016 test set (n=1242), the best arm reaches macro-F1 0.9702. The binary benign/malicious F1 is at least 0.994 across arms. The malicious head is not the primary release target and is not calibrated for production alerting.

## Service and enrollment

- HTTP service on FLW1 records: 6/6 known flows.
- Few-shot enrollment: 8/8 after registering three sub-prototypes for `smb`.
- Probe-to-service chain: 99,888 flows collected in 30 seconds on the test host; the service rejected container-management traffic as unknown, which is the expected behavior outside the product domain.

## Throughput and memory

| Configuration | Throughput | Latency at batch 1 | Peak VRAM at batch 128 |
|---|---:|---:|---:|
| Single arm | 1,017 flows/s | 10.7 ms | 3.37 GB |
| Four-arm ensemble | 253 flows/s | 43.1 ms | 3.40 GB |
| Distilled student | 1,011 flows/s | 10.6 ms | 3.37 GB |

Measured on an RTX 4090 with fp32. CPU inference is not supported. The GDN backbone uses Triton kernels.

## Benchmark comparisons

The internal report compares this model with MambaNetBurst and netFound under matched input budgets. Those comparisons are same-protocol comparisons on public splits. They are not reproduced in this repository because the public datasets are not redistributed.

Public split audit: five of six public benchmarks contain about 80% byte-identical train/test overlap. Tor is the exception at 0%. As a result, absolute benchmark accuracy is not evidence of generalization. Relative comparisons remain same-protocol comparisons. See [BENCHMARK_AUDIT.md](BENCHMARK_AUDIT.md).

## What is not claimed

- No claim of state-of-the-art accuracy on public benchmarks.
- No claim of session-level or cross-organization generalization.
- No claim that the model detects all security products. The label set is closed at 18 products, plus an unknown class.
- No claim that the malicious head is a replacement for an IDS.
- No claim of CPU support.

## Reproducibility

The released checkpoints, prototypes, label table, threshold, and ensemble configuration are sufficient to reproduce the test-half numbers if the evaluation split is available. The split itself is not redistributed because it contains lab traffic. The evaluation script is in `scripts/evaluate.py` and expects a directory of 1600-byte flow bins plus a CSV label file.
