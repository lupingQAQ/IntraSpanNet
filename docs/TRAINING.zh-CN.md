# 继续训练

本文说明如何在自己的流量上继续训练：数据契约、两个损失函数、步进接口，以及怎样导出 CLI 能直接加载的 checkpoint。内容对应 v0.1.0 的 `intraspannet/train.py`。

## 发布范围

| 已提供 | 未提供 |
|---|---|
| `SFTConfig`、`compute_sft_loss`（第 2 阶段） | 第 1 阶段对比预训练脚本 |
| `RLConfig`、`compute_rl_loss`（第 3 阶段） | 实验环境抓包目录结构与 33,184 条 SSL 池 |
| `Trainer`（每次调用走一步优化） | 四臂的集成搜索过程 |
| `load_backbone`（从已发布臂热启动） | 三阶段的完整驱动脚本 |

缺的是数据，不是代码。发布的四个臂在不可再分发的实验环境抓包上训练，凡是不依赖那批数据的部分都在这里。

## 1. 环境

```bash
python -m venv .venv
source .venv/bin/activate          # Windows 用 .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install flash-linear-attention
pip install -e ".[gpu,train]"
```

训练要走 Triton 路径，CPU 后端只用于推理。只装 `pip install "intraspannet[train]"` 得到的是 CPU 路径加 scikit-learn。

PyPI 上的 0.2.0 wheel 已包含这套接口。`pip install "intraspannet[train]"` 会一并装上 scikit-learn，`k > 1` 的 KMeans 子原型需要它。

GDN 骨干走 Triton 内核，训练必须有 CUDA GPU。单臂 2.86M 参数，显存瓶颈不在参数量，而在 1601 个 token 的序列长度。建议从 batch 32、bf16 自动混合精度起步，再往上加。

## 2. 数据契约

两个损失函数都接收一个张量字典。数据加载、采样与增强由调用方自己负责。

| 键 | 形状 | 类型 | 必需 | 含义 |
|---|---|---|---|---|
| `x` | `(B, 1600)` | `int64` | 是 | 前 5 个包，每包 320 字节，地址已置零 |
| `y_software` | `(B,)` | `int64` | 是 | `intraspannet.labels.PRODUCTS` 的下标 |
| `y_type` | `(B,)` | `int64` | 是 | 类型标签下标，共 10 类 |
| `y_tier` | `(B,)` | `int64` | 是 | 0 安全设备、1 安全软件、2 正常软件 |
| `y_malicious` | `(B,)` | `int64` | 是 | 恶意家族共 11 类，0 表示良性 |
| `y_domain` | `(B,)` | `int64` | 否 | 仅在 `grl_alpha > 0` 时使用 |

`y_type` 与 `y_tier` 不需要手工标注，它们由产品标签唯一确定：

```python
from intraspannet.labels import PRODUCT_TO_TIER, PRODUCT_TO_TYPE, PRODUCTS

name = PRODUCTS[class_id]
y_type = PRODUCT_TO_TYPE[name]
y_tier = PRODUCT_TO_TIER[name]
```

抓包转 `x` 用与推理同一个预处理器：

```python
from intraspannet.preprocess import flow_vectors_from_pcap

flows = flow_vectors_from_pcap("captures/wazuh_day1.pcap", min_pkts=1)  # (N, 1600) uint8
```

清单文件（manifest）每行一条 JSON，一个抓包里的所有流共用该抓包的产品标签。这与实验环境按产品分会话采集的方式一致：

```jsonl
{"pcap": "captures/wazuh_day1.pcap", "product": "wazuh_agent"}
{"pcap": "captures/squid_day2.pcap", "product": "squid_proxy"}
```

## 3. 热启动

已发布的 checkpoint 带 18 类产品头。沿用这 18 类，可以直接加载；改动类别数后产品头的形状不同，`load_state_dict` 会整体拒绝该文件。用 `load_backbone` 加载：形状一致的张量全部复制，不一致的留在初始化状态。

```python
from intraspannet.model import DualHeadClassifier
from intraspannet.train import load_backbone

model = DualHeadClassifier(num_software=23)
model, report = load_backbone("weights/intraspannet/stage3_a_s0.pth", model)

print(report["loaded"])    # 已复制的张量数
print(report["skipped"])   # ['software_head.0.weight', 'software_head.5.weight', 'software_head.5.bias']
print(report["missing"])   # 仍为初始化的键
```

