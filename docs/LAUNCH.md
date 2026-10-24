# Launch plan

For the dated schedule, see [LAUNCH_7DAY.md](LAUNCH_7DAY.md).

## Positioning

One sentence: GDNet identifies 18 security products and services from the first five packets of a flow, rejects unknown products, and ships with an audit of the public benchmark splits used for comparison.

Do not call it state of the art. Do not call it a replacement for an IDS. The strongest public angle is the split audit and the reproducible, small model. The strongest technical angle is the open-set path and the deployment constraints.

## Assets

| Asset | Path | Status |
|---|---|---|
| Code repository | `gdnet/` | Ready |
| Weights | `weights/gdnet/` | Ready, 94.6 MB |
| Model card | `gdnet/docs/MODEL_CARD.md` | Ready |
| Results | `gdnet/docs/RESULTS.md` | Ready |
| Benchmark audit | `gdnet/docs/BENCHMARK_AUDIT.md` | Ready |
| Release notes | `gdnet/docs/RELEASE_NOTES_v0.1.0.md` | Ready |
| Blog, English | `gdnet/docs/blog-en.md` | Ready |
| Blog, Chinese | `gdnet/docs/blog-zh.md` | Ready |
| Social copy | `gdnet/docs/social-posts.md` | Ready |
| Space | `gdnet/space/` | Code ready; needs GPU hardware |
| Demo capture | `gdnet/examples/sample.pcap` | Synthetic, 2.3 KB |

## Before launch

1. Account names are already set to GitHub `lupingQAQ` and Hugging Face `luping123`. If you publish under another account, run:

```bash
python scripts/set_accounts.py --github your-github --hf your-hf
```

2. Create the GitHub repository `gdnet`. Do not initialize it with a README.
3. Create the Hugging Face model repository `gdnet`.
4. Create the Space `gdnet-demo` and select a GPU hardware tier. The free CPU tier cannot run the model.
5. Verify the weights checksums:

```bash
cd weights/gdnet
sha256sum -c SHA256SUMS
```

6. Run the local test suite:

```bash
cd gdnet
pytest -q
```

7. Run the synthetic capture through the CLI on a CUDA machine. Confirm that the pipeline returns three rows and does not crash. The labels are expected to be unknown.

## Publish the code

```bash
cd gdnet
git init -b main
git add -A
git status --short
git commit -m "release: GDNet v0.1.0"
git remote add origin git@github.com:lupingQAQ/gdnet.git
git push -u origin main
git tag -a v0.1.0 -m "GDNet v0.1.0"
git push origin v0.1.0
```

Check the staged file list before committing. The repository must not contain weights, captures, logs, or the `weights/` directory.

## Publish the model

```bash
huggingface-cli login
huggingface-cli upload luping123/gdnet weights/gdnet . --repo-type model
```

Upload the model card as `README.md` in the model repository. The card is `gdnet/docs/MODEL_CARD.md`; rename it on upload or keep both and link them.

## Publish the Space

```bash
python scripts/build_space.py --weights weights/gdnet
huggingface-cli upload luping123/gdnet-demo space . --repo-type space
```

The Space needs a GPU. If the account does not have GPU credits, do not publish a CPU Space that always errors. Publish the model card and code first, and add the Space when hardware is available.

## Launch sequence

Day 0:

- GitHub release v0.1.0 with the weights zip and `SHA256SUMS`.
- Hugging Face model repository with the model card.
- Short post on X and LinkedIn.
- Post the English blog.

Day 1:

- Show HN.
- r/netsec and r/MachineLearning.
- Zhihu and V2X.
- FreeBuf or 安全客 submission.

Day 2:

- Follow-up post with the split audit table.
- Reply to issues and comments within 48 hours.
- Add a FAQ entry for each recurring criticism.

## Copy

Use the drafts in `social-posts.md`. Keep the first sentence factual. Put the limitation in the same post, not in a footnote.

## Likely criticism

| Criticism | Response |
|---|---|
| "The benchmark splits are leaked." | We disclose it. Five of six splits have about 80% overlap; Tor is 0%. All comparisons are same-protocol. The deduplicated results are in the report. |
| "The test set is small." | Yes, 503 flows, flow-level split, one held-out session per class. We do not claim session-level generalization. |
| "stunnel fails." | Yes, 0/30. It needs enrollment or new data. This is in the README and the model card. |
| "No CPU support." | Correct. The GDN backbone uses Triton kernels. GPU-only is a deliberate scope decision for v0.1.0. |
| "This is not SOTA." | We do not claim SOTA. The release is a small, reproducible model with an open-set path and a split audit. |
| "Weights are not reproducible without the data." | The checkpoints, prototypes, threshold, and evaluation script are released. The lab capture split is not redistributed. |

## Metrics

Track GitHub stars, Hugging Face downloads, issue quality, and citations. Do not optimize for stars at the cost of accuracy in the claims. A single reproducible issue report is worth more than a large but vague launch.

## Do not

- Do not astroturf or ask people to post without disclosure.
- Do not claim a benchmark record.
- Do not hide the leakage audit or the stunnel failure.
- Do not upload captures or customer data.
- Do not publish a CPU Space that cannot run the model.
