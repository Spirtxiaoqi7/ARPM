# ARPM Wiki Home

Welcome to the ARPM wiki.

ARPM, **Analysis-Based Role-Playing with Memory**, is an open-source long-term memory and retrieval framework for role-playing dialogue, persona consistency research, and local knowledge-base chat.

中文：ARPM 是一个面向长期角色一致性、角色扮演对话、外部记忆治理和可复现实验的开源系统。

## Start Here

- Repository: <https://github.com/Spirtxiaoqi7/ARPM>
- Paper: <https://arxiv.org/abs/2605.14802>
- User guide: [docs/USER_GUIDE.md](USER_GUIDE.md)
- Architecture: [docs/CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md)
- Formula notes: [docs/ARPM公式与数值说明.md](ARPM公式与数值说明.md)

## Main Features

- Long-term dialogue memory.
- Knowledge-base retrieval and dialogue-history retrieval.
- FAISS vector search.
- BM25+ keyword retrieval.
- Parent-child chunk recall.
- Temporal weighting and chronological prompt injection.
- OpenAI-compatible API configuration.
- Local Flask web interface.
- Research logs and diagnostic utilities.

## Installation

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

Open:

```text
http://127.0.0.1:5000
```

## Citation

```bibtex
@misc{zhao2026arpm,
  title         = {A Heterogeneous Temporal Memory Governance Framework for Long-Term LLM Persona Consistency},
  author        = {Zhao, Yang and Wang, Huan and Li, Yingshuo and Tu, Haomiao and Lin, Hujite},
  year          = {2026},
  eprint        = {2605.14802},
  archivePrefix = {arXiv},
  primaryClass  = {cs.AI},
  url           = {https://arxiv.org/abs/2605.14802}
}
```

## Suggested Wiki Pages

- Installation
- Model Download
- API Configuration
- Knowledge Base Management
- Memory and Retrieval Architecture
- Formula Notes
- Experiments and Reproducibility
- FAQ

