#!/usr/bin/env python3
"""Evaluate a GDNet ensemble on a labeled flow set.

Accepted inputs:
  - an .npz file with X (N, 1600) uint8 and y_prod (N,) int,
    optionally y_tier (N,) int and y_unknown (N,) 0/1
  - a directory of flow_*.bin files plus --labels CSV with columns source,label

Example:
  python scripts/evaluate.py --weights-dir weights/gdnet-v5 --npz test.npz
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter

import numpy as np

from gdnet.inference import Ensemble
from gdnet.labels import PRODUCT_TO_TIER, PRODUCTS
from gdnet.preprocess import iter_flow_bins


def macro_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    scores = []
    for cls in sorted(set(y_true.tolist())):
        tp = int(((y_true == cls) & (y_pred == cls)).sum())
        fp = int(((y_true != cls) & (y_pred == cls)).sum())
        fn = int(((y_true == cls) & (y_pred != cls)).sum())
        if tp + fp == 0 or tp + fn == 0:
            continue
        precision = tp / (tp + fp)
        recall = tp / (tp + fn)
        scores.append(0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall))
    return float(np.mean(scores)) if scores else 0.0


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Rank-based AUROC. labels: 1 = positive, 0 = negative."""
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(scores)
    ranks = np.empty(len(scores), dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    return float((ranks[labels == 1].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def load_npz(path: str):
    data = np.load(path, allow_pickle=True)
    x = data["X"].astype(np.uint8)
    y = data["y_prod"].astype(int)
    tier = data["y_tier"].astype(int) if "y_tier" in data else None
    unknown = data["y_unknown"].astype(int) if "y_unknown" in data else None
    return x, y, tier, unknown


def load_dir(path: str, labels_csv: str):
    rows = list(iter_flow_bins(path))
    if not rows:
        raise FileNotFoundError(f"no flow_*.bin in {path}")
    names = [os.path.basename(p) for p, _ in rows]
    lookup = {}
    with open(labels_csv, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            lookup[row["source"]] = row["label"]
    missing = [n for n in names if n not in lookup]
    if missing:
        raise ValueError(f"labels missing for {len(missing)} files, e.g. {missing[:3]}")
    x = np.stack([a for _, a in rows])
    y = np.array([PRODUCTS.index(lookup[n]) for n in names], dtype=int)
    return x, y, None, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights-dir", required=True)
    ap.add_argument("--npz", default="")
    ap.add_argument("--flow-dir", default="")
    ap.add_argument("--labels", default="")
    ap.add_argument("--device", default=None)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    if args.npz:
        x, y, tier, unknown = load_npz(args.npz)
    elif args.flow_dir and args.labels:
        x, y, tier, unknown = load_dir(args.flow_dir, args.labels)
    else:
        ap.error("provide --npz, or --flow-dir with --labels")

    engine = Ensemble.from_config(args.weights_dir, device=args.device, batch_size=args.batch)
    rows = engine.classify(x)
    pred = np.array([PRODUCTS.index(r["product"]) if not r["unknown"] else -1 for r in rows])
    known = pred >= 0

    metrics = {
        "n": int(len(y)),
        "accuracy_all": float((pred == y).mean()),
        "coverage": float(known.mean()),
        "accuracy_known": float((pred[known] == y[known]).mean()) if known.any() else 0.0,
        "macro_f1_known": macro_f1(y[known], pred[known]) if known.any() else 0.0,
        "unknown_rate": float((~known).mean()),
        "mean_distance": float(np.mean([r["distance"] for r in rows])),
        "predicted_products": dict(Counter(r["product"] for r in rows)),
    }
    if tier is not None:
        tier_pred = np.array(
            [-1 if p < 0 else PRODUCT_TO_TIER[PRODUCTS[p]] for p in pred],
            dtype=int,
        )
        valid = tier_pred >= 0
        metrics["tier_accuracy"] = float((tier_pred[valid] == tier[valid]).mean()) if valid.any() else 0.0
    if unknown is not None:
        metrics["auroc_unknown"] = auroc(np.array([r["distance"] for r in rows]), unknown)

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"metrics": metrics, "rows": rows}, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
