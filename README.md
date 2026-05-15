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
## Engineering Evolution: V1.0–V3.0

This section summarizes the engineering evolution of ARPM from its early research prototype to a more complete memory-augmented dialogue system. The development process was not a simple accumulation of features. Each version addressed a specific bottleneck exposed by the previous stage: V1.0 established the core research hypothesis, V2.0 closed the engineering loop, and V3.0 strengthened retrieval, temporal modeling, and system maintainability.

### V1.0: Research Prototype and Core Hypothesis

ARPM V1.0 was built around a central observation: long-term role-playing dialogue systems often fail not because the base model lacks language ability, but because the system lacks stable external memory governance and internal role-consistency constraints.

The first version focused on proving the feasibility of a training-free approach to long-term persona consistency. Instead of fine-tuning a model for each character, ARPM introduced an external memory and prompting framework that could be deployed with ordinary API-based LLMs.

The main mechanisms in V1.0 included:

- **Analysis-based generation protocol**  
  The model was required to reason about the character, situation, and retrieved memory before producing the final response. This reduced direct user-alignment drift and made the model less likely to abandon the intended persona.

- **Time-aware memory weighting**  
  Dialogue memory was weighted by dialogue rounds rather than only by semantic similarity. This allowed recent memories to remain salient while preserving permanent persona-related information.

- **Recursive Chinese text chunking**  
  The system used Chinese punctuation-aware recursive chunking to avoid the failure modes of generic English-oriented chunk splitters.

- **Parent-child chunk structure**  
  Smaller child chunks improved semantic retrieval precision, while larger parent chunks preserved enough surrounding context for generation.

- **Low-resource deployment design**  
  The system used a lightweight local embedding model and ordinary vector retrieval components, making it deployable by individual developers without expensive GPU resources.

At this stage, ARPM was primarily a research prototype. It demonstrated that persona consistency could be improved through external memory, temporal weighting, and analysis-driven generation, but several implementation details were still incomplete or manually coordinated.

### V2.0: Engineering Closure and Web-Based System

ARPM V2.0 shifted the focus from conceptual validation to usable engineering implementation. The goal of this stage was to close the gap between a research prototype and a deployable application.

The major update in V2.0 was the reconstruction of the system into a single Flask-based web application. Compared with the earlier microservice/script-based prototype, the new architecture simplified deployment and made the system easier to run, test, and demonstrate.

Key engineering updates included:

- **Single Flask application architecture**  
  The previous separated service structure was integrated into a lightweight web application. Users could launch the complete system through a simpler local workflow.

- **Complete web frontend**  
  V2.0 added a browser-based interface for dialogue, API configuration, knowledge-base upload, session management, and parameter adjustment.

- **Standardized vector storage**  
  The vector database was reorganized into explicit files for parent chunks, child chunks, child-to-parent mappings, metadata, and FAISS indexes. This made the retrieval layer more transparent and easier to maintain.

- **Incremental indexing**  
  New documents could be added without rebuilding the entire knowledge base from scratch. The system could encode new child chunks, append them to the FAISS index, and update JSON metadata files.

- **Closed parent-child retrieval loop**  
  Retrieval was implemented as “child matching, parent recall.” Queries were matched against smaller child chunks for precision, then mapped back to parent chunks for complete contextual injection.

- **Forced analysis-response protocol**  
  The `<analysis>...</analysis><response>...</response>` structure was made into a hard generation constraint for each round. The backend parsed the model output and returned only the response part to the user, while analysis content could be stored for internal inspection.

- **Asynchronous memory persistence**  
  Dialogue memory was written asynchronously to avoid blocking user interaction with disk I/O.

V2.0 corrected several practical weaknesses of V1.0. The system no longer depended mainly on manually coordinated scripts. It became a usable local application with knowledge-base upload, session persistence, structured storage, and browser interaction.

The main contribution of V2.0 was therefore not a new theoretical mechanism, but engineering closure. It made ARPM easier to reproduce, inspect, and deploy.

### V3.0: Algorithmic Enhancement and System Reconstruction

ARPM V3.0 moved beyond basic engineering closure and focused on retrieval quality, memory evolution, and long-term system stability.

As the system was tested over longer conversations, several new problems appeared. Standard BM25 and vector retrieval were not enough for role-playing dialogue. Some important memories needed to become stronger rather than weaker over time. Long-running systems also needed diagnostic tools to detect damaged indexes, inconsistent metadata, and broken session files.

V3.0 addressed these issues through several algorithmic and architectural updates.

#### BM25+ Hybrid Retrieval

V3.0 introduced an enhanced BM25+ retrieval module. The goal was to improve sparse retrieval without adding training cost.

The BM25+ module included:

- English stemming through Porter Stemmer;
- English and Chinese stop-word filtering;
- field weighting for titles, tags, and content;
- coverage rewards when a document matched all query terms;
- RRF fusion between vector retrieval and BM25+ ranking.

