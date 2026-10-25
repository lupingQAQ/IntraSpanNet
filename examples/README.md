# Examples

## Inference

Generate a synthetic capture:

```bash
python examples/make_sample_pcap.py
```

Run the classifier:

```bash
python -m intraspannet.cli classify \
  --pcap examples/sample.pcap \
  --weights-dir weights/intraspannet
```

The capture contains three short flows: a TLS-like TCP flow, a DNS-like UDP flow, and an HTTP-like TCP flow. The payloads are synthetic. The model is expected to reject them as unknown; the example is for checking the preprocessing and inference path, not for measuring accuracy.

## Further training

`train_sft.py` takes a JSONL manifest, one record per capture:

```jsonl
{"pcap": "captures/wazuh_day1.pcap", "product": "wazuh_agent"}
```

Every flow in that capture inherits the product label. `manifest.example.jsonl`
points at the synthetic sample so the path handling can be checked without any
data of your own; it is not a training set.

Supervised fine-tuning from a released arm:

```bash
python examples/train_sft.py \
  --weights-dir weights/intraspannet \
  --manifest examples/manifest.example.jsonl \
  --epochs 5 --batch 32 --lda 1.0 \
  --out runs/sft/arm.pth
```

RL fine-tuning on top of that checkpoint:

```bash
python examples/train_rl.py \
  --manifest examples/manifest.example.jsonl \
  --init runs/sft/arm.pth \
  --epochs 2 --lr 1e-5 \
  --out runs/rl/arm.pth
```

Both scripts write a checkpoint plus, for the RL stage, a prototype file, in the
format the CLI reloads from `--weights-dir`. Add `--demo` to either script to run
on random bytes, which checks the loop end to end without a dataset.

The interface behind the scripts is documented in [../docs/TRAINING.md](../docs/TRAINING.md).
