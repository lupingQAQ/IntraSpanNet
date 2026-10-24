# Scripts

| Script | Purpose |
|---|---|
| `evaluate.py` | Accuracy, macro-F1, tier accuracy, and unknown AUROC on a labeled flow set |
| `audit_split_dups.py` | Exact train/test duplicate audit for image-based benchmark splits |
| `audit_split_labels.py` | Cross-split label conflict audit |
| `download_weights.py` | Download the released weights from Hugging Face |

Training code is not included in v1.0.0. The release contains the final checkpoints, the inference path, the evaluation path, and the split audit. The training recipe is documented in `docs/RESULTS.md` and `docs/MODEL_CARD.md`.

`evaluate.py` expects either an `.npz` file with `X`, `y_prod`, optional `y_tier`, and optional `y_unknown`, or a directory of `flow_*.bin` files plus a CSV with `source,label` columns. The `.npz` format matches the internal dataset layout; the CSV format is easier to produce from a new capture set.
