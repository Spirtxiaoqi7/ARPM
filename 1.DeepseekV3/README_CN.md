# ARPM: 增强检索角色建模系统

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English README](README.md) | [安装指南](INSTALLATION_GUIDE.txt)

## 📖 项目简介

ARPM（Augmented Retrieval-based Persona Modeling，增强检索角色建模）是一个基于RAG（检索增强生成）的**角色一致对话系统**。它能够提供沉浸式的角色扮演对话体验，具备持久记忆和性格一致性。

### ✨ 核心特性

- 🎭 **角色扮演**：通过 `config.json` 配置角色名称和背景设定
- 🧠 **长期记忆**：混合检索（FAISS向量检索 + BM25关键词匹配）配合时间衰减机制
- 🔍 **智能检索**：结合语义相似度和关键词匹配
- ⏰ **时间衰减**：越近期的记忆权重越高，符合人类记忆规律
- 📝 **中文智能分块**：基于句子的智能文本分割工具（`chunker.py`）
- 🔌 **DeepSeek API**：由DeepSeek大语言模型驱动
- 💻 **多界面支持**：命令行（`chat_loop.py`）和图形界面（`chat_gui.py`）
- 🌐 **OpenAI兼容**：提供标准OpenAI API接口 `/v1/chat/completions`

## 🏗️ 系统架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     用户客户端   │◄───►│   DeepSeek API  │◄───►│    RAG服务      │
│ (chat_loop.py)  │     │    (端口8004)   │     │   (端口8003)    │
│ (chat_gui.py)   │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                         │
                               ▼                         ▼
                        ┌─────────────┐          ┌─────────────┐
                        │ DeepSeek LLM│          │   向量数据库  │
                        │   (API)     │          │(FAISS+BM25) │
                        └─────────────┘          └─────────────┘
```

## 📁 项目结构

```
ARPM/
├── api/                          # API服务
│   ├── deepseek_api.py          # DeepSeek服务（端口8004）
│   ├── rag_api.py               # RAG服务（端口8003）
│   └── __init__.py
├── models/                       # 嵌入模型（自动下载）
│   └── shibing624/
│       └── text2vec-base-chinese/
├── data/                         # 数据存储
├── vectors/                      # 向量索引存储（自动生成）
├── logs/                         # 对话日志（自动生成）
├── venv/                         # 虚拟环境（用户创建）
├── .env                          # API密钥配置
├── config.json                   # 角色配置
├── requirements.txt              # Python依赖
├── chunker.py                   # 文本分块工具
├── chat_loop.py                 # 命令行客户端
├── chat_gui.py                  # 图形界面客户端
├── RUN.bat                      # Windows启动脚本
├── extract_chat.py              # 对话提取工具
├── README.md                    # 英文文档
├── README_CN.md                 # 中文文档（本文件）
├── INSTALLATION_GUIDE.txt       # 详细安装指南
├── LICENSE                      # MIT协议
└── CONTRIBUTING.md              # 贡献指南
```

## 🚀 快速开始

### 环境要求

- Python 3.10 或更高版本
- DeepSeek API密钥 ([点击获取](https://platform.deepseek.com/))

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/Spirtxiaoqi7/ARPM.git
cd ARPM

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置API密钥
cp .env.example .env
# 编辑 .env 文件，添加你的DeepSeek API密钥：DEEPSEEK_API_KEY=your_key_here

# 6. 下载嵌入模型（首次运行自动下载，或手动下载）
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('shibing624/text2vec-base-chinese', cache_folder='models/shibing624/text2vec-base-chinese')"
```

### 运行系统

#### 方式1：一键启动（Windows）
```bash
# 双击或命令行运行：
RUN.bat
```

#### 方式2：手动启动
```bash
# 终端1：启动RAG服务
cd api && uvicorn rag_api:app --host 0.0.0.0 --port 8003

# 终端2：启动DeepSeek服务
cd api && uvicorn deepseek_api:app --host 0.0.0.0 --port 8004

# 终端3：启动命令行客户端
python chat_loop.py
```

