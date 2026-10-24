"""Portable inference for the GDNet V5 ensemble."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import torch
import torch.nn.functional as F

from .labels import PRODUCTS, describe
from .model import DualHeadClassifier
from .preprocess import FLOW_LEN, expand_paths, flow_vectors_from_pcap, flow_vectors_from_paths

DEFAULT_ARMS: tuple[str, ...] = ("b_s0", "a_lda", "b_lda", "a_s0")
DEFAULT_GATE: tuple[str, ...] = ("a_lda", "b_lda")
DEFAULT_THRESHOLD = 0.1041
DEFAULT_BATCH = 64


@dataclass
class Arm:
    name: str
    model: DualHeadClassifier
    prototypes: torch.Tensor

    @property
    def device(self) -> torch.device:
        return next(self.model.parameters()).device


def _check_classes(classes: Sequence[str], source: str) -> None:
    got = [str(c) for c in classes]
    if got != PRODUCTS:
        raise ValueError(
            f"{source}: class order does not match the released label table. "
            f"Expected {len(PRODUCTS)} classes, got {len(got)}."
        )


def load_arm(weights_dir: str, name: str, device: torch.device) -> Arm:
    ckpt_path = os.path.join(weights_dir, f"stage3_v5_{name}.pth")
    proto_path = os.path.join(weights_dir, f"prototypes_v5_{name}3_k3.pth")
    if not os.path.exists(ckpt_path):
        raise FileNotFoundError(ckpt_path)
    if not os.path.exists(proto_path):
        raise FileNotFoundError(proto_path)

    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    _check_classes(ckpt.get("classes", []), ckpt_path)

    model = DualHeadClassifier(
        num_software=len(PRODUCTS),
        num_types=10,
        num_tiers=3,
        num_malicious=11,
    )
    missing, unexpected = model.load_state_dict(ckpt["model"], strict=False)
    if any("software_head" in key for key in missing):
        raise RuntimeError(f"{ckpt_path}: software head is incomplete")

    proto = torch.load(proto_path, map_location="cpu", weights_only=False)
    _check_classes(proto.get("classes", []), proto_path)
    prototypes = F.normalize(proto["prototypes"].float(), dim=-1)

    model.to(device).eval()
    return Arm(name=name, model=model, prototypes=prototypes.to(device))


class Ensemble:
    """Averaged product probabilities and prototype distances over four arms."""

    def __init__(
        self,
        weights_dir: str,
        arms: Iterable[str] = DEFAULT_ARMS,
        gate: Iterable[str] = DEFAULT_GATE,
        threshold: float = DEFAULT_THRESHOLD,
        device: str | None = None,
        batch_size: int = DEFAULT_BATCH,
        allow_cpu: bool = False,
    ):
        self.weights_dir = weights_dir
        self.arms = tuple(arms)
        self.gate = tuple(gate)
        self.threshold = float(threshold)
        self.batch_size = int(batch_size)

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)
        if self.device.type == "cpu" and not allow_cpu:
            raise RuntimeError(
                "GDNet V5 uses Triton GDN kernels and requires a CUDA GPU. "
                "CPU inference is not supported in v1.0.0. "
                "Pass allow_cpu=True only if your flash-linear-attention build has a CPU path."
            )

        names = sorted(set(self.arms) | set(self.gate))
        self._loaded: dict[str, Arm] = {
            name: load_arm(weights_dir, name, self.device) for name in names
        }

    @classmethod
    def from_config(cls, weights_dir: str, config_path: str | None = None, **kwargs) -> "Ensemble":
        config_path = config_path or os.path.join(weights_dir, "config.json")
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as fh:
                cfg = json.load(fh)
            kwargs.setdefault("arms", tuple(cfg.get("cls", DEFAULT_ARMS)))
            kwargs.setdefault("gate", tuple(cfg.get("gate", DEFAULT_GATE)))
            kwargs.setdefault("threshold", float(cfg.get("threshold", DEFAULT_THRESHOLD)))
        return cls(weights_dir, **kwargs)

    @property
    def config(self) -> dict:
        return {
            "cls": list(self.arms),
            "gate": list(self.gate),
            "threshold": self.threshold,
            "device": str(self.device),
        }

    def _forward_arm(self, arm: Arm, x: torch.Tensor) -> tuple[np.ndarray, np.ndarray]:
        with torch.inference_mode():
            out = arm.model(x)
            feat = F.normalize(arm.model.encode(x), dim=-1)
            prob = F.softmax(out["software"], dim=-1)
            dist = 1.0 - (feat @ arm.prototypes.t()).max(dim=-1).values
        return prob.float().cpu().numpy(), dist.float().cpu().numpy()

    def classify(self, flows: np.ndarray, topk: int = 3) -> list[dict]:
        flows = np.asarray(flows)
        if flows.ndim != 2 or flows.shape[1] != FLOW_LEN:
            raise ValueError(f"expected an array of shape (N, {FLOW_LEN}), got {flows.shape}")
        if len(flows) == 0:
            return []

        probs = np.zeros((len(flows), len(PRODUCTS)), dtype=np.float64)
        dists = np.zeros((len(flows), len(self.gate)), dtype=np.float64)

        for i in range(0, len(flows), self.batch_size):
            batch = torch.from_numpy(np.ascontiguousarray(flows[i : i + self.batch_size])).long().to(self.device)
            for name in self.arms:
                p, _ = self._forward_arm(self._loaded[name], batch)
                probs[i : i + len(p)] += p
            for j, name in enumerate(self.gate):
                _, d = self._forward_arm(self._loaded[name], batch)
                dists[i : i + len(d), j] = d
        probs /= len(self.arms)
        mean_dist = dists.mean(axis=1)

        results = []
        for i in range(len(flows)):
            order = np.argsort(-probs[i])[: max(1, int(topk))]
            cls_id = int(order[0])
            product = PRODUCTS[cls_id]
            info = describe(product, lang="zh")
            info_en = describe(product, lang="en")
            unknown = bool(mean_dist[i] > self.threshold)
            results.append(
                {
                    "product": "unknown" if unknown else product,
                    "display": info["display"],
                    "tier": "未知" if unknown else info["tier"],
                    "tier_en": "Unknown" if unknown else info_en["tier"],
                    "type": "未知" if unknown else info["type"],
                    "type_en": "Unknown" if unknown else info_en["type"],
                    "unknown": unknown,
                    "distance": round(float(mean_dist[i]), 4),
                    "confidence": round(float(probs[i, cls_id]), 4),
                    "class_id": None if unknown else cls_id,
                    "topk": [
                        {
                            "product": PRODUCTS[int(k)],
                            "display": describe(PRODUCTS[int(k)], lang="zh")["display"],
                            "probability": round(float(probs[i, int(k)]), 4),
                        }
                        for k in order
                    ],
                }
            )
        return results

    def classify_pcap(self, path: str, min_pkts: int = 1, topk: int = 3) -> list[dict]:
        flows = flow_vectors_from_pcap(path, min_pkts=min_pkts)
        return self.classify(flows, topk=topk)

    def classify_paths(self, patterns: Iterable[str], min_pkts: int = 1, topk: int = 3) -> list[dict]:
        files = expand_paths(patterns)
        if not files:
            raise FileNotFoundError("no pcap files matched")
        flows = flow_vectors_from_paths(files, min_pkts=min_pkts)
        return self.classify(flows, topk=topk)

    def classify_flow_dir(self, directory: str, topk: int = 3) -> list[dict]:
        from .preprocess import iter_flow_bins

        rows = list(iter_flow_bins(directory))
        if not rows:
            raise FileNotFoundError(f"no flow_*.bin files in {directory}")
        flows = np.stack([arr for _, arr in rows])
        results = self.classify(flows, topk=topk)
        for (path, _), row in zip(rows, results):
            row["source"] = os.path.basename(path)
        return results
