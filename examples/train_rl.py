"""Reinforcement-learning fine-tuning (stage 3) on top of a supervised arm.

Stage 3 samples a product from the softmax and rewards three things: the product
being right, the type being right, and an honest rejection when the flow sits
far from every prototype. A running mean of the reward is the baseline, so keep
one ``RLConfig`` alive for the whole run instead of rebuilding it per step.

Usage:

    python examples/train_rl.py \
        --weights-dir weights/intraspannet \
        --manifest examples/manifest.example.jsonl \
        --init runs/sft/arm.pth \
        --epochs 2 --out runs/rl/arm.pth

The prototypes and the threshold come from the data you pass in. The shipped
value 0.1041 was calibrated on the dev half of the validation split; do not
reuse it for a different label set.
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

from intraspannet.labels import PRODUCT_TO_TYPE, PRODUCTS
from intraspannet.model import DualHeadClassifier, calibrate_threshold, compute_prototypes
from intraspannet.preprocess import flow_vectors_from_pcap
from intraspannet.train import RLConfig, Trainer, load_backbone


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
                raise SystemExit(f"{path}:{lineno}: unknown product {product!r}")
            rows.append((rec["pcap"], product))
    return rows


def load_flows(rows: list[tuple[str, str]]) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = [], []
    for pcap, product in rows:
        flows = flow_vectors_from_pcap(pcap, min_pkts=1)
        if len(flows) == 0:
            continue
        xs.append(flows)
        ys.append(np.full(len(flows), PRODUCTS.index(product), dtype=np.int64))
    if not xs:
        raise SystemExit("no flows extracted from the manifest")
    return np.concatenate(xs), np.concatenate(ys)


def demo_data(n: int = 512) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(1)
    x = rng.integers(0, 256, size=(n, 1600), dtype=np.uint8)
    y = rng.integers(0, len(PRODUCTS), size=n, dtype=np.int64)
    return x, y


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights-dir", help="released weights, used when --init is absent")
    ap.add_argument("--arm", default="a_s0")
    ap.add_argument("--init", help="checkpoint from examples/train_sft.py")
    ap.add_argument("--manifest")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-5, help="RL uses a much smaller step than SFT")
    ap.add_argument("--threshold-percentile", type=float, default=95.0)
    ap.add_argument("--k", type=int, default=3, help="sub-prototypes per class; k > 1 needs scikit-learn")
    ap.add_argument("--reward-ratio", type=float, default=0.5, help="weight of the type reward")
    ap.add_argument("--out", default="runs/rl/arm.pth")
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
    if args.init:
        model, report = load_backbone(args.init, model)
        print(f"init from {args.init}: {report['loaded']} tensors", file=sys.stderr)
    elif args.weights_dir:
        ckpt = os.path.join(args.weights_dir, f"stage3_{args.arm}.pth")
        model, report = load_backbone(ckpt, model)
        print(f"warm start from {ckpt}: {report['loaded']} tensors", file=sys.stderr)
    model.to(device)

    xt = torch.from_numpy(np.ascontiguousarray(x)).long()
    yt = torch.from_numpy(y)

    # Prototypes and threshold come from the data at hand. In a real run use a
    # held-out slice for the threshold, never the samples you train on.
    try:
        prototypes = compute_prototypes(model, xt, yt, device=str(device), k=args.k).to(device)
    except ImportError as exc:
        raise SystemExit(
            f"k={args.k} needs scikit-learn for the KMeans sub-prototypes: pip install scikit-learn, "
            f"or pass --k 1"
        ) from exc
    threshold = calibrate_threshold(
        model, xt, prototypes, device=str(device), percentile=args.threshold_percentile
    )
    print(f"prototypes {tuple(prototypes.shape)}, threshold {threshold:.4f}", file=sys.stderr)

    cfg = RLConfig(
        reward_product=1.0,
        reward_type=args.reward_ratio,
        reward_abstain=1.0,
        threshold=threshold,
    )
    trainer = Trainer(model, torch.optim.AdamW(model.parameters(), lr=args.lr))

    names = [PRODUCTS[int(i)] for i in y.tolist()]
    y_type = torch.tensor([PRODUCT_TO_TYPE[n] for n in names], dtype=torch.long)
    ds = TensorDataset(xt, yt, y_type)
    dl = DataLoader(ds, batch_size=args.batch, shuffle=True)

    for epoch in range(1, args.epochs + 1):
        loss_sum = 0.0
        reward_sum = 0.0
        for xb, yb, ytb in dl:
            batch = {"x": xb.to(device), "y_software": yb.to(device), "y_type": ytb.to(device)}
            stats = trainer.step_rl(batch, cfg, prototypes=prototypes)
            loss_sum += stats["total"]
            reward_sum += stats["reward"]
        n = max(len(dl), 1)
        print(f"epoch {epoch} loss {loss_sum / n:.4f} reward {reward_sum / n:.4f} baseline {cfg.baseline:.4f}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "classes": PRODUCTS}, args.out)
    torch.save({"prototypes": prototypes.detach().cpu(), "classes": PRODUCTS}, args.out.replace(".pth", "_prototypes_k3.pth"))
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
