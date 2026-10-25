# Further training

This document covers everything you need to continue training the model on your
own flows: the data contract, the two loss functions, the step driver, and how to
write a checkpoint the CLI can load again. It matches `intraspannet/train.py` in
v0.1.0.

## What ships and what does not

| Shipped | Not shipped |
|---|---|
| `SFTConfig`, `compute_sft_loss` — stage 2 objective | Stage 1 contrastive pretraining script |
| `RLConfig`, `compute_rl_loss` — stage 3 objective | The laboratory capture layout and the 33,184-flow SSL pool |
| `Trainer` — one optimizer step per call | The ensemble search that picked the four arms |
| `load_backbone` — warm start from a released arm | The full three-stage driver |

The reason is data, not code: the released arms were trained on lab captures that
are not redistributable. Everything that depends on your own data is here.

## 1. Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install flash-linear-attention
pip install -e ".[gpu,train]"
```

Training needs the Triton path: the CPU backend is for inference. `pip install "intraspannet[train]"` alone installs the CPU path plus scikit-learn.

The 0.2.0 wheel on PyPI carries this API. `pip install "intraspannet[train]"` also pulls scikit-learn, which the KMeans sub-prototypes need when `k > 1`.

The GDN backbone calls Triton kernels, so training needs a CUDA GPU. The
released ensemble is 2.86 M parameters per arm; the memory ceiling comes from the
1,601-token sequence, not from the parameter count. Start at batch 32 with bf16
autocast and scale up until the card is full.

## 2. The data contract

Both loss functions take a dict of tensors. You keep ownership of the data
loader, the sampler, and the augmentation.

| Key | Shape | Dtype | Required | Meaning |
|---|---|---|---|---|
| `x` | `(B, 1600)` | `int64` | yes | Five packets, 320 bytes each, addresses zeroed |
| `y_software` | `(B,)` | `int64` | yes | Index into `intraspannet.labels.PRODUCTS` |
| `y_type` | `(B,)` | `int64` | yes | Index into `TYPE_NAMES_EN`, 10 classes |
| `y_tier` | `(B,)` | `int64` | yes | 0 security appliance, 1 security software, 2 productivity |
| `y_malicious` | `(B,)` | `int64` | yes | 11 classes, 0 means benign |
| `y_domain` | `(B,)` | `int64` | no | Only used with `grl_alpha > 0` |

You do not label `y_type` and `y_tier` by hand. Both are functions of the product
label:

```python
from intraspannet.labels import PRODUCT_TO_TIER, PRODUCT_TO_TYPE, PRODUCTS

name = PRODUCTS[class_id]
y_type = PRODUCT_TO_TYPE[name]
y_tier = PRODUCT_TO_TIER[name]
```

Converting a capture into `x` uses the same preprocessor as inference:

```python
from intraspannet.preprocess import flow_vectors_from_pcap

flows = flow_vectors_from_pcap("captures/wazuh_day1.pcap", min_pkts=1)  # (N, 1600) uint8
```

A manifest is one JSON object per line. Every flow in a capture inherits the
label, which matches how the lab data was collected — one session per product.

```jsonl
{"pcap": "captures/wazuh_day1.pcap", "product": "wazuh_agent"}
{"pcap": "captures/squid_day2.pcap", "product": "squid_proxy"}
```

## 3. Warm start

Released checkpoints carry an 18-class product head. If you keep those 18 labels
you can load the file directly. If you change the number of classes the head
tensors have a different shape and `load_state_dict` rejects the whole file, so
use `load_backbone`, which copies every tensor whose shape matches and leaves the
rest at initialisation:

```python
from intraspannet.model import DualHeadClassifier
from intraspannet.train import load_backbone

model = DualHeadClassifier(num_software=23)
model, report = load_backbone("weights/intraspannet/stage3_a_s0.pth", model)

