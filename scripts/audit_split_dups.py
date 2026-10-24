#!/usr/bin/env python3
"""Audit exact flow-level duplicates between train and test directories.

Each directory is expected to contain one subdirectory per class, with files
named *.png (the CSTNET distribution format). The script reports:
  - number of test files whose bytes also appear in train
  - number of test files whose decoded pixels appear in train (requires Pillow)
  - per-class duplicate counts
  - label conflicts (same hash under different class directories)

Example:
  python scripts/audit_split_dups.py --train data/train --test data/test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict

try:
    from PIL import Image
except ImportError:  # pixel hashing is optional
    Image = None


def walk(root: str):
    for cls in sorted(os.listdir(root)):
        cls_dir = os.path.join(root, cls)
        if not os.path.isdir(cls_dir):
            continue
        for name in sorted(os.listdir(cls_dir)):
            path = os.path.join(cls_dir, name)
            if os.path.isfile(path):
                yield cls, path


def md5_bytes(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_pixels(path: str):
    if Image is None:
        return None
    try:
        with Image.open(path) as img:
            return hashlib.md5(img.convert("L").tobytes()).hexdigest()
    except Exception:
        return None


def index(root: str, pixel: bool):
    byte_map = defaultdict(set)
    pixel_map = defaultdict(set)
    for cls, path in walk(root):
        byte_map[md5_bytes(path)].add(cls)
        if pixel:
            h = md5_pixels(path)
            if h:
                pixel_map[h].add(cls)
    return byte_map, pixel_map


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--test", required=True)
    ap.add_argument("--pixel", action="store_true", help="also hash decoded pixels (requires Pillow)")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    train_bytes, train_pixels = index(args.train, args.pixel)
    test_bytes, test_pixels = index(args.test, args.pixel)

    byte_hits = 0
    byte_conflicts = []
    per_class = defaultdict(int)
    for cls, path in walk(args.test):
        h = md5_bytes(path)
        if h in train_bytes:
            byte_hits += 1
            per_class[cls] += 1
            if cls not in train_bytes[h]:
                byte_conflicts.append({"file": path, "test_class": cls, "train_classes": sorted(train_bytes[h])})

    total = sum(1 for _ in walk(args.test))
    result = {
        "train_files": sum(1 for _ in walk(args.train)),
        "test_files": total,
        "byte_overlap": byte_hits,
        "byte_overlap_share": round(byte_hits / total, 4) if total else 0.0,
        "per_class_overlap": dict(sorted(per_class.items())),
        "label_conflicts": len(byte_conflicts),
        "conflict_examples": byte_conflicts[:10],
    }
    if args.pixel:
        pixel_hits = 0
        for _, path in walk(args.test):
            h = md5_pixels(path)
            if h and h in train_pixels:
                pixel_hits += 1
        result["pixel_overlap"] = pixel_hits
        result["pixel_overlap_share"] = round(pixel_hits / total, 4) if total else 0.0

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
