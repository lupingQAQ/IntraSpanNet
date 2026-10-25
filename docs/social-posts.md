# Social posts

Account names are set to GitHub `lupingQAQ` and Hugging Face `luping123`. Keep the limitations in the same post.

## X thread

1/6
We audited the public traffic-classification benchmarks used in our comparison table. Five of six have about 80% byte-identical train/test overlap. Tor is 0%. The audit scripts and deduplicated results are in the release.

2/6
We also trained a 2.86M-parameter byte-level model for security product discovery. It takes the first five packets of a flow, identifies 18 security products and services, and rejects unknown products with a prototype-distance threshold.

3/6
Test results: product accuracy 0.8787, tier accuracy 0.9245, gate AUROC 0.9784. Unknown rejection is 100% on 18 bins. The test split is 503 flows, flow-level, one held-out session per class.

4/6
Known failures: stunnel 0/30. CPU inference is not supported; the GDN backbone uses Triton kernels and needs CUDA. The 9/10 acceptance result uses an internal timing rule that is not in v0.1.0. The released model reproduces 8/10.

5/6
Code and weights: Apache-2.0. Weights on Hugging Face. The repository contains no captures. Model card, results, and the split audit are in the repo.

6/6
If you maintain a public traffic dataset, deduplicate across splits before release. If you report a benchmark number, state whether the split contains duplicates. That matters more than another decimal place.

## LinkedIn

We released QuietSpan, a byte-level traffic classifier for security product discovery, together with an audit of the public benchmark splits used for comparison.

The audit found that five of six widely used traffic-classification benchmarks contain about 80% byte-identical flows in both train and test. Tor is the exception at 0%. This inflates absolute accuracy and makes cross-paper comparisons harder to interpret. The release includes the audit scripts and a deduplicated evaluation.

The model has 2.86M parameters per arm and uses the first five packets of a flow. It identifies 18 security products and services and rejects unknown products with a prototype-distance threshold. On the held-out test half, product accuracy is 0.8787 and gate AUROC is 0.9784. Unknown rejection is 100% on 18 unknown-product bins.

The limits are documented: stunnel has zero recall, the test split is flow-level rather than session-level, and CPU inference is not supported. Code and weights are Apache-2.0. The repository contains no captures.

Links: GitHub and Hugging Face.

## Show HN

Title: Show HN: QuietSpan – byte-level traffic classification with a public-split audit

Body:

I released a small traffic classifier and an audit of the public benchmarks used to compare it.

The audit: five of six public traffic-classification splits contain about 80% byte-identical train/test flows. Tor is 0%. The scripts hash file bytes and decoded pixels. The overlap is a property of the distributed splits, not of a single paper.

The model: 2.86M parameters per arm, four-arm ensemble, first five packets of a unidirectional flow, IPv4 addresses masked. It identifies 18 security products and services and rejects unknown products with a prototype-distance threshold.

Results on a 503-flow flow-level test split: product accuracy 0.8787, tier accuracy 0.9245, gate AUROC 0.9784. Unknown rejection is 100% on 18 bins. stunnel is 0/30.

Constraints: CUDA GPU required; the GDN backbone uses Triton kernels. CPU inference is not supported. The test split is flow-level, not session-level. Training code is not included in v0.1.0.

Code and weights are Apache-2.0. No captures are redistributed. Happy to answer questions about the audit method or the open-set path.

## r/netsec

Title: QuietSpan: identifying security products from the first five packets, with a public benchmark split audit

Body:

I released a model that identifies security products and services from the first five packets of a flow, plus an audit of the public benchmarks used for comparison.

The audit is the part I would read first. Five of six public splits contain about 80% byte-identical train/test flows. Tor is 0%. The scripts are in the repo; they hash PNG bytes and decoded pixels. This affects any paper evaluated on the same files.

The model is a 2.86M-parameter byte-level GDN classifier. It outputs product, type, tier, prototype distance, and confidence. Unknown products are rejected at a calibrated distance threshold. The four-arm ensemble reaches 0.8787 product accuracy on a 503-flow test split. Unknown rejection is 100% on 18 bins.

