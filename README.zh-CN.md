# IntraSpanNet

[English](README.md) | **简体中文**

面向安全产品发现的字节级流量分类模型。

IntraSpanNet 从一条流的前 5 个包识别安全产品与服务，输出产品、类型、大类，并对不在已知类别中的流量给出未知告警。发布版本为四臂集成，单臂 2.86M 参数。

- 模型：[Hugging Face 上的 intraspannet](https://huggingface.co/luping123/IntraSpanNet)
- 论文：[中文 PDF](paper/IntraSpanNet-zh.pdf)、[英文 PDF](paper/IntraSpanNet.pdf)
- 项目主页：https://lupingQAQ.github.io/IntraSpanNet/
- 演示：暂未部署。Space 代码在 `space/`，需要 CUDA GPU。
- 技术报告：[docs/RESULTS.md](docs/RESULTS.md)
- 基准审计：[docs/BENCHMARK_AUDIT.md](docs/BENCHMARK_AUDIT.md)

**DOI:** [10.5281/zenodo.23643146](https://zenodo.org/records/23643146)

## 能力

输入为一条单向流，取前 5 个包，每包 320 字节，共 1600 字节。每包由 80 字节 IPv4 与传输层头、240 字节载荷组成。IPv4 源地址与目的地址置零。

每条流的输出：

| 字段 | 含义 |
|---|---|
| `tier` | 安全设备、安全软件、正常软件 |
| `type` | WAF、上网行为管理、堡垒机、NDR、零信任/VPN、EDR/HIDS、杀毒、浏览器、文件传输、远程管理 |
| `product` | 18 个产品标签之一，或 `unknown` |
| `distance` | 到最近类原型的余弦距离 |
| `confidence` | 四个分类臂的平均 softmax 概率 |
| `topk` | 概率最高的三个产品 |

当平均原型距离超过 `0.1041` 时判为未知。阈值在验证集的 dev 半折上校准，未在 test 半折上调参。

## 结果

最终系统使用分类臂 `b_s0`、`a_lda`、`b_lda`、`a_s0`，门控臂 `a_lda`、`b_lda`。

| 指标 | test（503 流） | 全验证集（1006 流） |
|---|---:|---:|
| 产品准确率 | 0.8787 | 0.8817 |
| 大类准确率 | 0.9245 | 0.9334 |
| Macro-F1（有支撑类） | 0.7621 | 0.8240 |
| 门控 AUROC | 0.9784 | 0.9820（dev） |

其他结果：

- 恶意家族 macro-F1：0.9702，USTC-TFC2016 去重测试集，n=1242。
- 未知拒识：18 个未知产品 bins 全部拒识。q=0.64 至 0.75 区间内操作点稳定。
- 验收 demo：含时序救援 9/10，不含时序救援 8/10；未知拒识 100%。
- 端到端服务：已知流 6/6。Few-shot 注册：注册 3 个子原型后 8/8。
- 吞吐：四臂集成在 batch 32 及以上约 253 flows/s；单臂约 1017 flows/s。batch 1 延迟分别为 43.1ms 与 10.7ms。
- 显存：RTX 4090 上 batch 128 峰值约 3.4GB；集成权重合计约 46MB。

test 集为验证集的流级半折，不是会话级留出。每个产品类只有 1 个留出会话，绝对指标的强度受此限制。完整协议与区间见 [docs/RESULTS.md](docs/RESULTS.md)。

## 快速开始

环境要求：

- Python 3.10 及以上。
- PyTorch。带 CUDA 与 `flash-linear-attention` 是快路径；纯 CPU 安装也能跑。

CPU 走一份纯 PyTorch 的 GDN 移植，单臂约 2 秒一条流，四臂集成约 10 秒一条流。GPU 上的 Triton 内核快三个数量级，那才是部署形态。`scripts/verify_cpu_backend.py` 可以拿你自己有标签的抓包验证这份 CPU 移植，直接给出命中率。

```bash
git clone https://github.com/lupingQAQ/IntraSpanNet.git
cd IntraSpanNet
python -m venv .venv
source .venv/bin/activate
pip install -e .            # 默认即可在 CPU 上跑
pip install -e ".[gpu]"     # 加上 flash-linear-attention 走 Triton 快路径
```

不想克隆仓库的话，`pip install intraspannet` 能从 PyPI 装同一份代码，权重仍从 Hugging Face 下载。

下载权重：

```bash
huggingface-cli download luping123/IntraSpanNet --local-dir weights/intraspannet
```

分类一个抓包文件：

```bash
python -m intraspannet.cli classify \
  --pcap sample.pcap \
  --weights-dir weights/intraspannet \
  --json results.json
```

加 `--device cpu` 强制走 CPU；只想快速看一眼输出，再加 `--arms a_s0 --gate a_s0` 用单臂。

命令会打印每条流的结果与汇总。`--json` 输出完整记录。

服务模式：

```bash
python -m intraspannet.cli serve --weights-dir weights/intraspannet --port 9012
```

服务接收 `POST /`，请求体为一个或多个 1620 字节的 `FLW1` 记录，返回 JSON 数组。

## 输入格式

- 以太网、IPv4、TCP 或 UDP。
- 每条单向流按源地址、源端口、目的地址、目的端口、协议区分。
- 取前 5 个包，按抓包顺序排列。
- 每包取 80 字节 IP 与传输层头，加 240 字节载荷。
- 短包与短流补零。
- 每 1600 字节流的第 12 至 20 字节为 IPv4 源地址与目的地址，置零。

支持 `pcap`、`pcapng` 与 `cap`。预处理使用 dpkt。

## 模型结构

![架构图](docs/assets/architecture.svg)

```
bytes (1600)
  -> ByteEmbed (256)
  -> [bytes, CLS] 加位置编码
  -> 4 个 GDN Block（d_model=256, d_state=16）
  -> CLS 特征 (256)
  -> 产品头 (18)、类型头 (10)、大类头 (3)、恶意头 (11)
```

开放集判定使用每类 3 个子原型。对特征 `f` 与原型矩阵 `P`，距离为 `1 - max(cos(f, P))`。门控对两个门控臂的距离取平均。

四个分类臂结构相同，差异在预训练配方、损失权重与硬负样本采样。集成对 softmax 输出与原型距离取平均。

## 训练

发布版本的四个臂由三个阶段产生：

| 阶段 | 数据 | 目标 |
|---|---|---|
| 1. 对比预训练 | 33,184 条纯训练流 | NT-Xent / SimCLR |
| 2. 多任务 SFT | 产品、基准、恶意训练流 | 产品、类型、大类、恶意、域对抗损失 |
| 3. RL 微调 | 训练 split，奖励塑形 | 产品正确、类型正确、诚实拒识 |

第 2、3 阶段以稳定 API 形式提供，可以在自己的抓包上继续训练：

| 接口 | 作用 |
|---|---|
| `SFTConfig` | 监督阶段的各项损失权重 |
| `compute_sft_loss` | 多任务监督损失，返回每个分项与 `total` |
| `RLConfig` | REINFORCE 阶段的奖励权重 |
| `compute_rl_loss` | 带滑动均值基线的 REINFORCE 目标 |
| `Trainer` | 每次调用走一步优化，两个阶段通用 |
| `load_backbone` | 从已发布臂热启动，自动适配改过尺寸的产品头 |

```python
import torch
from intraspannet.model import DualHeadClassifier
from intraspannet.train import SFTConfig, Trainer, load_backbone

model = DualHeadClassifier(num_software=18)
model, report = load_backbone("weights/intraspannet/stage3_a_s0.pth", model)
model.cuda()

cfg = SFTConfig(lda=1.0, hardneg=0.5)
trainer = Trainer(model, torch.optim.AdamW(model.parameters(), lr=1e-4))

batch = {
    "x": flows.cuda(),                       # (B, 1600) int64
    "y_software": y.cuda(),                  # labels.PRODUCTS 的下标
    "y_type": y_type.cuda(),                 # 由 PRODUCT_TO_TYPE 得到
    "y_tier": y_tier.cuda(),                 # 由 PRODUCT_TO_TIER 得到
    "y_malicious": torch.zeros_like(y).cuda(),
}
stats = trainer.step_sft(batch, cfg, class_prior=prior.cuda())
```

两个可直接运行的脚本，输入是一份「抓包 + 产品标签」的 JSONL 清单：

```bash
python examples/train_sft.py --weights-dir weights/intraspannet \
    --manifest examples/manifest.example.jsonl --epochs 5 --out runs/sft/arm.pth

python examples/train_rl.py --manifest examples/manifest.example.jsonl \
    --init runs/sft/arm.pth --epochs 2 --lr 1e-5 --out runs/rl/arm.pth
```

完整说明见 [docs/TRAINING.zh-CN.md](docs/TRAINING.zh-CN.md)：batch 契约、每个配置字段、原型与阈值校准、导出成 CLI 可重新加载的格式，以及几个容易踩的坑。

训练数据来自 18 个产品与服务的实验环境抓包，以及公开基准训练 split。SSL 池不含验证集与留出集。验证集按流级拆分为 dev 与 test，选择、阈值校准与集成选择仅使用 dev。

训练使用 4 张 RTX 4090，发布 checkpoint 为最终四臂。第 1 阶段依赖实验环境的抓包目录结构，未包含在发布内容里；继续训练建议直接从已发布的臂起步。

## 评测协议

- 产品与大类准确率：test 半折（503 流）与全验证集（1006 流）上的流级准确率。
- Macro-F1：对 test 中有样本的类计算 macro-F1。小类会放大波动，全验证集数值更稳定。
- 开放集 AUROC：已知产品流对未知与新颖流。
- 未知拒识：固定阈值下被拒识的未知产品 bins 比例。
- 恶意检测：USTC-TFC2016 去重测试 split 上的 macro-F1。

报告同时包含泄漏审计。六个公开基准中有五个的 train/test 存在约 80% 的字节级全同重复，Tor 为 0%。报告中的基准对比均使用同一 split，相对结论属于同协议对比，绝对基准准确率不能作为泛化证据。审计脚本与干净子集清单在报告归档中。

## 局限

- `stunnel` 是验收中唯一零召回的产品（0/30），需要注册或补充数据。
- test 为流级拆分，不是会话级拆分。每类只有 1 个留出会话，会话级泛化未测量。
- 9/10 验收结果中的时序救援规则未包含在 v0.1.0。发布集成单独复现的是 8/10。
- 移动端与 IoT 基准不在目标范围内。目标范围为 PC、服务器与内网设备。
- 模型在实验环境流量上训练。生产网络中软件版本、代理、NAT 配置不同，效果未知。
- CPU 推理走 PyTorch 移植，单臂约 2 秒一条流，用于排查，不适合挂到探针上实时跑。
- 蒸馏学生模型仅用于实验，比集成低 5.6 个百分点，不作为推荐部署形态。

## 数据与隐私

仓库不包含抓包。发布权重使用实验环境流量与公开基准训练 split 训练，不含客户流量。不要向公共演示上传敏感抓包。

## 许可证

代码与权重：Apache-2.0。文档：CC-BY-4.0。见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。

## 引用

```bibtex
@software{luping2026intraspannet,
  author = {luping},
  title  = {IntraSpanNet: 不主动扫描识别内网安全设备、终端安全产品与常用软件},
  year   = {2026},
  doi    = {10.5281/zenodo.23643146},
  url    = {https://github.com/lupingQAQ/IntraSpanNet},
  note   = {模型：https://huggingface.co/luping123/IntraSpanNet}
}
```

## 致谢

字节级骨干沿用 MambaNetBurst 的架构。GDN 层由 flash-linear-attention 提供。详见 [NOTICE](NOTICE)。