print(report["loaded"])    # tensors copied
print(report["skipped"])   # ['software_head.0.weight', 'software_head.5.weight', 'software_head.5.bias']
print(report["missing"])   # model keys left at init
```

The encoder, the type head, the tier head, the malicious head and the projection
head all transfer. Only the resized product head starts from scratch — which is
what you want, since it is the part that has to learn your new classes.

## 4. Supervised stage (stage 2)

### Interface

| Function | Signature |
|---|---|
| `compute_sft_loss` | `(model, batch, cfg=None, class_prior=None, grl_alpha=0.0) -> dict[str, Tensor]` |
| `Trainer.step_sft` | `(batch, cfg=None, **kw) -> dict[str, float]` |

`compute_sft_loss` returns one entry per loss term plus `total`:

| Key | Term |
|---|---|
| `software` | Cross-entropy on the product head |
| `type` | Cross-entropy on the type head |
| `tier` | Cross-entropy on the tier head |
| `malicious` | Cross-entropy on the malicious family head |
| `contrast` | Supervised contrastive loss on the 64-d projection |
| `domain` | Domain-adversarial loss, only when `grl_alpha > 0` and `y_domain` is present |
| `total` | Weighted sum, the tensor you call `backward()` on |

`SFTConfig` holds every weight:

| Field | Default | Effect |
|---|---|---|
| `w_software` | 1.0 | Product head weight |
| `w_type` | 0.5 | Type head weight |
| `w_tier` | 0.3 | Tier head weight |
| `w_malicious` | 0.3 | Malicious head weight |
| `w_contrast` | 0.2 | Contrastive weight |
| `w_domain` | 0.1 | Domain-adversarial weight |
| `lda` | 0.0 | Logit adjustment by class prior; 0 gives the S0 recipe, > 0 gives LDA |
| `hardneg` | 0.0 | Extra weight on close negatives; > 0 gives the HN recipe |
| `hardneg_temp` | 0.1 | Temperature of the contrastive similarity |
| `label_smoothing` | 0.0 | Applied to the four cross-entropy terms |

`lda` needs the training-set class frequency. Pass it as `class_prior`, a
`(C,)` tensor that sums to 1:

```python
counts = torch.bincount(y_software, minlength=len(PRODUCTS)).float()
class_prior = counts / counts.sum()
```

The released arms map onto the three variants directly:

| Arm | Recipe | `SFTConfig` |
|---|---|---|
| `a_s0`, `b_s0` | Plain multi-task | `SFTConfig()` |
| `a_lda`, `b_lda` | Logit adjustment | `SFTConfig(lda=1.0)` + `class_prior` |
| `*_hn` | Hard negatives | `SFTConfig(hardneg=0.5)` |

### Example

`examples/train_sft.py` is a complete loop over a manifest:

```bash
python examples/train_sft.py \
    --weights-dir weights/intraspannet \
    --manifest examples/manifest.example.jsonl \
    --epochs 5 --batch 32 --lda 1.0 \
    --out runs/sft/arm.pth
```

The core of it, without the argument parsing:

```python
import torch
from intraspannet.model import DualHeadClassifier
from intraspannet.train import SFTConfig, Trainer, load_backbone

model = DualHeadClassifier(num_software=18)
model, _ = load_backbone("weights/intraspannet/stage3_a_s0.pth", model)
model.cuda()

cfg = SFTConfig(lda=1.0, hardneg=0.5)
trainer = Trainer(model, torch.optim.AdamW(model.parameters(), lr=1e-4))

for batch in loader:                       # your dict of tensors
    batch = {k: v.cuda() for k, v in batch.items()}
    stats = trainer.step_sft(batch, cfg, class_prior=prior.cuda())
    # stats: {"software": 0.71, "type": 0.23, ..., "total": 1.02}
