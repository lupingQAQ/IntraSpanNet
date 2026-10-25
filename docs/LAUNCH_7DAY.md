# Seven-day release schedule

Status at the start: GitHub repository, release v0.1.0, Hugging Face model, and the technical report on GitHub are live. Zenodo and the preprint server require account actions.

## Day 0 (done)

- GitHub repository: https://github.com/lupingQAQ/quietspan
- Release v0.1.0 with source and weight assets.
- Hugging Face model: https://huggingface.co/luping123/quietspan
- Technical report: `paper/quietspan.pdf` in the repository.
- Model card, results, benchmark audit, and launch copy are in the repository.

## Day 1: DOI and preprint

1. Create the Zenodo deposit with the package in `zenodo/`. Publish it and copy the version DOI.
2. Submit the PDF to TechRxiv. If TechRxiv is slow, use Preprints.org. Do not submit to both with different DOIs.
3. Add the DOI to `README.md`, `README.zh-CN.md`, `CITATION.cff`, and the Hugging Face model card.
4. Push the DOI update and re-upload the model card.

Do not write "accepted" or "published". A preprint is not peer reviewed.

## Day 2: Hugging Face and X

1. Post a Hugging Face Community article or a model discussion with the release summary and the paper link.
2. Publish the X thread from `docs/social-posts.md`. Attach the benchmark overlap figure.
3. Publish the LinkedIn post.
4. Pin the release post on the GitHub repository if the account supports it.

## Day 3: Hacker News and Reddit

1. Submit Show HN with the title and body from `docs/social-posts.md`.
2. Post to r/netsec and r/MachineLearning. Read the self-promotion rules first; participate in comments instead of dropping the link.
3. Answer technical questions with numbers from `docs/RESULTS.md`, not with marketing language.

## Day 4: Chinese channels

1. Publish the Zhihu long-form article. Use the Chinese blog draft, not a machine translation.
2. Publish the WeChat article.
3. Submit to FreeBuf or 安全客. Use the security-focused copy.
4. Post a short note on V2X.

## Day 5: Model platforms and video

1. Create a ModelScope model page with the model card and the weight links.
2. Record a three-minute demo: synthetic capture, CLI run, JSON output, and one paragraph on limitations.
3. Submit the demo to Bilibili and 即刻.
4. Send the release to Import AI, TLDR AI, and The Batch through their submission forms. Do not send repeated follow-ups.

## Day 6: Follow-up

1. Publish a short post with the benchmark overlap chart and the deduplicated results.
2. Reply to GitHub issues and Hugging Face discussions within 48 hours.
3. Add an FAQ entry for each recurring question: stunnel, CPU, test size, split audit, license.

## Day 7: Review

1. Record stars, model downloads, paper downloads, DOI visits, and issue quality.
2. Write a changelog entry for v1.0.1 if documentation changes are needed.
3. Decide whether to add a GPU Space, a training-code release, or a second data collection round.

## Claim discipline

- No state-of-the-art claim.
- No claim of session-level generalization.
- No claim that the malicious head replaces an IDS.
- No claim that the benchmark numbers are clean. The audit is part of the release.
- If a venue asks about AI assistance, follow its disclosure policy. Do not claim human-only authorship if that is not true.
- Cite the version DOI, not the concept DOI, when referring to v0.1.0.
