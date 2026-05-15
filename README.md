# ARPM v4.0

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black" />
  <img src="https://img.shields.io/badge/HTML5-E34F26?style=flat&logo=html5&logoColor=white" />
  <img src="https://img.shields.io/badge/CSS3-1572B6?style=flat&logo=css3&logoColor=white" />
  <img src="https://img.shields.io/badge/FAISS-Vector_Search-4B8BBE?style=flat" />
  <img src="https://img.shields.io/badge/BM25%2B-Hybrid_Retrieval-5A5A5A?style=flat" />
  <img src="https://img.shields.io/badge/HuggingFace-Models-FFD21E?style=flat&logo=huggingface&logoColor=black" />
  <img src="https://img.shields.io/badge/OpenAI-Compatible_API-412991?style=flat&logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/arXiv-coming_soon-B31B1B?style=flat&logo=arxiv&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat" />
</p>

ARPM v4.0, short for **Analysis-Based Role-Playing with Memory**, is an open-source role-playing dialogue system with long-term memory, hybrid retrieval, temporal weighting, and a lightweight web interface.

本项目面向两类场景：一类是可复现实验和学术研究，另一类是自由对话、角色扮演和个人知识库交互。系统默认提供前后端一体化运行方式，也支持 Docker 部署，便于在本地实验、课程项目、论文复现和开源社区协作中使用。

> arXiv: (https://arxiv.org/abs/2605.14802)

## Highlights

- **Hybrid memory retrieval**: knowledge-base retrieval and dialogue-history retrieval are stored and retrieved separately.
- **Vector + BM25+ fusion**: knowledge retrieval combines semantic vector search with BM25+ keyword ranking through RRF.
- **Dual temporal weighting**: both dialogue round order and physical time are retained for memory scoring and prompt injection.
- **Chronological prompt injection**: recalled blocks are injected from earlier turns to later turns, so the latest recalled content appears closest to the final instruction.
- **Role-aware retrieval**: user name, AI name, and source-role cues can be used to enhance retrieval queries.
- **Research-friendly logging**: recall logs, dialogue logs, and chain-of-thought-related diagnostic logs are separated under the admin logging structure.
- **Free dialogue support**: the frontend supports immersive chat and clean research display modes, with Chinese/English interface switching.

## Technology Stack

- **Backend**: Python, Flask
- **Frontend**: HTML, CSS, vanilla JavaScript
- **Vector index**: FAISS
- **Embedding model**: `shibing624/text2vec-base-chinese`
- **Keyword retrieval**: BM25+ with `jieba` Chinese tokenization
- **LLM API**: OpenAI-compatible chat completion API, including DeepSeek/OpenAI-style endpoints
- **Deployment**: local Python virtual environment or Docker Compose

## Academic Use

ARPM v4.0 is designed to support controlled experiments around memory-augmented dialogue systems. It can be used to study:

- role consistency in long multi-turn dialogue;
- retrieval-augmented generation for character simulation;
- temporal decay in dialogue memory;
- vector retrieval versus BM25+ keyword retrieval;
- prompt construction under chronological memory injection;
- ablation studies for retrieval, temporal weighting, BM25+, and role-aware query enhancement.

The project includes research notes and formula descriptions under `docs/`. Runtime logs can be used for experimental inspection, error analysis, and figure reproduction.

## Free Dialogue Use

Besides research use, ARPM v4.0 can also be used as a local role-playing chat system. You can configure:

- user name and user persona;
- AI name and system prompt;
- API key, base URL, and model name;
- retrieval parameters and ablation switches;
- knowledge-base files for character background, world settings, or personal notes.

The frontend provides two visual styles:

- immersive chat mode for daily conversation and role-playing;
- clean research mode for observation, debugging, and experiment demonstration.

## Quick Start

Windows:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
start.bat
```

Linux or macOS:

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

The compose file maps:

```text
./runtime        -> /app/runtime
./assets/models  -> /app/assets/models
```

## Model Download

Vector retrieval uses the sentence embedding model:

```text
shibing624/text2vec-base-chinese
```

Model weights are not included in this repository. The expected local path is:

```text
assets/models/shibing624/text2vec-base-chinese
```

Download with Git LFS:

```bash
git lfs install
mkdir -p assets/models/shibing624
git clone https://huggingface.co/shibing624/text2vec-base-chinese assets/models/shibing624/text2vec-base-chinese
```

Download with Hugging Face CLI:

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

You can also keep the model outside the repository and point the app to it:

```bash
export ARPM_MODEL_ROOT=/path/to/models
```

Windows PowerShell:

```powershell
$env:ARPM_MODEL_ROOT = "D:\models"
```

## BM25+

BM25+ is not a downloadable model. It is a keyword-ranking algorithm implemented in:

```text
backend/utils/bm25_plus.py
```

The implementation uses `jieba` for Chinese tokenization and builds the BM25+ index from imported knowledge-base parent chunks at runtime. In the knowledge retrieval path, vector search and BM25+ keyword ranking are fused through RRF.

Related dependencies are pinned in `requirements.txt`:

```text
jieba==0.42.1
rank-bm25==0.2.2
```

The current retrieval path uses the in-project `BM25PlusScorer`; `rank-bm25` is retained as an environment dependency for reproducibility and future replacement experiments.

## Project Layout

```text
backend/app.py                       Flask entry
backend/config.py                    Path and runtime configuration
backend/api                          HTTP API endpoints
backend/core/retriever.py            Vector, BM25+, and RRF retrieval flow
backend/core/generator.py            Prompt construction and response generation
backend/storage/vector_store.py      FAISS vector storage
backend/storage/memory_store.py      Dialogue memory storage
backend/utils/bm25_plus.py           BM25+ scorer
backend/utils/admin_logger.py        Research and diagnostic logs
backend/web/templates/index.html     Frontend template
backend/web/static                   Frontend CSS and JavaScript
config                               Character and system configuration
docs                                 Research and implementation notes
scripts                              Utility scripts
tests                                Test files
```

## Runtime Paths

Default runtime data directory:

```text
runtime/arpm-app
```

Default model root:

```text
assets/models
```

Both paths can be changed with environment variables:

```text
ARPM_RUNTIME_DIR
ARPM_MODEL_ROOT
```

## API Configuration

The frontend settings panel supports OpenAI-compatible API configuration:

```text
API key
Base URL
Model name
Temperature
Max tokens
```

The default configuration is compatible with DeepSeek-style endpoints, and can be changed from the web interface.

## Research Notes

For formula descriptions, parameter values, temporal decay settings, and experiment-facing explanations, see:

```text
docs/
```

The project keeps runtime data out of the release package. When publishing or sharing experimental results, keep raw logs, figures, and private datasets separate from the source repository unless they are explicitly intended for release.

## License

This project is released under the license included in `LICENSE`.

## Citation

The paper citation will be added after the arXiv preprint is available.

```markdown
## Citation

如果你在研究中使用 ARPM v4.0，请引用以下 arXiv 预印本：

```bibtex
@misc{zhao2026arpm,
  title        = {A Heterogeneous Temporal Memory Governance Framework for Long-Term LLM Persona Consistency},
  author       = {Zhao, Yang and Wang, Huan and Li, Yingshuo and Tu, Haomiao and Lin, Hujite},
  year         = {2026},
  eprint       = {2605.14802},
  archivePrefix = {arXiv},
  primaryClass = {cs.AI},
  url          = {https://arxiv.org/abs/2605.14802}
}
