# ARPM v3.0 — Analysis-Based Role-Playing with Memory

> **Status: Early Public Prototype**
>
> ARPM V3 is an early public prototype of the ARPM project.  
> It explores analysis-based generation, retrieval-augmented dialogue memory, and long-term persona consistency.
>
> Newer internal versions have moved toward **External Fluid Memory (EFM)**, focusing on cross-model continuity, time-aware retrieval, memory governance, promotion, rollback, and auditable long-term dialogue state.
>
> This repository remains public as an early implementation reference.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-3.0-green.svg)](https://github.com/Spirtxiaoqi7/ARPM)

---

## What is ARPM?

**ARPM** is an experimental memory architecture for long-term AI dialogue.

Version 3.0 focuses on combining **analysis-based generation** with **retrieval-augmented memory**, so that an AI character or dialogue agent can maintain better consistency across long conversations.

It is not only a prompt template, and it is not only a normal RAG chatbot.  
ARPM V3 attempts to give the model structured external evidence before generation, including dialogue history, knowledge fragments, time-aware memory weights, and retrieval signals.

The core idea is simple:

> A model can be replaced.  
> A broken memory chain cannot.

---

## Current Research Direction

ARPM V3 is the public early-stage version.

The current research direction has evolved into ARPM V4/V5, with a stronger focus on:

- External Fluid Memory
- Cross-model persona continuity
- Time-aware dialogue evidence
- Dual-source retrieval
- Dual-timescale memory modeling
- Memory promotion and rollback
- Auditable long-term dialogue logs
- Analysis-style generation instead of pure roleplay prompting

In later versions, memory is treated as a governable object that can be recalled, promoted, merged, rolled back, and audited, rather than as static text simply injected into the prompt.

---

## Core Features

### Analysis-Based Dialogue Protocol

ARPM V3 uses an analysis-first dialogue protocol.

- First-turn silent analysis
- Full response generation after memory initialization
- Retrieval-enhanced dialogue state
- Persona consistency through external memory evidence
- Reduced dependence on pure prompt-based roleplay

The goal is to make the model respond based on retrieved context and structured memory, rather than relying only on the current context window.

---

### Cognitive Memory Architecture

ARPM V3 includes an early cognitive memory design for long-form AI interaction.

- **ARPM Turn Protocol**: first-round analysis and later full-response generation
- **Time-aware Memory**: memory decay and nostalgia-style enhancement
- **Scene-aware Memory**: grouped management of plot or conversation segments
- **Real-time Archiving**: long context is automatically split and archived
- **Session Isolation**: multiple sessions are kept separate to reduce memory confusion

This version is an early attempt at making long conversations more stable and inspectable.

---

### Retrieval-Augmented Generation

ARPM V3 uses hybrid retrieval to provide external evidence for generation.

- **BM25+ Retrieval**: keyword matching with field weighting and coverage reward
- **Vector Search**: Chinese semantic retrieval based on `text2vec`
- **RRF Fusion**: combines keyword and vector retrieval results
- **Keyword Boosting**: dynamic weighting with anti-abuse constraints
- **Knowledge Base Support**: uploaded documents can be chunked and searched

The retrieval layer is designed to support both factual knowledge and dialogue memory.

---

### Ablation and Experiment Support

ARPM V3 includes component-level switches for experimental comparison.

- **ARPM Global Switch**: compare pure LLM dialogue with enhanced dialogue
- **BM25+ Switch**: test keyword retrieval contribution
- **CoT Reranking Switch**: test reasoning-assisted reranking
- **Time Decay Switch**: test temporal memory weighting
- **Keyword Boost Switch**: test explicit keyword intervention
- **Feedback Collection**: collect likes, dislikes, and regenerated responses

These features were designed to observe how each component affects long-term dialogue consistency.

---

### Practical System Functions

ARPM V3 also includes several practical tools for local experimentation.

- **System Diagnostics**: health checks and basic auto-repair
- **Knowledge Base Management**: upload, chunk, search, and manage fragments
- **Chat History Management**: delete single messages or clear sessions
- **Content Archive**: store regenerated or reported content for inspection
- **Local Deployment**: runs on CPU without requiring a GPU

This makes V3 suitable as a local prototype for testing memory-augmented AI dialogue.

---

## What ARPM V3 Is Not

ARPM V3 is an early prototype and should not be confused with the latest ARPM architecture.

It is not:

- A finished product
- A complete external memory governance system
- A full implementation of ARPM V4/V5
- A general-purpose enterprise RAG platform
- A replacement for later External Fluid Memory designs

It is best understood as an early public implementation that explores the first stage of ARPM:  
**retrieval-enhanced, analysis-based long-term dialogue memory.**
