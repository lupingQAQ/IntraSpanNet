# Architecture

## Inference path

```
pcap/pcapng
  -> dpkt parser
  -> unidirectional flow key (src, sport, dst, dport, proto)
  -> first 5 packets, 80B header + 240B payload each
  -> 1600B uint8 vector, IPv4 addresses zeroed
  -> four classifier arms (shared architecture, different training recipes)
       ByteEmbed -> 4 x GDN -> CLS -> software head (18) / type head (10)
                                     / tier head (3) / malicious head (11)
  -> average softmax over four arms
  -> average prototype distance over two gate arms
  -> threshold 0.1041
  -> product / type / tier / unknown
```

## Package layout

| Path | Purpose |
|---|---|
| `intraspannet/backbone.py` | ByteEmbed and GDN encoder |
| `intraspannet/model.py` | Dual-head classifier and prototype utilities |
| `intraspannet/preprocess.py` | pcap/pcapng to 1600-byte flow vectors |
| `intraspannet/inference.py` | Weight loading, ensemble, thresholding |
| `intraspannet/cli.py` | `classify` and `serve` commands |
| `intraspannet/labels.py` | Label order, display names, type and tier maps |
| `scripts/evaluate.py` | Evaluation on a directory of flow bins |
| `scripts/audit_split_dups.py` | Public split duplicate audit |
| `scripts/audit_split_labels.py` | Cross-split label conflict audit |

## Design decisions

1. Byte-level input, no tokenizer. The model consumes raw bytes. This avoids protocol parsers and keeps the preprocessing deterministic. The cost is a fixed 1600-byte input and no explicit packet-boundary features.
2. First five packets only. The training pipeline and the probe use the same budget. Longer flows are truncated; shorter flows are zero-padded. This keeps inference cheap and matches the deployment constraint.
3. IP masking. IPv4 source and destination addresses are zeroed. The model cannot memorize host addresses. Ports, protocol, headers, and payload remain.
4. Prototype-based open set. The product head is closed-set. A separate prototype distance decides whether to trust it. The threshold is calibrated on dev, not test.
5. Four-arm ensemble. The arms differ in pretraining recipe and loss weighting. Averaging reduces variance. The gate uses two arms whose operating points were stable across dev folds.
6. GPU-only inference. The GDN layer uses Triton kernels. A CPU path would require a separate implementation and is not part of v0.1.0.
7. No data in the repository. Captures are not redistributed. The released weights and a synthetic test capture are sufficient to exercise the pipeline.

## Hardware

- Reference GPU: RTX 4090 24GB.
- Minimum: 4GB VRAM at batch 32.
- Recommended: 8GB VRAM at batch 128.
- Ensemble weights: about 46MB. Activation memory dominates.

## Failure modes

- Unknown products that are close to a known prototype are accepted. The distance and confidence should be reviewed together.
- Products that share a protocol profile can be confused. `stunnel` is the clearest example in the evaluation.
- Flow truncation loses information for long-lived connections.
- A single direction of a connection is classified independently. Asymmetric protocols may produce different labels for each direction.

