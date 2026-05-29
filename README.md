# ARPM v4.0

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/FAISS-Vector_Search-4B8BBE?style=flat" alt="FAISS" />
  <img src="https://img.shields.io/badge/BM25%2B-Hybrid_Retrieval-5A5A5A?style=flat" alt="BM25+" />
  <img src="https://img.shields.io/badge/OpenAI-Compatible_API-412991?style=flat&logo=openai&logoColor=white" alt="OpenAI-compatible API" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/arXiv-2605.14802-B31B1B?style=flat&logo=arxiv&logoColor=white" alt="arXiv 2605.14802" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat" alt="MIT License" />
</p>

ARPM, short for **Analysis-Based Role-Playing with Memory**, is an open-source long-term memory and retrieval framework for role-playing dialogue, persona consistency research, and local knowledge-base interaction.

ARPM v4.0 focuses on **heterogeneous temporal memory governance**: it separates knowledge-base memory from dialogue-history memory, combines vector retrieval with BM25+ keyword ranking, applies temporal weighting, and injects recalled memory in chronological order for long multi-turn dialogue.

中文简介：ARPM 是一个面向长期角色一致性、记忆增强对话和可复现实验的开源系统。它支持本地 Web 对话、OpenAI 兼容 API、FAISS 向量检索、BM25+ 关键词检索、父子块召回、双时态权重和研究日志输出。

## Keywords

`LLM memory`, `persona consistency`, `role-playing dialogue`, `RAG`, `retrieval-augmented generation`, `BM25+`, `FAISS`, `temporal memory`, `long-term dialogue`, `Chinese NLP`, `OpenAI-compatible API`, `Flask`, `AI companion`, `knowledge base chatbot`

中文关键词：长期记忆、角色一致性、角色扮演对话、检索增强生成、外部记忆治理、时间衰减、父子块召回、知识库聊天、中文大模型应用。

## Paper

The corresponding preprint is available on arXiv:

- **A Heterogeneous Temporal Memory Governance Framework for Long-Term LLM Persona Consistency**
- arXiv: [2605.14802](https://arxiv.org/abs/2605.14802)

If you use ARPM in academic work, please cite the paper with the citation metadata in [CITATION.cff](CITATION.cff) or the BibTeX entry in the [Citation](#citation) section.

## What ARPM Does

- Maintains separate retrieval paths for global knowledge-base memory and per-session dialogue history.
- Combines FAISS vector search, BM25+ keyword ranking, and Reciprocal Rank Fusion.
- Applies temporal weighting to model recency, long-term anchors, and dialogue continuity.
- Injects recalled memory chronologically so later recalled content appears closer to the final instruction.
- Provides a lightweight Flask web interface for free dialogue, role-playing, API configuration, knowledge upload, and diagnostics.
- Keeps research logs, recall logs, dialogue logs, and implementation notes for reproducible inspection.

## Use Cases

- Long-term role-playing dialogue and AI companion prototypes.
- Persona consistency experiments across long multi-turn conversations.
- Memory-augmented RAG systems for Chinese and mixed Chinese-English knowledge bases.
- Course projects, thesis experiments, and reproducible LLM application research.
- Local knowledge-base chat with OpenAI-compatible model providers.

## Quick Start

### Windows

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
start.bat
```

### Linux or macOS

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
sh start.sh
```

Open the web interface:

```text
http://127.0.0.1:5000
```

## Docker

```bash
docker compose up --build
```

The compose file maps local runtime and model directories into the container:

```text
./runtime         -> /app/runtime
./assets/models   -> /app/assets/models
```

## Model Download

Vector retrieval uses the sentence embedding model:

```text
shibing624/text2vec-base-chinese
```

Model weights are not included in this repository. The default local path is:

```text
assets/models/shibing624/text2vec-base-chinese
```

Download with Git LFS:

```bash
git lfs install
mkdir -p assets/models/shibing624
git clone https://huggingface.co/shibing624/text2vec-base-chinese assets/models/shibing624/text2vec-base-chinese
```

Or download with Hugging Face CLI:

```bash
pip install -U huggingface_hub
huggingface-cli download shibing624/text2vec-base-chinese --local-dir assets/models/shibing624/text2vec-base-chinese
```

If Hugging Face is slow in your network, set a mirror endpoint before download:

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

Windows PowerShell:

```powershell
$env:HF_ENDPOINT = "https://hf-mirror.com"
```

You can also keep the model outside the repository and point ARPM to it:

```bash
export ARPM_MODEL_ROOT=/path/to/models
```

Windows PowerShell:

```powershell
$env:ARPM_MODEL_ROOT = "D:\models"
```

## Project Layout

```text
backend/app.py                       Flask entry point
backend/api                          HTTP API endpoints
backend/core/retriever.py            Vector, BM25+, and RRF retrieval flow
backend/core/generator.py            Prompt construction and response generation
backend/storage/vector_store.py      FAISS vector storage
backend/storage/memory_store.py      Dialogue memory storage
backend/utils/bm25_plus.py           BM25+ scorer
backend/web/templates/index.html     Frontend template
backend/web/static                   Frontend CSS and JavaScript
config                               Character and system configuration
docs                                 Research and implementation notes
scripts                              Utility scripts
tests                                Test files
```

## Documentation Map

- [Project Overview](docs/PROJECT_OVERVIEW.md): encyclopedia-style overview for readers, search engines, and wiki pages.
- [Wiki Home Draft](docs/WIKI_HOME.md): copy-ready GitHub Wiki homepage draft.
- [User Guide](docs/USER_GUIDE.md): local setup, configuration, dialogue flow, and troubleshooting.
- [Current Architecture](docs/CURRENT_ARCHITECTURE.md): current code path and implementation boundaries.
- [Formula and Numerical Notes](docs/ARPM公式与数值说明.md): retrieval, temporal weighting, and experiment-facing formulas.
- [Feature Summary](docs/FEATURES_SUMMARY.md): feature list and implementation summary.
- [Changelog](docs/CHANGELOG.md): release notes.
- [Contributing](CONTRIBUTING.md): issue, pull request, and research contribution notes.
- [Security](SECURITY.md): vulnerability reporting and sensitive-data guidance.

## Repository Discovery

Recommended GitHub topics:

```text
llm, rag, memory, persona-consistency, role-playing, chatbot, faiss,
bm25, temporal-memory, chinese-nlp, flask, openai-compatible
```

Suggested short description:

```text
Long-term memory RAG framework for role-playing dialogue and LLM persona consistency research.
```

Suggested website field:

```text
https://arxiv.org/abs/2605.14802
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

## Contributing

Issues, documentation improvements, reproducibility reports, and pull requests are welcome. Please see [CONTRIBUTING.md](CONTRIBUTING.md) before opening a larger change.

Do not commit API keys, private chat logs, local runtime databases, uploaded knowledge bases, or embedding model weights. Use [.env.example](.env.example) as a local configuration reference.

## License

ARPM is released under the [MIT License](LICENSE).
