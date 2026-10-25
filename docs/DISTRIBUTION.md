# Where this release is published

The channels below need no academic account, no institution, and no invitation. Each row states what is live and what is still blocked.

## Live

| Channel | URL | What it carries |
|---|---|---|
| GitHub Pages | https://lupingQAQ.github.io/quietspan/ | landing page, abstract, audit table, install commands, citation |
| GitHub repository | https://github.com/lupingQAQ/quietspan | code, docs, both papers, release tag v0.1.0 |
| GitHub Release | https://github.com/lupingQAQ/quietspan/releases/tag/v0.1.0 | source zip, weights zip, checksums |
| Hugging Face model | https://huggingface.co/luping123/quietspan | weights, model card, config with arm mapping |
| Hugging Face discussion | https://huggingface.co/luping123/quietspan/discussions/1 | release announcement |

## Ready, needs one account action

| Channel | What it needs | Why it is worth doing |
|---|---|---|
| PyPI | an API token (`twine upload`) | `pip install quietspan` is the shortest path from "interesting" to "running it" |
| Kaggle | a Kaggle account | datasets and notebooks are indexed by search and cited by practitioners |
| ModelScope | an account, Chinese phone number accepted | the Chinese mirror of the model card; large domestic ML audience |
| Papers with Code | GitHub login only | links the report to code and weights; this is where people look for implementations |
| Dev.to | email account | developer write-ups surface in search for months |
| V2EX | email account | Chinese developer forum, one thread per project, high signal |
| 掘金 | email account | Chinese developer blog, good for the audit story |
| CSDN | email account | high volume, weaker signal, useful for long-tail search |

## Deliberately not used

X, LinkedIn, Hacker News, Reddit, 知乎 and FreeBuf were excluded by request. The prepared copy in `social-posts.md` is left in place but unpublished.

## Submission order that costs the least effort

1. PyPI. One token, permanent install path, feeds every later post with a command people can run.
2. Papers with Code. GitHub login, links report to code, no writing involved.
3. ModelScope. Mirror of the English model card, reaches the Chinese audience that will not read GitHub.
4. Kaggle. A notebook that loads the weights and runs the CLI on a synthetic capture.
5. Dev.to and 掘金. One article each, the audit story rather than the model story.
6. V2EX. Short post, link to the landing page, expect hard questions and answer them.
