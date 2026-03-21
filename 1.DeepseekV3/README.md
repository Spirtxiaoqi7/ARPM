# ARPM: Augmented Retrieval-based Persona Modeling

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[中文文档](README_CN.md) | [Installation](INSTALLATION_GUIDE.txt)

## 📖 Overview

ARPM (Augmented Retrieval-based Persona Modeling) is a **character-consistent dialogue system** based on RAG (Retrieval-Augmented Generation). It enables immersive role-playing conversations with persistent memory and personality consistency.

### ✨ Key Features

- 🎭 **Character Role-Playing**: Configurable character names and backgrounds via `config.json`
- 🧠 **Long-term Memory**: Hybrid retrieval (Vector Search + BM25) with time decay mechanism
- 🔍 **Smart Retrieval**: Combines semantic similarity (FAISS) and keyword matching (BM25)
- ⏰ **Time Decay**: Recent memories weighted more heavily for contextual relevance
- 📝 **Chinese Text Chunking**: Intelligent sentence-aware text segmentation (`chunker.py`)
- 🔌 **DeepSeek API**: Powered by DeepSeek's large language model
- 💻 **Multiple Interfaces**: Both CLI (`chat_loop.py`) and GUI (`chat_gui.py`) clients
- 🌐 **OpenAI-Compatible**: Provides standard OpenAI API endpoints at `/v1/chat/completions`

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   User Client   │◄───►│  DeepSeek API   │◄───►│   RAG Service   │
│ (chat_loop.py)  │     │  (Port 8004)    │     │  (Port 8003)    │
│ (chat_gui.py)   │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                         │
                               ▼                         ▼
                        ┌─────────────┐          ┌─────────────┐
                        │ DeepSeek LLM│          │ Vector DB   │
                        │   (API)     │          │(FAISS+BM25) │
                        └─────────────┘          └─────────────┘
```

## 📁 Project Structure

```
ARPM/
├── api/                          # API services
│   ├── deepseek_api.py          # DeepSeek service (port 8004)
│   ├── rag_api.py               # RAG service (port 8003)
│   └── __init__.py
├── models/                       # Embedding models (auto-downloaded)
│   └── shibing624/
│       └── text2vec-base-chinese/
├── data/                         # Data storage
├── vectors/                      # Vector index storage (auto-generated)
├── logs/                         # Conversation logs (auto-generated)
├── venv/                         # Virtual environment (user-created)
├── .env                          # API key configuration
├── config.json                   # Character configuration
├── requirements.txt              # Python dependencies
├── chunker.py                   # Text chunking tool
├── chat_loop.py                 # CLI client
├── chat_gui.py                  # GUI client
├── RUN.bat                      # Windows startup script
├── extract_chat.py              # Chat extraction utility
├── README.md                    # This file
├── README_CN.md                 # Chinese documentation
├── INSTALLATION_GUIDE.txt       # Detailed setup guide
├── LICENSE                      # MIT License
└── CONTRIBUTING.md              # Contribution guidelines
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- DeepSeek API Key ([Get one here](https://platform.deepseek.com/))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Spirtxiaoqi7/ARPM.git
cd ARPM

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure API key
cp .env.example .env
# Edit .env and add your DeepSeek API key: DEEPSEEK_API_KEY=your_key_here

# 6. Download embedding model (auto-download on first run, or manual)
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('shibing624/text2vec-base-chinese', cache_folder='models/shibing624/text2vec-base-chinese')"
```

### Running the System

#### Option 1: One-Click Start (Windows)
```bash
# Double-click or run:
RUN.bat
```

#### Option 2: Manual Start
```bash
# Terminal 1: Start RAG Service
cd api && uvicorn rag_api:app --host 0.0.0.0 --port 8003

# Terminal 2: Start DeepSeek Service
cd api && uvicorn deepseek_api:app --host 0.0.0.0 --port 8004

# Terminal 3: Start CLI Client
python chat_loop.py
```

#### Option 3: GUI Client
```bash
python chat_gui.py
```

## ⚙️ Configuration

### Character Configuration (`config.json`)

```json
{
    "character_name": "Luo Ji",
    "character_background": "You are Luo Ji, I am Cheng Xin. You are a character from Three-Body Problem..."
}
```

### Environment Variables (`.env`)

```bash
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

⚠️ **Never commit your `.env` file!** It contains sensitive API keys.

## 📚 Usage

### Adding Documents to RAG Memory

```bash
# Basic usage - add text file to RAG
python chunker.py your_file.txt --add

# Advanced options
python chunker.py your_file.txt \
    --add \
    --target-size 250 \
    --overlap 1 \
    --batch-size 500 \
    --timestamp 0
```

### Chatting

Once services are running:

1. **CLI Mode**: Type your message and press Enter
2. **GUI Mode**: Use the graphical interface to chat
3. **Type `exit`** or close window to quit

### API Endpoints

#### RAG Service (http://127.0.0.1:8003)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/add_document` | POST | Add documents to RAG |
| `/search` | POST | Vector similarity search |
| `/search_hybrid` | POST | Hybrid (vector + BM25) search with time decay |
| `/health` | GET | Health check |
| `/stats` | GET | Statistics |

#### DeepSeek Service (http://127.0.0.1:8004)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate` | POST | Generate character response |
| `/v1/chat/completions` | POST | OpenAI-compatible API |
| `/health` | GET | Health check |
| `/config` | GET | Current character config |

## 🔧 Advanced Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_PORT` | 8003 | RAG service port |
| `DEEPSEEK_PORT` | 8004 | DeepSeek service port |
| `RAG_HOST` | 127.0.0.1 | RAG service host |
| `DEEPSEEK_HOST` | 127.0.0.1 | DeepSeek service host |

### Chunker Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--target-size` | 250 | Target chunk size (characters) |
| `--overlap` | 1 | Number of overlapping sentences |
| `--min-size` | 50 | Minimum chunk size |
| `--batch-size` | 500 | Batch size for adding documents |
| `--timestamp` | 0 | Timestamp for temporal weighting |

## 🛠️ Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError`
- **Solution**: Ensure virtual environment is activated: `venv\Scripts\activate`

**Issue**: `DeepSeek API key not found`
- **Solution**: Check `.env` file exists and contains valid `DEEPSEEK_API_KEY`

**Issue**: `Model not found`
- **Solution**: The model will auto-download on first run, or manually download from [HuggingFace](https://huggingface.co/shibing624/text2vec-base-chinese)

**Issue**: `Port already in use`
- **Solution**: Kill existing processes or change ports via environment variables

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2026 Spirtxiaoqi7

## 🙏 Acknowledgments

- [DeepSeek](https://deepseek.com/) for providing the LLM API
- [shibing624/text2vec-base-chinese](https://huggingface.co/shibing624/text2vec-base-chinese) for the Chinese embedding model
- [FAISS](https://github.com/facebookresearch/faiss) for vector similarity search
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [BM25](https://github.com/dorianbrown/rank_bm25) for keyword retrieval

## 📧 Contact & Support

- Issues: [GitHub Issues](https://github.com/Spirtxiaoqi7/ARPM/issues)
- Author: Spirtxiaoqi7

---

⭐ **Star this repository if you find it helpful!**
