# Examples

Generate a synthetic capture:

```bash
python examples/make_sample_pcap.py
```

Run the classifier:

```bash
python -m gdnet.cli classify \
  --pcap examples/sample.pcap \
  --weights-dir weights/gdnet-v5
```

The capture contains three short flows: a TLS-like TCP flow, a DNS-like UDP flow, and an HTTP-like TCP flow. The payloads are synthetic. The model is expected to reject them as unknown; the example is for checking the preprocessing and inference path, not for measuring accuracy.
