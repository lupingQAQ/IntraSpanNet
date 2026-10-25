---
license: apache-2.0
language:
  - en
  - zh
library_name: pytorch
tags:
  - network-security
  - traffic-classification
  - encrypted-traffic
  - open-set-recognition
  - mamba
  - gdn
  - pytorch
metrics:
  - accuracy
  - f1
  - auroc
---

# QuietSpan

QuietSpan identifies security products and services from the first five packets of a network flow. It reports a product label, a type, a tier, and an open-set distance. Flows that do not match a known product are rejected as unknown.

This repository contains the weights and configuration. Code is at [github.com/lupingQAQ/quietspan](https://github.com/lupingQAQ/quietspan). The technical report is at [paper/quietspan.pdf](https://github.com/lupingQAQ/quietspan/blob/main/paper/quietspan.pdf).

## Model details

- Architecture: ByteEmbed, four Gated DeltaNet blocks, four task heads.
- Input: 1600 bytes per flow (5 packets x 320 bytes, IPv4 addresses masked).
- Parameters: 2.86M per arm; 11.44M for the four-arm ensemble.
- Output classes: 18 products, 10 types, 3 tiers, 11 malicious classes.
- Open-set method: three sub-prototypes per class; cosine distance; threshold 0.1041.
- Ensemble: classifier arms A-S0, A-LDA, B-LDA, B-S0; gate arms A-LDA and B-LDA.
- Arm naming: the letter is the pre-training run (A or B), the suffix is the training variant (`s0` standard multi-task objective, `lda` logit adjustment by class prior, `hn` hard-negative weighting). Checkpoint files carry the same labels in lower case, for example `stage3_a_s0.pth` is arm A-S0.
- License: Apache-2.0.

## Intended use

- Asset discovery: identify security agents, appliances, and common services on hosts and internal networks.
- Shadow IT and shadow security review: find products that are present but not in the asset inventory.
- Research: byte-level traffic classification and open-set recognition.

The model is intended for authorized monitoring on networks you own or administer. It is not a replacement for an IDS, EDR, or vulnerability scanner.

## Out-of-scope use

- Identifying users, content, or application payloads.
- Monitoring networks without authorization.
- Mobile and IoT device classification. The model was not trained for those domains.
- Real-time blocking or automated enforcement without human review.

## Training data

- 40,283 labeled flows from lab captures of 18 products and services.
- Public benchmark training splits for pretraining and the malicious head.
- Contrastive pretraining uses 33,184 training-only flows. Validation and holdout flows are excluded.
- No customer traffic is included in the released weights or repository.

The product labels are:

`windows_defender`, `clamav_freshclam_win`, `clamav_freshclam`, `velociraptor`, `velociraptor_win`, `osquery`, `wazuh_agent`, `wireguard`, `openvpn`, `stunnel`, `squid_proxy`, `ntopng`, `guacamole_mgmt`, `waf_modsecurity`, `suricata_update`, `web_http`, `ssh`, `ftp`.

## Evaluation

| Metric | Test (503 flows) | All validation (1006 flows) |
|---|---:|---:|
| Product accuracy | 0.8787 | 0.8817 |
| Tier accuracy | 0.9245 | 0.9334 |
| Macro-F1 (supported classes) | 0.7621 | 0.8240 |
| Gate AUROC | 0.9784 | 0.9820 (dev) |

Additional results:

- Unknown rejection: 100% on 18 unknown-product bins.
- Malicious macro-F1: 0.9702 on deduplicated USTC-TFC2016 (n=1242).
- Acceptance: 8/10 products without timing rescue; 9/10 with the internal timing rule, which is not included in v0.1.0.
- Throughput: 253 flows/s for the ensemble, 1,017 flows/s for one arm, on an RTX 4090.

The test split is a flow-level half of the validation set, not a session-level holdout. Each class has one held-out session. See [docs/RESULTS.md](https://github.com/lupingQAQ/quietspan/blob/main/docs/RESULTS.md) for the full protocol.

## Limitations

- `stunnel` has zero recall in the acceptance demo (0/30).
- Flow-level test split; session-level generalization is not measured.
- CPU inference is not supported. The GDN backbone uses Triton kernels and requires CUDA.
- The model was trained on lab traffic. Production performance with different software versions, proxies, or NAT is unknown.
- The malicious head is a secondary output and is not calibrated for production alerting.
- Public benchmark splits contain about 80% train/test overlap (Tor 0%). Absolute benchmark numbers are not evidence of generalization.

## Ethical and legal considerations

Traffic classification can reveal sensitive information about a network. Use the model only on networks you own or have written authorization to monitor. Do not upload captures to public demos. Follow local law and organizational policy.

The model outputs a probability and a distance, not a fact. Treat low-confidence and unknown results as prompts for human review.

## Files

- `stage3_*.pth`: six classifier arms.
- `prototypes_*_k3.pth`: prototype matrices.
- `stage1_clean_*.pth`: contrastive encoders.
- `student_d1.pth`: distilled student, experimental.
- `config.json`: ensemble configuration and reference metrics.
- `labels.json`: label table.
- `SHA256SUMS`: checksums.

## Citation

```bibtex
@software{quietspan2026,
  title  = {QuietSpan: an intranet traffic detection model for security product identification},
  year   = {2026},
  url    = {https://github.com/lupingQAQ/quietspan},
  note   = {Model: https://huggingface.co/luping123/quietspan}
}
```