Known issues: stunnel is 0/30, CPU inference is not supported, and the test split is flow-level. I am not claiming SOTA.

Code and weights are Apache-2.0. No captures are included. Feedback on the audit method or the open-set calibration is welcome.

## r/MachineLearning

Title: [P] QuietSpan: a 2.86M-parameter byte-level traffic classifier, plus an 80% train/test overlap audit

Body:

I released a small byte-level model for security product discovery and an audit of the public splits used in the comparison.

Model: ByteEmbed, four Gated DeltaNet blocks, four heads, prototype-based open-set rejection. Input is 1600 bytes (five packets, 320 bytes each, IPv4 masked). The ensemble has four arms. Test product accuracy is 0.8787; gate AUROC is 0.9784; unknown rejection is 100% on 18 bins. stunnel is the known failure.

Audit: five of six public traffic-classification splits contain about 80% exact train/test overlap. Tor is 0%. The scripts use file-byte and decoded-pixel hashes. This is a data-distribution property, not a model property. The release includes a deduplicated evaluation.

Limits: flow-level test split, one held-out session per class, no CPU path, no training code in v0.1.0. Code and weights are Apache-2.0.

I would be interested in feedback on the open-set calibration and on whether the audit method misses near-duplicates.

## Zhihu

我们发布了一个流量分类模型 QuietSpan，以及一份公开基准 split 审计。

审计发现，六个常用流量分类基准中有五个的 train/test 存在约 80% 的字节级全同流，Tor 为 0%。这不是某一篇论文的问题，而是数据分发时的采样方式导致的。所有在同一批文件上评测的方法都受影响。仓库里包含审计脚本与去重后的评测结果。

模型单臂 2.86M 参数，输入为一条流的前 5 个包，共 1600 字节，识别 18 个安全产品与服务，并用原型距离拒识未知产品。test 上产品准确率 0.8787，门控 AUROC 0.9784，18 个未知 bins 全部拒识。stunnel 为 0/30，是已知缺陷。

代码与权重使用 Apache-2.0，仓库不含抓包。CPU 推理不支持，GDN 骨干需要 CUDA。

## FreeBuf / 安全客

开源了一个面向安全产品发现的流量分类模型 QuietSpan。输入为一条流的前 5 个包，输出产品、类型、大类与未知告警。单臂 2.86M 参数，四臂集成，原型距离拒识未知产品。

同时发布了一份公开基准审计：六个常用流量分类基准中，五个的 train/test 存在约 80% 的字节级全同流，Tor 为 0%。审计脚本与去重评测一并开源。

test 产品准确率 0.8787，门控 AUROC 0.9784，未知拒识 100%（18 bins）。stunnel 0/30，CPU 推理不支持，test 为流级拆分。代码与权重 Apache-2.0，仓库不含抓包。

## V2X

发布 QuietSpan：从一条流的前 5 个包识别 18 个安全产品与服务，支持未知拒识。单臂 2.86M 参数，四臂集成。

同时开源公开基准审计：六个常用流量分类基准中五个的 train/test 重叠约 80%，Tor 为 0%。

代码与权重 Apache-2.0，仓库不含抓包。CPU 推理不支持。test 产品准确率 0.8787，stunnel 0/30 为已知缺陷。

## WeChat

QuietSpan 已开源。模型从一条流的前 5 个包识别 18 个安全产品与服务，并用原型距离拒识未知产品。单臂 2.86M 参数，四臂集成。

随模型发布的还有一份公开基准审计：六个常用流量分类基准中，五个的 train/test 存在约 80% 的字节级全同流，Tor 为 0%。审计脚本与去重评测一并开源。

test 产品准确率 0.8787，门控 AUROC 0.9784，未知拒识 100%（18 bins）。stunnel 0/30，CPU 推理不支持。代码与权重 Apache-2.0，仓库不含抓包。
