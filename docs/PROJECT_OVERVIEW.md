# ARPM Project Overview

## Summary

**ARPM**, short for **Analysis-Based Role-Playing with Memory**, is an open-source long-term memory framework for role-playing dialogue systems and LLM persona consistency research. The project combines retrieval-augmented generation, external memory governance, temporal weighting, and a lightweight web interface.

ARPM v4.0 reframes long-term persona consistency as a heterogeneous temporal memory governance problem. Instead of relying on a foundation model to remember all facts and interaction history, ARPM stores and retrieves external memory from structured knowledge bases and session-level dialogue histories.

中文概述：ARPM 是一个面向长期角色一致性、角色扮演对话、知识库交互和可复现实验的开源系统。它通过外部记忆、混合检索、时态权重和提示词注入，让普通 OpenAI 兼容大模型在长对话中更稳定地保持人物设定、事实连续性和互动边界。

## Core Concepts

### External Memory Governance

ARPM treats long-term consistency as a memory governance problem. Persona facts, background documents, dialogue history, and recalled context are managed outside the base model, then injected into the prompt at generation time.

### Hybrid Retrieval

The knowledge-base retrieval path combines:

- FAISS vector retrieval for semantic matching.
- BM25+ keyword retrieval for names, places, entities, and exact concepts.
- Reciprocal Rank Fusion for combining retrieval signals.
- Parent-child chunk recall for balancing precision and context.

### Temporal Memory

ARPM records both dialogue round order and physical time. Retrieved memory can then be reranked by temporal signals, making recent dialogue salient while preserving important long-term anchors.

### Chronological Prompt Injection

Recalled memory is injected in chronological order. This helps the model reconstruct continuity from earlier events to later events instead of receiving retrieved blocks as an unordered list.

## Target Users

- LLM application developers building memory-augmented chat systems.
- Researchers studying persona consistency, role-playing dialogue, and long-term RAG.
- Students reproducing experiments around temporal memory and retrieval.
- Writers or creators testing local character dialogue systems.
- Developers building Chinese or mixed Chinese-English knowledge-base chatbots.

## Technical Stack

- Python and Flask for the backend.
- HTML, CSS, and vanilla JavaScript for the frontend.
- FAISS for vector search.
- `shibing624/text2vec-base-chinese` for Chinese sentence embeddings.
- BM25+ style keyword retrieval with `jieba` tokenization.
- OpenAI-compatible chat completion APIs.
- Docker Compose for optional containerized deployment.

## Research Context

The corresponding preprint is:

```text
A Heterogeneous Temporal Memory Governance Framework for Long-Term LLM Persona Consistency
arXiv:2605.14802
https://arxiv.org/abs/2605.14802
```

The repository also includes experimental notes, cross-model logs, formula descriptions, and implementation summaries that can support reproducibility work.

## Public Description

One-sentence description:

```text
ARPM is a long-term memory RAG framework for role-playing dialogue and LLM persona consistency research.
```

Short Chinese description:

```text
ARPM 是一个用于长期角色一致性、角色扮演对话和记忆增强 RAG 的开源研究系统。
```

## Suggested External Links

- GitHub repository: <https://github.com/Spirtxiaoqi7/ARPM>
- arXiv preprint: <https://arxiv.org/abs/2605.14802>

