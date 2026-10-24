# Six public traffic benchmarks have an 80% train/test overlap

We audited the public traffic-classification benchmarks used in our comparison table. Five of the six contain a large fraction of byte-identical flows in both train and test. The overlap is about 80% of the test set. Tor is the exception, with 0%.

This post describes the audit, the model we trained under a deduplicated protocol, and the limits of both.

## Why audit the splits

Traffic classification papers often report accuracy above 0.99 on public benchmarks. The numbers are difficult to compare because preprocessing, split construction, and packet budgets differ. One variable is rarely discussed: whether the same flow appears in both train and test.

We hashed every flow in the distributed train, validation, and test directories. Two hashes were used: MD5 of the PNG file bytes, and MD5 of the decoded grayscale pixels. The two hashes produced identical results. Duplicates are exact matches, not near-duplicates.

| Benchmark | Train | Test | Train ∩ test | Share of test | Clean test |
|---|---:|---:|---:|---:|---:|
| ISCXVPN2016 | 13,281 | 1,384 | 1,106 | 79.9% | 278 |
| ISCXTor2016 | 11,655 | 1,458 | 0 | 0% | 1,458 |
| USTC-TFC2016 | 37,323 | 6,662 | 5,605 | 84.1% | 1,057 |
| CICIoT2022 | 18,734 | 1,951 | 1,571 | 80.5% | 380 |
| CrossPlatform-Android | 44,700 | 4,656 | 3,733 | 80.2% | 923 |
| CrossPlatform-iOS | 40,379 | 4,205 | 3,396 | 80.8% | 809 |

Label conflicts across splits are zero. Every duplicate stays inside its class.

The likely cause is independent sampling from the same flow pool without cross-split deduplication. The property belongs to the data distribution, not to any single paper. Every method evaluated on the same files sees the same overlap.

## What it means

Absolute accuracy on these benchmarks is inflated. About 80% of the test flows are memorization cases. A model can reach a high score by learning flow identity rather than protocol behavior.

Same-split comparisons remain valid as same-protocol comparisons. If two methods are evaluated on the same files, the overlap affects both. But the numbers are not evidence of generalization to a new network.

Tor is the only clean benchmark in the set. Comparisons on Tor are the strongest evidence in our report. On the other five, we report both the original split and a deduplicated test subset. On the deduplicated subset, our macro-F1 drops by 1.4 to 4.4 percentage points. The relative lead over the external baseline does not shrink.

## The model

We trained a byte-level classifier with four Gated DeltaNet blocks. Each arm has 2.86M parameters. The input is the first five packets of a unidirectional flow, 320 bytes per packet, for a total of 1600 bytes. Each packet contributes 80 bytes of IPv4 and transport headers and 240 bytes of payload. IPv4 source and destination addresses are zeroed.

The model has four heads: product (18 classes), type (10), tier (3), and malicious family (11). The product head is closed-set. A separate prototype distance decides whether to trust it. Each class has three sub-prototypes. At inference, the distance is one minus the maximum cosine similarity to any prototype. If the mean distance over two gate arms exceeds 0.1041, the flow is reported as unknown.

The released system averages four classifier arms and two gate arms. The arms share the same architecture and differ in pretraining recipe, loss weighting, and hard-negative sampling.

Training has three stages:

1. Contrastive pretraining on 33,184 training-only flows.
2. Multi-task supervised fine-tuning for 60 epochs.
3. REINFORCE fine-tuning for 300 episodes with reward shaping.

The validation set is split at the flow level into dev and test halves. Threshold calibration, checkpoint selection, and ensemble selection use dev only. Test is used once for the final numbers.

## Results

| Metric | Test (503 flows) | All validation (1006 flows) |
|---|---:|---:|
| Product accuracy | 0.8787 | 0.8817 |
| Tier accuracy | 0.9245 | 0.9334 |
| Macro-F1 (supported classes) | 0.7621 | 0.8240 |
| Gate AUROC | 0.9784 | 0.9820 (dev) |

Unknown-product bins are rejected at 100% in the acceptance set. The operating point is stable from q=0.64 to q=0.75.

The acceptance demo contains 264 product bins. The raw ensemble accepts 8 of 10 products. An internal timing-rescue rule raises this to 9 of 10. The timing rule is not part of the release, so the published model reproduces the 8/10 result.

`stunnel` is the only product with zero recall (0/30). It needs enrollment or additional data. The test split is flow-level, not session-level; each class has one held-out session. These limits matter more than the third decimal of accuracy.

## What is in the release

- Four-arm ensemble and prototype matrices.
- Portable inference package with pcap/pcapng preprocessing.
- CLI and HTTP service for the 1620-byte FLW1 record format.
- Evaluation and split-audit scripts.
- Model card, results summary, and benchmark audit.

CPU inference is not supported. The GDN backbone uses Triton kernels and requires CUDA. The reference GPU is an RTX 4090; the ensemble peaks at about 3.4GB of VRAM at batch 128 and runs at 253 flows per second.

The code and weights are Apache-2.0. The documentation is CC-BY-4.0. The repository contains no captures.

## Reproduce the audit

The audit scripts are in `scripts/audit_split_dups.py` and `scripts/audit_split_labels.py`. They expect one subdirectory per class and files in the distributed format. The scripts report byte overlap, pixel overlap, per-class counts, and label conflicts. The clean-subset lists are generated locally and are not redistributed because the benchmark filenames contain capture metadata.

If you maintain a public traffic dataset, the useful next step is to deduplicate across splits before release. If you report a benchmark number, state whether the split contains duplicates. This is more valuable than another decimal place.
