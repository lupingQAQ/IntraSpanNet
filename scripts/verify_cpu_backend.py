"""Check the CPU reference path against labelled captures.

The CPU path in ``intraspannet._gdn_cpu`` is a plain PyTorch port of the Triton
Gated DeltaNet block. This script tells you whether the port reproduces the
model's behaviour on your hardware: point it at captures whose product you know
and it reports the hit rate.

    python scripts/verify_cpu_backend.py \
        --weights-dir weights/intraspannet \
        --manifest labelled.jsonl \
        --flows 3

The manifest is the one used for training, one capture per line:

    {"pcap": "captures/osquery_day1.pcap", "product": "osquery"}

A correct port reproduces the product on most flows of a capture it has seen.
Anything near chance means the port is wrong for your fla version, not that the
model is bad.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intraspannet.labels import PRODUCTS  # noqa: E402
from intraspannet.model import DualHeadClassifier  # noqa: E402
from intraspannet.preprocess import flow_vectors_from_pcap  # noqa: E402


def read_manifest(path: str) -> list[tuple[str, str]]:
    rows = []
    with open(path, encoding="utf-8-sig") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rec = json.loads(line)
            if rec["product"] not in PRODUCTS:
                raise SystemExit(f"{path}:{lineno}: unknown product {rec['product']!r}")
            rows.append((rec["pcap"], rec["product"]))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights-dir", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--flows", type=int, default=3, help="flows per capture")
    ap.add_argument("--arm", default="a_s0")
    ap.add_argument("--threads", type=int, default=0, help="torch CPU threads; 0 leaves the default")
    args = ap.parse_args()

    if args.threads:
        torch.set_num_threads(args.threads)

    ckpt_path = os.path.join(args.weights_dir, f"stage3_{args.arm}.pth")
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    model = DualHeadClassifier(num_software=len(PRODUCTS), backend="cpu")
    model.load_state_dict(ckpt["model"], strict=True)
    model.eval()

    hits = total = 0
    for pcap, label in read_manifest(args.manifest):
        flows = flow_vectors_from_pcap(pcap, min_pkts=1)[: args.flows]
        if len(flows) == 0:
            print(f"{pcap}: no flows", file=sys.stderr)
            continue
        preds = []
        with torch.no_grad():
            for flow in flows:
                logits = model(torch.from_numpy(np.ascontiguousarray(flow)).long().unsqueeze(0))["software"]
                preds.append(PRODUCTS[int(logits.argmax())])
        hit = sum(p == label for p in preds)
        hits += hit
        total += len(preds)
        print(f"{os.path.basename(pcap):<40} {label:<20} {hit}/{len(preds)}  {preds}")

    if total == 0:
        print("no flows evaluated", file=sys.stderr)
        return 1
    print(f"\nhit rate {hits}/{total} = {hits / total:.3f}")
    return 0 if hits / total >= 0.5 else 2


if __name__ == "__main__":
    sys.exit(main())