```

`Trainer` calls `zero_grad`, `backward` and `optimizer.step` for you. If you need
gradient accumulation or a scheduler, call `compute_sft_loss` yourself and keep
the `total` tensor.

## 5. RL stage (stage 3)

### Interface

| Function | Signature |
|---|---|
| `compute_rl_loss` | `(model, batch, cfg=None, prototypes=None) -> dict[str, Tensor]` |
| `Trainer.step_rl` | `(batch, cfg=None, **kw) -> dict[str, float]` |

The policy is the product softmax. At each step one action is sampled per flow,
and the reward is the sum of three terms:

| Term | Value |
|---|---|
| `reward_product` | 1.0 if the sampled product is correct |
| `reward_type` | `reward_type` if the type argmax is correct |
| `reward_abstain` | `reward_abstain` if the prototype distance exceeds the threshold |

| `RLConfig` field | Default | Meaning |
|---|---|---|
| `reward_product` | 1.0 | Weight of the product reward |
| `reward_type` | 0.5 | Weight of the type reward |
| `reward_abstain` | 1.0 | Weight of the honest-rejection reward |
| `threshold` | 0.1041 | Prototype distance above which a flow should be rejected |
| `baseline_decay` | 0.9 | Decay of the running reward mean |
| `entropy_bonus` | 0.0 | Optional entropy term |
| `baseline` | 0.0 | Running mean, updated in place |

`cfg.baseline` is **state**. Reuse one `RLConfig` for the whole run; building a
new one per step resets the baseline to zero and the advantages become raw
rewards, which is both noisier and biased upward at the start.

The `prototypes` argument is optional. Pass it when you have enrolled classes and
want the abstain reward active; skip it to train on the product and type rewards
alone.

### Prototypes and threshold

```python
from intraspannet.model import calibrate_threshold, compute_prototypes

prototypes = compute_prototypes(model, x_train, y_train, device="cuda", k=3)
threshold = calibrate_threshold(model, x_dev, prototypes, device="cuda", percentile=95)
```

`k=3` reproduces the released three sub-prototypes per class. The threshold must
come from data the model has not trained on — the shipped 0.1041 came from the
dev half of the validation split, not from the test half and not from training.

### Example

```bash
python examples/train_rl.py \
    --manifest examples/manifest.example.jsonl \
    --init runs/sft/arm.pth \
    --epochs 2 --lr 1e-5 \
    --out runs/rl/arm.pth
```

RL uses a much smaller learning rate than the supervised stage. The released
recipe started at `1e-5`; a stage-2 learning rate here destroys the encoder
within a few hundred steps.

## 6. Export and evaluate

A checkpoint the CLI can load is a dict with two keys:

```python
torch.save({"model": model.state_dict(), "classes": PRODUCTS}, "runs/sft/stage3_mine.pth")
torch.save({"prototypes": prototypes.cpu(), "classes": PRODUCTS}, "runs/sft/prototypes_mine_k3.pth")
```

`classes` is checked at load time. If it differs from `intraspannet.labels.PRODUCTS`
the loader raises rather than silently mapping your class 7 onto `wireguard`.

Point the CLI at the new files:

```bash
python -m intraspannet.cli classify \
    --pcap captures/day3.pcap \
    --weights-dir runs/sft \
    --threshold 0.1041
```

If the directory holds several arms, `config.json` selects them:

```json
{"cls": ["mine"], "gate": ["mine"], "threshold": 0.1041}
```

## 7. Pitfalls

**Class order.** `PRODUCTS` is the training order stored in the checkpoints. Adding
a label means editing `PRODUCTS`, `PRODUCT_TO_TYPE`, `PRODUCT_TO_TIER`,
`DISPLAY_NAMES` and the type/tier name lists together, then retraining. The
released prototypes and threshold no longer apply to a different label set.

**Head shape.** Use `load_backbone` rather than `load_state_dict` whenever
`num_software` changes. A shape mismatch raises with `strict=False` as well.

**Threshold leakage.** Calibrating the open-set threshold on training flows
produces an optimistically tight threshold and inflates the unknown-rejection
number.

**RL state.** One `RLConfig` per run. See above.

**Autocast.** bf16 autocast on the forward pass is fine and is what the recipes
used, but keep the loss in fp32 — the contrastive term exponentiates similarities
and loses precision in half.

**Batch composition.** The contrastive term needs at least two samples of the same
class in a batch. With 18 classes and a shuffled loader, batch 32 is enough; if
you switch to class-balanced sampling, keep the batches mixed across classes.

## 8. Compute

The released arms were trained on 4 x RTX 4090. A single-arm stage-2 fine-tune
over a few tens of thousands of flows is a few epochs on one 24 GB card at batch
32 with bf16. Stage 3 is cheap by comparison because it samples one action per
flow and keeps the encoder nearly fixed at `1e-5`.
