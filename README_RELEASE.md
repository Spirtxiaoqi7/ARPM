# ARPM-v4 Release Package

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black" />
  <img src="https://img.shields.io/badge/FAISS-Vector_Search-4B8BBE?style=flat" />
  <img src="https://img.shields.io/badge/BM25%2B-Hybrid_Retrieval-5A5A5A?style=flat" />
  <img src="https://img.shields.io/badge/HuggingFace-Models-FFD21E?style=flat&logo=huggingface&logoColor=black" />
  <img src="https://img.shields.io/badge/OpenAI-Compatible_API-412991?style=flat&logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/arXiv-coming_soon-B31B1B?style=flat&logo=arxiv&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat" />
</p>

This package is arranged for a GitHub-style release. It contains source code,
configuration, tests, documentation, frontend static assets, dependency pins,
and Docker files.

It intentionally does not include virtual environments, runtime databases,
logs, uploaded files, experiment outputs, or model weights.

ARPM v4.0 is intended for both academic research and free dialogue use. For
research, it supports memory-augmented role-playing experiments, retrieval
ablation, temporal weighting analysis, prompt-injection inspection, and
figure/log reproduction. For daily use, it supports configurable AI personas,
knowledge-base assisted conversation, and an immersive chat interface.

Main implementation languages and technologies:

- Python and Flask for the backend
- HTML, CSS, and vanilla JavaScript for the frontend
- FAISS for vector indexing
- `shibing624/text2vec-base-chinese` for sentence embeddings
- BM25+ and `jieba` for keyword retrieval
- Docker Compose for containerized deployment

arXiv: coming soon. The preprint link can be added to `README.md` after release.

## Local Run

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
start.bat
```

On Linux or macOS:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
sh start.sh
```

The service listens on port `5000` by default.

## Docker Run

```bash
docker compose up --build
```

Runtime data is stored in `./runtime`. Model files should be placed under
`./assets/models`, or the `ARPM_MODEL_ROOT` environment variable should point to
an external model directory.

## Model And Retrieval Assets

向量检索使用句向量模型 `shibing624/text2vec-base-chinese`。模型权重不包含在发布包内，需要用户自行下载。

默认本地路径：

```text
assets/models/shibing624/text2vec-base-chinese
```

方式一：使用 Git LFS 下载：

```bash
git lfs install
mkdir -p assets/models/shibing624
git clone https://huggingface.co/shibing624/text2vec-base-chinese assets/models/shibing624/text2vec-base-chinese
```

方式二：使用 Hugging Face CLI 下载：

```bash
pip install -U huggingface_hub
huggingface-cli download shibing624/text2vec-base-chinese --local-dir assets/models/shibing624/text2vec-base-chinese
```

如果 Hugging Face 访问较慢，可以先设置镜像端点：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

Windows PowerShell：

```powershell
$env:HF_ENDPOINT = "https://hf-mirror.com"
```

BM25+ 不需要单独下载模型。它是关键词排序算法，实现在 `backend/utils/bm25_plus.py`，使用 `jieba` 做中文分词，并在知识库导入后基于知识库块运行时构建索引。知识库混合检索会通过 RRF 融合向量检索和 BM25+ 排名结果。

## Important Paths

- Backend entry: `backend/app.py`
- Frontend template: `backend/web/templates/index.html`
- Frontend assets: `backend/web/static`
- Runtime data: `runtime/arpm-app`
- Model root: `assets/models`

## Environment Variables

Copy `.env.example` to `.env` when using Docker Compose and adjust values as
needed.
