# Security policy

## Intended use

GDNet is a network traffic classifier for authorized asset discovery and security review. Use it only on networks you own or have written permission to monitor. The model reports probabilities and distances, not facts. High-impact decisions require human review.

## Prohibited use

- Monitoring networks without authorization.
- Identifying users, content, or application payloads.
- Building profiles of individuals.
- Automated blocking or enforcement without review.
- Uploading customer or production captures to public demos.

## Data handling

The repository and released weights contain no captures. If you run the model on your own traffic, the capture remains on your infrastructure. Do not send captures to third-party services without a data processing agreement.

The public demo, if deployed, processes uploaded files in memory and does not retain them. Do not upload sensitive traffic to the demo even so.

## Reporting a vulnerability

Report security issues in the code or model to the maintainers by opening a private security advisory on GitHub. Include:

- A description of the issue.
- Reproduction steps or a minimal example.
- Affected version or commit.
- Any suggested fix.

Do not open a public issue for an unpatched vulnerability. The maintainers will acknowledge within five working days.

## Model limitations as security issues

The following are known limitations, not vulnerabilities:

- `stunnel` has zero recall in the acceptance set.
- Unknown products close to a known prototype may be accepted.
- CPU inference is not supported.
- The model was trained on lab traffic and may not transfer to production networks.

## Supply chain

- Pin dependencies in production.
- Verify `SHA256SUMS` before loading weights.
- `torch.load` is used with `weights_only=False` because the checkpoints contain class metadata. Load only weights from a trusted source.

## License

Apache-2.0. See `LICENSE`.
