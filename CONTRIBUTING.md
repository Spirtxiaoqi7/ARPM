# Contributing to ARPM

Thank you for your interest in ARPM. Contributions are welcome in code, documentation, experiments, reproducibility reports, issue triage, and examples.

## Good First Contributions

- Improve setup notes for Windows, Linux, macOS, or Docker.
- Add reproducible examples for different OpenAI-compatible providers.
- Clarify documentation around retrieval, memory weighting, and knowledge-base upload.
- Report bugs with logs, screenshots, environment details, and reproduction steps.
- Add tests for retrieval, configuration, memory storage, or API behavior.

## Development Setup

```bash
python -m venv .venv
pip install -r requirements.txt
```

Windows:

```powershell
start.bat
```

Linux or macOS:

```bash
sh start.sh
```

## Before Opening a Pull Request

- Keep changes focused and easy to review.
- Update documentation when behavior changes.
- Avoid committing local runtime data, API keys, model weights, private logs, or generated caches.
- Run the relevant tests when possible:

```bash
pytest
```

## Issue Reports

Please include:

- Operating system and Python version.
- Installation method.
- Model path and whether the embedding model was downloaded successfully.
- API provider, base URL format, and model name, with secrets removed.
- Steps to reproduce.
- Expected behavior and actual behavior.
- Relevant logs or screenshots.

## Research Contributions

For experiment reports, please include:

- Dataset or scenario description.
- Model provider and model name.
- Retrieval settings.
- Temporal weighting settings.
- Evaluation criteria.
- Whether runtime logs can be shared.