编码器、类型头、大类头、恶意头、投影头全部可迁移，只有被改过尺寸的产品头从头学。这正是想要的：新类别该由这个头去学。

## 4. 监督阶段（第 2 阶段）

### 接口

| 函数 | 签名 |
|---|---|
| `compute_sft_loss` | `(model, batch, cfg=None, class_prior=None, grl_alpha=0.0) -> dict[str, Tensor]` |
| `Trainer.step_sft` | `(batch, cfg=None, **kw) -> dict[str, float]` |

`compute_sft_loss` 返回每个分项加一个 `total`：

| 键 | 分项 |
|---|---|
| `software` | 产品头交叉熵 |
| `type` | 类型头交叉熵 |
| `tier` | 大类头交叉熵 |
| `malicious` | 恶意家族头交叉熵 |
| `contrast` | 64 维投影上的监督对比损失 |
| `domain` | 域对抗损失，仅当 `grl_alpha > 0` 且 batch 含 `y_domain` |
| `total` | 加权和，反向传播的那个张量 |

`SFTConfig` 的字段：

| 字段 | 默认 | 作用 |
|---|---|---|
| `w_software` | 1.0 | 产品头权重 |
| `w_type` | 0.5 | 类型头权重 |
| `w_tier` | 0.3 | 大类头权重 |
| `w_malicious` | 0.3 | 恶意头权重 |
| `w_contrast` | 0.2 | 对比项权重 |
| `w_domain` | 0.1 | 域对抗权重 |
| `lda` | 0.0 | 按类先验做 logit 调整；0 即 S0，大于 0 即 LDA |
| `hardneg` | 0.0 | 对相近负样本加权；大于 0 即 HN |
| `hardneg_temp` | 0.1 | 对比相似度的温度 |
| `label_smoothing` | 0.0 | 作用于四个交叉熵项 |

`lda` 需要训练集的类别频率，以 `class_prior` 传入，形状 `(C,)` 且和为 1：

```python
counts = torch.bincount(y_software, minlength=len(PRODUCTS)).float()
class_prior = counts / counts.sum()
```

发布臂与三种配方一一对应：

| 臂 | 配方 | 配置 |
|---|---|---|
| `a_s0`、`b_s0` | 标准多任务 | `SFTConfig()` |
| `a_lda`、`b_lda` | logit 调整 | `SFTConfig(lda=1.0)` 并传 `class_prior` |
| `*_hn` | 硬负样本 | `SFTConfig(hardneg=0.5)` |

### 示例

`examples/train_sft.py` 是一个完整循环：

```bash
python examples/train_sft.py \
    --weights-dir weights/intraspannet \
    --manifest examples/manifest.example.jsonl \
    --epochs 5 --batch 32 --lda 1.0 \
    --out runs/sft/arm.pth
```

去掉参数解析后的核心部分：

```python
import torch
from intraspannet.model import DualHeadClassifier
from intraspannet.train import SFTConfig, Trainer, load_backbone

model = DualHeadClassifier(num_software=18)
model, _ = load_backbone("weights/intraspannet/stage3_a_s0.pth", model)
model.cuda()

cfg = SFTConfig(lda=1.0, hardneg=0.5)
trainer = Trainer(model, torch.optim.AdamW(model.parameters(), lr=1e-4))

for batch in loader:                       # 自己构造的张量字典
    batch = {k: v.cuda() for k, v in batch.items()}
    stats = trainer.step_sft(batch, cfg, class_prior=prior.cuda())
    # stats: {"software": 0.71, "type": 0.23, ..., "total": 1.02}
```

`Trainer` 替你调用 `zero_grad`、`backward` 与 `optimizer.step`。要做梯度累积或接学习率调度器，就自己调 `compute_sft_loss` 并对返回的 `total` 反向传播。

## 5. 强化学习阶段（第 3 阶段）

### 接口

| 函数 | 签名 |
|---|---|
| `compute_rl_loss` | `(model, batch, cfg=None, prototypes=None) -> dict[str, Tensor]` |
| `Trainer.step_rl` | `(batch, cfg=None, **kw) -> dict[str, float]` |

策略是产品 softmax。每步为每条流采样一个动作，奖励由三项相加：

