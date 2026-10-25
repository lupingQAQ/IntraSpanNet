#!/usr/bin/env python3
"""Download the released QuietSpan weights from Hugging Face."""

from __future__ import annotations

import argparse
import os

DEFAULT_REPO = "your-org/quietspan"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--out", default="weights/quietspan")
    args = ap.parse_args()

    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise SystemExit("pip install huggingface_hub") from exc

    os.makedirs(args.out, exist_ok=True)
    path = snapshot_download(repo_id=args.repo, local_dir=args.out)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
