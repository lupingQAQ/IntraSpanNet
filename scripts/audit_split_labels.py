#!/usr/bin/env python3
"""Report cross-split label conflicts for exact duplicate files.

Each split is a directory with one subdirectory per class. The script hashes
files in both splits and reports hashes that appear under different classes.

Example:
  python scripts/audit_split_labels.py --train data/train --test data/test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict


def walk(root: str):
    for cls in sorted(os.listdir(root)):
        cls_dir = os.path.join(root, cls)
        if not os.path.isdir(cls_dir):
            continue
        for name in sorted(os.listdir(cls_dir)):
            path = os.path.join(cls_dir, name)
            if os.path.isfile(path):
                yield cls, path


def md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--test", required=True)
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    train = defaultdict(set)
    for cls, path in walk(args.train):
        train[md5(path)].add(cls)

    conflicts = []
    for cls, path in walk(args.test):
        h = md5(path)
        if h in train and cls not in train[h]:
            conflicts.append({"file": path, "test_class": cls, "train_classes": sorted(train[h])})

    result = {
        "conflicts": len(conflicts),
        "examples": conflicts[:20],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
