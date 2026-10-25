---
title: IntraSpanNet Demo
colorFrom: gray
colorTo: blue
sdk: gradio
sdk_version: 5.0.0
app_file: app.py
pinned: false
models:
  - luping123/IntraSpanNet
---

# IntraSpanNet Demo

Upload a pcap or pcapng file. The app extracts the first five packets of each unidirectional flow and classifies it.

The app requires a CUDA GPU. On a free CPU Space it will show an error instead of running the model. Set `GDNET_WEIGHTS` to the directory containing the downloaded weights, or place them in `intraspannet/` next to `app.py`.

Do not upload sensitive captures.
