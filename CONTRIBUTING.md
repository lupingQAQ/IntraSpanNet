# Contributing

## Scope

Contributions are welcome for:

- Preprocessing for additional capture formats.
- Inference performance and memory improvements.
- Evaluation scripts and reproducibility fixes.
- Documentation corrections.
- New product labels, with data and a reproducible protocol.

The project does not accept:

- Customer captures or production traffic.
- Claims of state-of-the-art results without a reproducible protocol.
- Changes that hide known limitations.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

A CUDA GPU is required for model forward tests. Tests that need `fla` are skipped when the dependency is missing.

## Code style

- Python 3.10+.
- Line length 110.
- Type hints for public functions.
- No hard-coded absolute paths.
- No network access in tests.

## Pull requests

1. Open an issue for non-trivial changes.
2. Keep the change focused.
3. Add or update tests.
4. Run `pytest -q`.
5. Describe the change and its limitations in the PR.

## Data policy

Do not include captures, labels derived from customer traffic, or model weights in pull requests. Use synthetic or public data.

## License

By contributing, you agree that your contribution is licensed under Apache-2.0.
