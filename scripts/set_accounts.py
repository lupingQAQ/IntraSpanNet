#!/usr/bin/env python3
"""Replace account placeholders in the release documents.

Example:
  python scripts/set_accounts.py --github acme --hf acme
"""

from __future__ import annotations

import argparse
import os

TARGETS = [
    "README.md",
    "README.zh-CN.md",
    "CITATION.cff",
    "docs/MODEL_CARD.md",
    "docs/LAUNCH.md",
    "docs/RELEASE_NOTES_v1.0.0.md",
    "docs/social-posts.md",
    "space/README.md",
]


def replace(path: str, github: str, hf: str) -> int:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    original = text
    text = text.replace("github.com/your-org", f"github.com/{github}")
    text = text.replace("huggingface.co/spaces/your-org", f"huggingface.co/spaces/{hf}")
    text = text.replace("huggingface.co/your-org", f"huggingface.co/{hf}")
    text = text.replace("your-org", hf)
    if text != original:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return original.count("your-org")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--github", required=True, help="GitHub user or organization")
    ap.add_argument("--hf", required=True, help="Hugging Face user or organization")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    total = 0
    for rel in TARGETS:
        path = os.path.join(args.root, rel)
        if not os.path.exists(path):
            print(f"skip missing {rel}")
            continue
        n = replace(path, args.github, args.hf)
        total += n
        print(f"{rel}: {n} placeholders replaced")
    print(f"total: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