#### 方式3：图形界面客户端
```bash
python chat_gui.py
```

## ⚙️ 配置说明

### 角色配置（`config.json`）

```json
{
    "character_name": "罗辑",
    "character_background": "你是罗辑，我是程心。你是《三体》中的面壁者..."
}
```

### 环境变量（`.env`）

```bash
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

⚠️ **切勿将.env文件提交到GitHub！** 包含敏感API密钥。

## 📚 使用说明

### 向RAG记忆库添加文档

```bash
# 基础用法 - 将文本文件添加到RAG
python chunker.py your_file.txt --add

# 高级选项
python chunker.py your_file.txt \
    --add \
    --target-size 250 \
    --overlap 1 \
    --batch-size 500 \
    --timestamp 0
```

### 进行对话

服务启动后：

1. **命令行模式**：输入消息并按回车
2. **图形界面模式**：使用GUI界面进行交互
3. **输入 `exit`** 或关闭窗口退出

### API接口

#### RAG服务（http://127.0.0.1:8003）

| 接口 | 方法 | 说明 |
|------|------|------|
| `/add_document` | POST | 添加文档到RAG |
| `/search` | POST | 向量相似度检索 |
| `/search_hybrid` | POST | 混合检索（向量+BM25+时间衰减） |
| `/health` | GET | 健康检查 |
| `/stats` | GET | 统计信息 |

#### DeepSeek服务（http://127.0.0.1:8004）

| 接口 | 方法 | 说明 |
|------|------|------|
| `/generate` | POST | 生成角色回复 |
| `/v1/chat/completions` | POST | OpenAI兼容API |
| `/health` | GET | 健康检查 |
| `/config` | GET | 当前角色配置 |

## 🔧 高级配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RAG_PORT` | 8003 | RAG服务端口 |
| `DEEPSEEK_PORT` | 8004 | DeepSeek服务端口 |
| `RAG_HOST` | 127.0.0.1 | RAG服务主机 |
| `DEEPSEEK_HOST` | 127.0.0.1 | DeepSeek服务主机 |

### 分块工具参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--target-size` | 250 | 目标块大小（字符数） |
| `--overlap` | 1 | 重叠句子数 |
| `--min-size` | 50 | 最小块大小 |
| `--batch-size` | 500 | 批量添加大小 |
| `--timestamp` | 0 | 时间戳（用于时间权重） |

## 🛠️ 故障排查

### 常见问题

**问题**：`ModuleNotFoundError`
- **解决**：确保虚拟环境已激活：`venv\Scripts\activate`

**问题**：`DeepSeek API key not found`
- **解决**：检查`.env`文件是否存在且包含有效的`DEEPSEEK_API_KEY`

**问题**：`Model not found`
- **解决**：模型会在首次运行时自动下载，或手动从[HuggingFace](https://huggingface.co/shibing624/text2vec-base-chinese)下载

**问题**：`Port already in use`
- **解决**：终止占用端口的进程或通过环境变量修改端口

## 📄 开源协议

本项目采用 MIT 协议开源 - 详见 [LICENSE](LICENSE) 文件。

Copyright (c) 2026 Spirtxiaoqi7

## 🙏 致谢

- [DeepSeek](https://deepseek.com/) 提供大语言模型API
- [shibing624/text2vec-base-chinese](https://huggingface.co/shibing624/text2vec-base-chinese) 提供中文嵌入模型
- [FAISS](https://github.com/facebookresearch/faiss) 提供向量相似度检索
- [FastAPI](https://fastapi.tiangolo.com/) 提供Web框架
- [BM25](https://github.com/dorianbrown/rank_bm25) 提供关键词检索

## 📧 联系方式

- Issues: [GitHub Issues](https://github.com/Spirtxiaoqi7/ARPM/issues)
- 作者：Spirtxiaoqi7

---

⭐ **如果本项目对您有帮助，请给个Star！**
