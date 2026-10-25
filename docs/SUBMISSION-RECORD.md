# 投稿记录 — 《计算机工程》

## 结果

**2026-10-26 投稿成功**，稿件进入作者中心「最新投稿」。

| 项 | 值 |
|---|---|
| 期刊 | 计算机工程 / Computer Engineering（ISSN 1000-3428，CN 31-1289/TP） |
| 投稿系统 | JournalX（ecice06.com） |
| 投稿时间 | 2026-10-26 |
| 文题 | IntraSpanNet：不主动扫描识别内网安全设备、终端安全产品与常用软件 |
| 英文文题 | IntraSpanNet: Identifying Security Appliances, Endpoint Agents, and Common Software from Five-Packet Intranet Flows without Active Scanning |
| 作者 | 李晨赫（独立研究者） |
| 栏目 | 网络空间安全 |
| 基金 | 无 |
| 稿件文件 | IntraSpanNet-zh-doc.zip（169.72 KB，内含 IntraSpanNet-zh.docx） |
| 系统内部 ID | 68165941608 |
| 稿号 | 编辑部受理后分配（「最新投稿」阶段尚未显示） |

查看入口：作者中心 → 最新投稿
`https://www.ecice06.com/JournalX_ecice/author/Author!submited.action`

## 稿件内容

- 中文全文 6 页，表格 I–XIII，图 2 张
- 参考文献 32 条，全部在正文引用
- 摘要 381 字（中）/ 811 字符（英）
- 关键词 8 个：被动资产发现；内网流量分析；流量探针；字节级分类；无分词器学习；Gated DeltaNet；开集识别；加密流量分析

## 推荐审稿人

| 姓名 | 单位 | 邮箱 |
|---|---|---|
| Gayan Kulatilleke | The University of Queensland | g.kulatilleke@uq.edu.au |
| Marius Portmann | The University of Queensland | marius@itee.uq.edu.au |

邮箱取自 MambaNetBurst 论文公开主页，电话填昆士兰大学总机 61333651111。

**注意**：详细信息页显示审稿人列表出现重复（每人两次），是分两次会话分别添加造成的。不影响投稿状态，若编辑部来信询问再说明。

## 编辑部留言

> 本文为独立研究，代码、权重与评测脚本已公开（https://github.com/lupingQAQ/IntraSpanNet，DOI: 10.5281/zenodo.23643146），仓库内不含任何抓包。

## 提交过程中的技术说明

JournalX 稿件上传的白名单是 `rar|doc|zip`，`.docx` 不在其中，直接上传会被静默拒收、页面回退。最终以 ZIP 形式提交，成功。

上传落库的判定是页面下部「已经上传的文件列表」出现条目，而非 URL 变化。

## 后续动作

1. 等编辑部回信（初审 + 栏目编辑分派稿号）
2. 收到稿号后补记到本文件
3. 若 30 天内无回音，用 `docs/SUBMISSION_EMAIL.md` 的内容再去信询问

## 投稿后的修订（2026-10-26）

投稿完成后，训练接口（`load_backbone`）、两个可运行示例和中英训练文档随 0.1.1 发布，论文第四节原句「训练代码不在发布包内」已不成立，做了两处修改：

| 文件 | 修改 | 时间 |
|---|---|---|
| `paper/IntraSpanNet.md` | 第四节该句改写为：第二、第三阶段以文档化接口发布，第一阶段不发布 | 2026-10-26 |
| `paper/IntraSpanNet-zh.md` | 同上，中文对应 | 2026-10-26 |
| `paper/IntraSpanNet.pdf` | 重新排版，仍 6 页 | 2026-10-26 |
| `paper/IntraSpanNet-zh.pdf` | 重新排版，仍 6 页 | 2026-10-26 |
| `paper/IntraSpanNet-zh.docx` | 重新生成 | 2026-10-26 |

**Zenodo 预印本**（10.5281/zenodo.23643146）已用同一 DOI 原地更新：作者由 QAQ, Luping 更正为 Li, Chenhe，三个文件全部替换。没有新建版本，因此 DOI 与论文引用保持一致。

**注意**：期刊系统里那份 `IntraSpanNet-zh-doc.zip`（169.72 KB）是投稿时的版本，文本仍是旧表述。仓库里的 `.doc` 与 `.zip` 保留为该次投稿的快照，未覆盖；`.docx` 是新版。若编辑部来信要求说明，可解释为投稿后代码发布范围扩大，不涉及实验数据与结论。

