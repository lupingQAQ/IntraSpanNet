import json
import os
import sys

import gradio as gr
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gdnet.inference import Ensemble
from gdnet.preprocess import flow_vectors_from_pcap

WEIGHTS_DIR = os.environ.get("GDNET_WEIGHTS", os.path.join(os.path.dirname(__file__), "gdnet-v5"))
MODEL_REPO = os.environ.get("GDNET_MODEL", "your-org/gdnet-v5")
_ENGINE = None


def _ensure_weights():
    if os.path.exists(os.path.join(WEIGHTS_DIR, "stage3_v5_b_s0.pth")):
        return
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise gr.Error("huggingface_hub is required to download the weights.") from exc
    snapshot_download(repo_id=MODEL_REPO, local_dir=WEIGHTS_DIR)


def engine():
    global _ENGINE
    if _ENGINE is None:
        if not torch.cuda.is_available():
            raise gr.Error(
                "This Space requires a CUDA GPU. The released model uses Triton kernels "
                "and does not support CPU inference."
            )
        _ensure_weights()
        _ENGINE = Ensemble.from_config(WEIGHTS_DIR)
    return _ENGINE


def classify(file_path):
    if not file_path:
        raise gr.Error("Upload a pcap or pcapng file.")
    flows = flow_vectors_from_pcap(file_path)
    if len(flows) == 0:
        raise gr.Error("No IPv4 TCP or UDP flows found in the capture.")
    rows = engine().classify(flows, topk=3)
    table = pd.DataFrame(
        [
            {
                "tier": r["tier"],
                "type": r["type"],
                "product": r["product"],
                "unknown": r["unknown"],
                "distance": r["distance"],
                "confidence": r["confidence"],
            }
            for r in rows
        ]
    )
    summary = {
        "flows": len(rows),
        "unknown": sum(1 for r in rows if r["unknown"]),
        "products": {},
    }
    for r in rows:
        summary["products"][r["product"]] = summary["products"].get(r["product"], 0) + 1
    return table, json.dumps(summary, ensure_ascii=False, indent=2), json.dumps(rows[:50], ensure_ascii=False, indent=2)


with gr.Blocks(title="GDNet V5") as demo:
    gr.Markdown(
        "# GDNet V5\n"
        "Byte-level traffic classification for security product discovery. "
        "The model identifies 18 security products and services, and rejects unknown products.\n\n"
        "The demo processes the first five packets of each unidirectional flow. "
        "Use only traffic you are authorized to analyze. Do not upload sensitive captures."
    )
    with gr.Row():
        with gr.Column():
            capture = gr.File(label="pcap / pcapng", file_types=[".pcap", ".pcapng", ".cap"])
            run = gr.Button("Classify", variant="primary")
        with gr.Column():
            summary = gr.Textbox(label="Summary", lines=8)
    table = gr.Dataframe(label="Per-flow results", wrap=True)
    raw = gr.Code(label="JSON (first 50 flows)", language="json")

    run.click(classify, inputs=capture, outputs=[table, summary, raw])

    gr.Markdown(
        "Hardware: NVIDIA GPU with CUDA. The GDN backbone uses Triton kernels. "
        "CPU execution is not supported in v1.0.0. "
        "Metrics and limitations: see the model card."
    )


if __name__ == "__main__":
    demo.launch()
