# IntraSpanNet v0.1.0

Release date: 2026-10-24

## Summary

IntraSpanNet is a byte-level traffic classifier for security product discovery. It identifies 18 security products and services from the first five packets of a flow and rejects unknown products with a prototype-distance threshold. The release contains a four-arm ensemble, a portable inference package, a CLI, an HTTP service, evaluation scripts, and a public-split audit.

## Results

| Metric | Test (503 flows) | All validation (1006 flows) |
|---|---:|---:|
| Product accuracy | 0.8787 | 0.8817 |
| Tier accuracy | 0.9245 | 0.9334 |
| Macro-F1 (supported classes) | 0.7621 | 0.8240 |
| Gate AUROC | 0.9784 | 0.9820 (dev) |

- Unknown rejection: 100% on 18 unknown-product bins.
- Malicious macro-F1: 0.9702 on deduplicated USTC-TFC2016 (n=1242).
- Throughput: 253 flows/s for the ensemble, 1,017 flows/s for a single arm, on an RTX 4090.

## Contents

- `intraspannet/`: model, preprocessing, inference, CLI.
- `scripts/`: evaluation and split-audit tools.
- `docs/`: results, model card, architecture, benchmark audit.
- `space/`: Gradio demo.
- `examples/`: synthetic capture generator.
- Weights: distributed on Hugging Face, not in the Git repository.

## Known limitations

- `stunnel` recall is zero in the acceptance set.
- The test split is flow-level, not session-level.
- CPU inference is not supported.
- Timing rescue is not included.
- Training code is not included in this release.

## Install

```bash
pip install -e .
huggingface-cli download luping123/IntraSpanNet --local-dir weights/intraspannet
python -m intraspannet.cli classify --pcap sample.pcap --weights-dir weights/intraspannet
```

## Links

- Code: https://github.com/lupingQAQ/IntraSpanNet
- Model: https://huggingface.co/luping123/IntraSpanNet
- Space code: `space/` (requires a CUDA GPU; not deployed)

## License

Apache-2.0 for code and weights. CC-BY-4.0 for documentation.
