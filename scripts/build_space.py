#!/usr/bin/env python3
"""Assemble a Hugging Face Space directory.

Copies the quietspan package, the sample capture, and the weights index into
space/. Run this before uploading space/ to Hugging Face.

Example:
  python scripts/build_space.py --weights weights/quietspan
"""

from __future__ import annotations

import argparse
import os
import shutil


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--space", default="space")
    ap.add_argument("--weights", default="weights/quietspan")
    args = ap.parse_args()

    src_pkg = os.path.join("quietspan")
    dst_pkg = os.path.join(args.space, "quietspan")
    if os.path.exists(dst_pkg):
        shutil.rmtree(dst_pkg)
    shutil.copytree(
        src_pkg,
        dst_pkg,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )

    sample = os.path.join("examples", "sample.pcap")
    if os.path.exists(sample):
        shutil.copy2(sample, os.path.join(args.space, "sample.pcap"))

    dst_weights = os.path.join(args.space, "quietspan")
    if os.path.isdir(args.weights):
        os.makedirs(dst_weights, exist_ok=True)
        for name in ("config.json", "labels.json", "SHA256SUMS"):
            src = os.path.join(args.weights, name)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dst_weights, name))
        print(f"copied package and metadata; weights themselves stay in {args.weights}")
    print(f"space assembled at {args.space}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
