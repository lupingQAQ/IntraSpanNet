"""Fine-tune IntraSpanNet on your own captures (stage 2, supervised).

A manifest is a JSONL file, one record per capture:

    {"pcap": "captures/wazuh_day1.pcap", "product": "wazuh_agent"}

Every flow in that capture inherits the product label. The product name must be
one of ``intraspannet.labels.PRODUCTS``; the type and tier labels are derived
from the same table so they cannot drift.

Usage:

    python examples/train_sft.py \
        --weights-dir weights/intraspannet \
        --manifest examples/manifest.example.jsonl \
        --epochs 5 --batch 32 --out runs/sft/arm.pth

Pass --demo to train on random bytes with random labels. That path checks the
plumbing, not the model.

The released arms were trained on 4 x RTX 4090. One arm on a few tens of
thousands of flows fits on a single 24 GB card at batch 32 in bf16.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from intraspannet.labels import PRODUCT_TO_TIER, PRODUCT_TO_TYPE, PRODUCTS
from intraspannet.model import DualHeadClassifier
from intraspannet.preprocess import flow_vectors_from_pcap
from intraspannet.train import SFTConfig, Trainer, load_backbone


def read_manifest(path: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    with open(path, encoding="utf-8-sig") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rec = json.loads(line)
            product = rec["product"]
            if product not in PRODUCTS:
                raise SystemExit(
                    f"{path}:{lineno}: unknown product {product!r}. "
                    f"Known labels: {', '.join(PRODUCTS)}"
                )
            rows.append((rec["pcap"], product))
    if not rows:
        raise SystemExit(f"{path}: no records")
    return rows


def load_flows(rows: list[tuple[str, str]]) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = [], []
    for pcap, product in rows:
        flows = flow_vectors_from_pcap(pcap, min_pkts=1)
        if len(flows) == 0:
            print(f"skip {pcap}: no flows", file=sys.stderr)
            continue
        xs.append(flows)
        ys.append(np.full(len(flows), PRODUCTS.index(product), dtype=np.int64))
        print(f"{pcap}: {len(flows)} flows -> {product}", file=sys.stderr)
    if not xs:
        raise SystemExit("no flows extracted from the manifest")
    return np.concatenate(xs), np.concatenate(ys)


def demo_data(n: int = 512) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(0)
    x = rng.integers(0, 256, size=(n, 1600), dtype=np.uint8)
    y = rng.integers(0, len(PRODUCTS), size=n, dtype=np.int64)
    return x, y


def targets_for(y: torch.Tensor) -> dict[str, torch.Tensor]:
    names = [PRODUCTS[int(i)] for i in y.tolist()]
    return {
        "y_type": torch.tensor([PRODUCT_TO_TYPE[n] for n in names], dtype=torch.long),
        "y_tier": torch.tensor([PRODUCT_TO_TIER[n] for n in names], dtype=torch.long),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights-dir", help="directory with stage3_*.pth; omit to train from scratch")
    ap.add_argument("--arm", default="a_s0", help="which released arm to warm start from")
    ap.add_argument("--manifest", help="JSONL manifest of captures and product labels")
    ap.add_argument("--demo", action="store_true", help="random bytes, random labels")
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--lda", type=float, default=0.0, help="logit adjustment weight (0 = plain)")
    ap.add_argument("--hardneg", type=float, default=0.0, help="hard-negative weight in the contrastive term")
    ap.add_argument("--out", default="runs/sft/arm.pth")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    if args.demo:
        x, y = demo_data()
    elif args.manifest:
        x, y = load_flows(read_manifest(args.manifest))
    else:
        raise SystemExit("pass --manifest or --demo")

    device = torch.device(args.device)
    model = DualHeadClassifier(num_software=len(PRODUCTS))
    if args.weights_dir:
        ckpt = os.path.join(args.weights_dir, f"stage3_{args.arm}.pth")
        model, report = load_backbone(ckpt, model)
        print(
            f"warm start from {ckpt}: {report['loaded']} tensors, "
            f"{len(report['skipped'])} skipped, {len(report['missing'])} left at init",
            file=sys.stderr,
        )
    model.to(device)

    ds = TensorDataset(torch.from_numpy(np.ascontiguousarray(x)).long(), torch.from_numpy(y))
    dl = DataLoader(ds, batch_size=args.batch, shuffle=True, drop_last=False)

    cfg = SFTConfig(lda=args.lda, hardneg=args.hardneg)
    counts = np.bincount(y, minlength=len(PRODUCTS)).astype(np.float32)
    prior = torch.from_numpy(counts / counts.sum())
    trainer = Trainer(model, torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01))

    for epoch in range(1, args.epochs + 1):
        running = 0.0
        for xb, yb in dl:
            xb = xb.to(device)
            yb = yb.to(device)
            batch = {"x": xb, "y_software": yb, "y_malicious": torch.zeros_like(yb)}
            batch.update({k: v.to(device) for k, v in targets_for(yb.cpu()).items()})
            with torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=device.type == "cuda"):
                stats = trainer.step_sft(batch, cfg, class_prior=prior.to(device))
            running += stats["total"]
        print(f"epoch {epoch} loss {running / max(len(dl), 1):.4f}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "classes": PRODUCTS}, args.out)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