| 项 | 取值 |
|---|---|
| `reward_product` | 采样的产品正确，得 1.0 |
| `reward_type` | 类型 argmax 正确，得 `reward_type` |
| `reward_abstain` | 原型距离超过阈值，得 `reward_abstain` |

| `RLConfig` 字段 | 默认 | 含义 |
|---|---|---|
| `reward_product` | 1.0 | 产品奖励权重 |
| `reward_type` | 0.5 | 类型奖励权重 |
| `reward_abstain` | 1.0 | 诚实拒识奖励权重 |
| `threshold` | 0.1041 | 超过该原型距离即应拒识 |
| `baseline_decay` | 0.9 | 奖励滑动均值的衰减 |
| `entropy_bonus` | 0.0 | 可选的熵项 |
| `baseline` | 0.0 | 滑动均值，原地更新 |

`cfg.baseline` 是**状态**。整个训练复用同一个 `RLConfig`；每步新建会把基线清零，优势值退化成原始奖励，噪声更大且训练初期系统性偏高。

`prototypes` 参数可选。已完成注册、希望拒识奖励生效时传入；只训练产品与类型奖励时不传。

### 原型与阈值

```python
from intraspannet.model import calibrate_threshold, compute_prototypes

prototypes = compute_prototypes(model, x_train, y_train, device="cuda", k=3)
threshold = calibrate_threshold(model, x_dev, prototypes, device="cuda", percentile=95)
```

`k=3` 复现发布版的每类三个子原型。阈值必须来自模型没训练过的数据：发布的 0.1041 取自验证集的 dev 半折，既不是 test 半折，也不是训练集。

### 示例

```bash
python examples/train_rl.py \
    --manifest examples/manifest.example.jsonl \
    --init runs/sft/arm.pth \
    --epochs 2 --lr 1e-5 \
    --out runs/rl/arm.pth
```

RL 的学习率比监督阶段小得多。发布配方从 `1e-5` 起步；用监督阶段的学习率跑这一步，几百步内编码器就被破坏。

## 6. 导出与评测

CLI 能加载的 checkpoint 是一个含两个键的字典：

```python
torch.save({"model": model.state_dict(), "classes": PRODUCTS}, "runs/sft/stage3_mine.pth")
torch.save({"prototypes": prototypes.cpu(), "classes": PRODUCTS}, "runs/sft/prototypes_mine_k3.pth")
```

加载时会校验 `classes`。与 `intraspannet.labels.PRODUCTS` 不一致就直接报错，不会把你的第 7 类悄悄映射成 `wireguard`。

用新权重分类：

```bash
python -m intraspannet.cli classify \
    --pcap captures/day3.pcap \
    --weights-dir runs/sft \
    --threshold 0.1041
```

目录内有多个臂时，由 `config.json` 选择：

```json
{"cls": ["mine"], "gate": ["mine"], "threshold": 0.1041}
```

## 7. 常见坑

**类别顺序。** `PRODUCTS` 是 checkpoint 里存的训练顺序。新增标签要同时改 `PRODUCTS`、`PRODUCT_TO_TYPE`、`PRODUCT_TO_TIER`、`DISPLAY_NAMES` 以及类型与大类的名称表，然后重训。原有的原型与阈值对新标签集不再适用。

**产品头形状。** 改动 `num_software` 后必须用 `load_backbone`，不要直接 `load_state_dict`。形状不符时即使 `strict=False` 也会抛错。

**阈值泄漏。** 在训练流上校准开放集阈值，会得到一个偏紧的阈值，把未知拒识率报得虚高。

**RL 状态。** 每次训练一个 `RLConfig`，原因见上。

**混合精度。** 前向用 bf16 自动混合精度没问题，也是发布配方的做法；但损失要留在 fp32。对比项要对相似度取指数，半精度下会掉有效位。

**batch 构成。** 对比项要求同一 batch 内至少有两个同类样本。18 类、随机打乱的 loader，batch 32 足够；若改成按类均衡采样，也要保证 batch 内类别混合。

## 8. 算力

发布的四个臂在 4 张 RTX 4090 上训练。单臂在自己几万条流上做第 2 阶段微调，一张 24GB 卡、batch 32、bf16，几个 epoch 的量级。第 3 阶段相对便宜：每条流只采一个动作，且编码器保持在 `1e-5` 附近几乎不动。
