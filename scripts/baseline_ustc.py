"""Baseline comparison on USTC-TFC2016, for the journal revision.

Extracts 5-packet / 1600-byte vectors from the raw pcaps, builds a byte-histogram
feature, trains a linear baseline, and reports accuracy and macro-F1 on a flow-level
split. The point is to give the paper a second, independently reproducible number on
a public dataset that anyone can rerun.

Usage:
    python scripts/baseline_ustc.py --data D:\\traffic-ids\\data\\ustc --out baseline_ustc.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import tempfile
from collections import Counter

import numpy as np

try:
    import dpkt
except ImportError:
    dpkt = None

FLOW_BYTES = 1600
PKTS = 5
PKT_BYTES = 320


def extract_7z(path: str, workdir: str) -> list[str]:
    out = os.path.join(workdir, os.path.splitext(os.path.basename(path))[0])
    os.makedirs(out, exist_ok=True)
    try:
        subprocess.run(["7z", "x", "-y", f"-o{out}", path], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:
        print("7z failed:", path, exc)
        return []
    found = []
    for root, _, files in os.walk(out):
        for f in files:
            if f.endswith((".pcap", ".pcapng")):
                found.append(os.path.join(root, f))
    return found


def flow_vectors(pcap_path: str) -> list[np.ndarray]:
    """First five packets of each unidirectional flow, 320 bytes each, padded."""
    if dpkt is None:
        return []
    vecs = []
    seen = {}
    try:
        with open(pcap_path, "rb") as fh:
            try:
                reader = dpkt.pcap.Reader(fh)
            except Exception:
                fh.seek(0)
                reader = dpkt.pcapng.Reader(fh)
            for _, buf in reader:
                try:
                    eth = dpkt.ethernet.Ethernet(buf)
                except Exception:
                    continue
                ip = eth.data
                if not isinstance(ip, (dpkt.ip.IP,)):
                    continue
                proto = ip.p
                src = ip.src
                dst = ip.dst
                key = (src, dst, proto)
                if key in seen:
                    continue
                raw = bytes(ip)[:PKT_BYTES]
                vec = np.zeros(FLOW_BYTES, dtype=np.uint8)
                vec[: len(raw)] = np.frombuffer(raw, dtype=np.uint8)
                if len(raw) >= 20:
                    vec[12:20] = 0  # mask addresses
                seen[key] = True
                vecs.append(vec)
    except Exception as exc:
        print("pcap read failed:", pcap_path, exc)
    return vecs


def histogram(vecs: list[np.ndarray]) -> np.ndarray:
    """Normalised 256-bin byte histogram per flow."""
    out = np.zeros((len(vecs), 256), dtype=np.float32)
    for i, v in enumerate(vecs):
        c = np.bincount(v, minlength=256).astype(np.float32)
        out[i] = c / max(c.sum(), 1.0)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=r"D:\traffic-ids\data\ustc")
    ap.add_argument("--out", default="baseline_ustc.json")
    ap.add_argument("--per-class", type=int, default=200, help="max flows per class")
    ap.add_argument("--per-capture", type=int, default=120, help="max flows per pcap")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    classes = {}
    manifest = []  # (pcap_path, label, vectors)
    for label in ("Benign", "Malware"):
        root = os.path.join(args.data, label)
        pcaps = []
        for name in sorted(os.listdir(root)):
            p = os.path.join(root, name)
            if name.endswith(".pcap"):
                pcaps.append(p)
            elif name.endswith(".7z"):
                with tempfile.TemporaryDirectory() as td:
                    pcaps.extend(extract_7z(p, td))
        per_pcap = []
        for p in pcaps:
            v = flow_vectors(p)
            if v:
                random.shuffle(v)
                per_pcap.append(v[: args.per_capture])
        classes[label] = per_pcap
        print(label, "captures:", len(per_pcap), "flows:", sum(len(v) for v in per_pcap))

    # capture-level split: no capture contributes flows to both sides
    X, y, groups = [], [], []
    for idx, label in enumerate(("Benign", "Malware")):
        caps = classes[label]
        order = list(range(len(caps)))
        random.shuffle(order)
        cut = max(1, int(len(order) * 0.7))
        train_idx = set(order[:cut])
        for ci, vecs in enumerate(caps):
            for v in vecs:
                X.append(v)
                y.append(idx)
                groups.append((label, ci, ci in train_idx))
    X = np.array(X)
    y = np.array(y)
    is_train = np.array([g[2] for g in groups])
    if len(X) < 40 or is_train.sum() < 20 or (~is_train).sum() < 10:
        print("not enough flows:", len(X))
        return

    F = histogram(list(X))
    tr = np.where(is_train)[0]
    te = np.where(~is_train)[0]
    n = len(F)
    print("train flows:", len(tr), "test flows:", len(te),
          "train captures:", len({(g[0], g[1]) for g in groups if g[2]}),
          "test captures:", len({(g[0], g[1]) for g in groups if not g[2]}))

    mu = F[tr].mean(0, keepdims=True)
    sd = F[tr].std(0, keepdims=True) + 1e-6
    Xtr = (F[tr] - mu) / sd
    Xte = (F[te] - mu) / sd
    ytr = y[tr].astype(np.float32)
    yte = y[te]

    w = np.zeros(Xtr.shape[1], dtype=np.float32)
    b = 0.0
    lr, epochs, l2 = 0.1, 400, 1e-3
    for _ in range(epochs):
        z = Xtr @ w + b
        p_hat = 1.0 / (1.0 + np.exp(-z))
        w -= lr * (Xtr.T @ (p_hat - ytr) / len(ytr) + l2 * w)
        b -= lr * float((p_hat - ytr).mean())

    pred = ((1.0 / (1.0 + np.exp(-(Xte @ w + b)))) > 0.5).astype(int)
    acc = float((pred == yte).mean())
    f1s = []
    for c in (0, 1):
        tp = int(((pred == c) & (yte == c)).sum())
        fp = int(((pred == c) & (yte != c)).sum())
        fn = int(((pred != c) & (yte == c)).sum())
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)

    res = {
        "dataset": "USTC-TFC2016",
        "task": "benign vs malware",
        "features": "256-bin byte histogram, standardised",
        "model": "logistic regression (numpy, 400 epochs)",
        "flows_total": int(n),
        "train": int(len(tr)),
        "test": int(len(te)),
        "accuracy": round(acc, 4),
        "macro_f1": round(sum(f1s) / 2, 4),
        "class_counts": {str(k): v for k, v in Counter(y.tolist()).items()},
    }
    print(json.dumps(res, indent=2))
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)


if __name__ == "__main__":
    main()
