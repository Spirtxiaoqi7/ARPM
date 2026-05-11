# ARPM v4.0

ARPM v4.0 是一个基于 Flask 后端和静态前端的角色扮演记忆系统，支持知识库召回、对话历史召回、双时间权重、角色感知查询增强，以及按时间顺序注入 prompt 的召回内容。

本发布包用于 GitHub 开源发布，不包含虚拟环境、运行数据库、日志、上传文件、实验输出和模型权重。

## 快速启动

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

访问：

```text
http://127.0.0.1:5000
```

## Docker 启动

```bash
docker compose up --build
```

`docker-compose.yml` 会映射：

```text
./runtime       -> /app/runtime
./assets/models -> /app/assets/models
```

## 向量模型下载

向量检索使用句向量模型：

```text
shibing624/text2vec-base-chinese
```

默认本地路径为：

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

Windows PowerShell:

```powershell
$env:HF_ENDPOINT = "https://hf-mirror.com"
```

也可以把模型放在仓库外部，然后通过环境变量指定模型根目录：

```bash
export ARPM_MODEL_ROOT=/path/to/models
```

Windows PowerShell:

```powershell
$env:ARPM_MODEL_ROOT = "D:\models"
```

## BM25+

BM25+ 不是需要下载的模型权重，而是关键词排序算法。本项目中的实现位置是：

```text
backend/utils/bm25_plus.py
```

该实现使用 `jieba` 做中文分词，在导入知识库后基于父块内容运行时构建 BM25+ 索引。知识库检索时，系统会将向量检索结果和 BM25+ 关键词排序结果通过 RRF 融合。

相关依赖已写入 `requirements.txt`：

```text
jieba==0.42.1
rank-bm25==0.2.2
```

说明：当前核心 BM25+ 逻辑使用 `backend/utils/bm25_plus.py` 中的 `BM25PlusScorer` 自研实现，`rank-bm25` 作为环境依赖保留，便于复现实验或后续替换。

## 项目结构

```text
backend/app.py                       Flask entry
backend/config.py                    Path and runtime configuration
backend/core/retriever.py            Vector, BM25+, RRF retrieval flow
backend/storage/vector_store.py      FAISS vector storage
backend/utils/bm25_plus.py           BM25+ scorer
backend/web/templates/index.html     Frontend template
backend/web/static                   Frontend CSS and JavaScript
config                               Character and system configuration
docs                                 Research and implementation notes
scripts                              Utility scripts
tests                                Test files
```

## 运行路径

默认运行数据目录：

```text
runtime/arpm-app
```

默认模型根目录：

```text
assets/models
```

二者都可以通过环境变量修改：

```text
ARPM_RUNTIME_DIR
ARPM_MODEL_ROOT
```