This made retrieval more robust for mixed Chinese-English character settings, names, locations, tags, and structured knowledge entries.

#### Bidirectional Temporal Memory Model

Earlier versions mainly used time decay. V3.0 extended temporal modeling by introducing two directions of memory evolution:

- **exponential decay**, where ordinary memories gradually lose weight over dialogue rounds;
- **nostalgic enhancement**, where certain long-term background memories become more important as time passes.

This reflected a more flexible view of memory. Not all memories should fade. Some background experiences, emotional anchors, or identity-defining events may become stronger in long-term interaction.

V3.0 also introduced temporal-blind memory flags for core persona information, allowing foundational character facts to remain stable regardless of recency.

#### Adaptive Keyword Boosting

V3.0 added a keyword boosting mechanism for knowledge chunks. Each chunk could contain weighted keywords. When a query matched these keywords, the retrieval score could be dynamically boosted.

To avoid abuse, the system also introduced multi-match scaling. A small number of keyword hits would only receive partial boosting, while stronger boosts required broader matching. This prevented keyword stuffing from overwhelming semantic relevance.

#### Scene-Aware Memory Architecture

Role-playing dialogue often evolves through scenes rather than isolated turns. V3.0 introduced scene-aware memory management to model this structure.

A scene was treated as a coherent narrative unit across several dialogue rounds. Memories inside the same scene could share a temporal reference point, and cross-scene retrieval could apply different decay logic. This made memory behavior more aligned with narrative continuity.

#### Self-Diagnosis and Repair

V3.0 also introduced system-level diagnostic tools. The diagnostic layer checked:

- vector database file integrity;
- metadata consistency;
- FAISS index validity;
- model loading status;
- disk space;
- session file completeness;
- orphan chunk detection;
- scene data integrity.

The goal was to make the system maintainable during long-term use. A memory system is not only a retrieval algorithm; it also needs protection against data corruption, incomplete writes, broken mappings, and index drift.

### Design Philosophy Across V1.0–V3.0

The evolution from V1.0 to V3.0 reflects a shift in ARPM’s design philosophy.

V1.0 asked whether persona consistency could be improved without fine-tuning.  
V2.0 asked whether the idea could be turned into a usable system.  
V3.0 asked whether the system could remain accurate, stable, and maintainable during long-term operation.

Across these versions, several principles remained consistent:

1. **Training-free first**  
   ARPM does not assume that each persona requires model fine-tuning. Instead, it treats persona consistency as a memory governance and prompt-construction problem.

2. **External memory over model identity**  
   The system does not rely on the base model itself to remember everything. Long-term continuity is maintained through external memory structures, retrieval rules, temporal weighting, and prompt injection.

3. **Analysis before response**  
   The model should not directly imitate a character at the surface level. It should first analyze the role, context, memory, and user intent before generating the final response.

4. **Retrieval is not enough**  
   A memory system cannot rely only on vector similarity. Keyword retrieval, temporal weighting, parent-child chunking, scene structure, and diagnostic mechanisms are all necessary for long-term reliability.

5. **Low-resource deployability**  
   ARPM was designed for individual developers and small teams. It avoids expensive fine-tuning and heavyweight infrastructure whenever possible.

6. **Long-term interaction as the real test**  
   The system is evaluated not only by single-turn accuracy, but by its ability to preserve persona, memory, boundaries, and interaction style across extended dialogue.

### Summary

From V1.0 to V3.0, ARPM evolved from a research prototype into a more complete long-term dialogue system.

V1.0 established the core mechanisms: analysis-based generation, time-aware memory, Chinese chunking, and low-resource retrieval.

V2.0 completed the engineering loop: Flask web application, standardized vector storage, parent-child retrieval, forced analysis-response parsing, and asynchronous memory persistence.

V3.0 enhanced the retrieval and memory model: BM25+ hybrid retrieval, bidirectional temporal memory, adaptive keyword boosting, scene-aware memory, and self-diagnosis.

This development path laid the foundation for later versions of ARPM, especially the transition toward heterogeneous temporal memory governance, cross-model continuity evaluation, and more auditable long-term persona consistency.


### V4.0: Heterogeneous Temporal Memory Governance and Cross-Model Continuity

ARPM V4.0 marked the transition from a role-playing memory system to a more formal external memory governance framework for long-term LLM persona consistency.

Compared with V1.0–V3.0, V4.0 no longer treated memory as a single retrieval component attached to a role-playing chatbot. Instead, it reframed long-term persona consistency as a heterogeneous temporal governance problem. The key question became: when the foundation model changes, the context window is cleared, and the knowledge base contains heavy noise, can an external memory system still preserve facts, timelines, identity boundaries, and interaction continuity?

The corresponding arXiv preprint is:

```text
A Heterogeneous Temporal Memory Governance Framework for Long-Term LLM Persona Consistency
arXiv:2605.14802
https://arxiv.org/abs/2605.14802


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
