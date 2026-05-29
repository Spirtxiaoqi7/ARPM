# LOCOMO QA Scripts

This folder is the standalone LOCOMO QA benchmark workspace for ARPM-v4.

It is intentionally separated from the frontend and normal chat workflow. The
goal is to evaluate long-conversation QA with clean evidence alignment.

## Current Split

LOCOMO official QA evidence is annotated by `dia_id`, so the importer uses:

```text
one official dialogue turn = one ARPM chat-memory chunk
```

No ARPM knowledge-base parent/child chunking is used for the first QA baseline.
The knowledge base remains empty. All LOCOMO turns are stored as chat memory.

Each indexed chunk keeps:

```text
sample_id
session_id
session_num
session_time_raw
timestamp.round_num
timestamp.physical_time
speaker
dia_id
text_raw
```

The injected prompt block is sorted chronologically by `round_num`, with earlier
turns first and later turns last. Each memory block includes physical time,
round number, speaker, and dia_id.

## Files

```text
data/locomo10.json              Official LOCOMO sample data
data/locomo_qa.jsonl            Flattened QA records
data/import_manifest.json       Import summary
import_locomo_qa.py             Import LOCOMO into ARPM chat memory
run_retrieval_eval.py           Retrieval-only baseline
run_qa_generation.py            LLM QA generation baseline
make_zh_report.py               Chinese-readable CSV report
prompts.py                      Prompt builders
metrics.py                      EM/F1/Recall/MRR metrics
common.py                       Shared paths and IO helpers
results/                        Outputs
```

## Run Retrieval First

This does not call an LLM and costs no API money.

```bash
python LOCOMO/run_retrieval_eval.py --method chat_vector --k 20 --limit 100
python LOCOMO/make_zh_report.py --input LOCOMO/results/retrieval_chat_vector.jsonl
```

Full retrieval run:

```bash
python LOCOMO/run_retrieval_eval.py --method chat_vector --k 20
```

Other retrieval modes:

```bash
python LOCOMO/run_retrieval_eval.py --method arpm_retrieval --k 20
python LOCOMO/run_retrieval_eval.py --method arpm_temporal --k 20
```

## Run QA Generation

Generation uses English questions and English answers for official metric
compatibility. The Chinese report is only for human reading.

Environment variables:

```bash
set OPENAI_API_KEY=your_key
set OPENAI_BASE_URL=https://api.deepseek.com
set OPENAI_MODEL=deepseek-chat
```

Small dry run without API call:

```bash
python LOCOMO/run_qa_generation.py --method plain_rag --limit 3 --dry-run --save-prompts
```

Small real run:

```bash
python LOCOMO/run_qa_generation.py --method plain_rag --limit 20
python LOCOMO/make_zh_report.py --input LOCOMO/results/qa_plain_rag.jsonl
```

ARPM protocol run:

```bash
python LOCOMO/run_qa_generation.py --method arpm_protocol --limit 20
```

ARPM full prompt injection run:

```bash
python LOCOMO/run_qa_generation.py --method arpm_full --limit 20
```

## Prompt Methods

`plain_rag`:

```text
LOCOMO QA instruction + retrieved memory blocks + question
```

`arpm_protocol`:

```text
original system prompt / analysis protocol
+ LOCOMO QA instruction
+ retrieved memory blocks
+ question
```

`arpm_full`:

```text
original system prompt / analysis protocol
+ ARPM chronological memory injection rule
+ LOCOMO QA instruction
+ chronological retrieved memory
+ question
```

Use `--system-prompt-file path/to/prompt.txt` if you want to inject the exact
paper/system prompt you wrote before.

## Outputs

Retrieval:

```text
LOCOMO/results/retrieval_chat_vector.jsonl
LOCOMO/results/retrieval_chat_vector.summary.json
LOCOMO/results/retrieval_chat_vector.zh.csv
```

Generation:

```text
LOCOMO/results/qa_plain_rag.jsonl
LOCOMO/results/qa_plain_rag.summary.json
LOCOMO/results/qa_plain_rag.zh.csv
```
