# LOCOMO QA Baseline Import

This directory contains the LOCOMO QA import files for ARPM-v4.

## Data Source

The current import uses the official LOCOMO sample file:

```text
data/locomo10.json
```

The file follows the official LOCOMO structure:

```text
sample
  sample_id
  conversation
    speaker_a
    speaker_b
    session_1_date_time
    session_1
      dia_id
      speaker
      text
    session_2_date_time
    session_2
    ...
  qa
    question
    answer
    category
    evidence
```

## Split Rule

For QA, the importer uses **one official dialogue turn as one ARPM chat-memory chunk**.

Reason:

- LOCOMO evidence is annotated by `dia_id`.
- Retrieval evaluation needs exact alignment between retrieved chunks and gold evidence.
- Re-chunking by token, sentence, or ARPM knowledge parent/child chunks would blur evidence boundaries.

Therefore, no parent-child knowledge chunking is applied for the QA baseline.

## Metadata Mapping

Each LOCOMO sample becomes one ARPM session:

```text
sample_id=conv-26 -> session_id=locomo_conv-26
```

Each official dialogue turn becomes one chat chunk:

```text
dia_id=D1:3 -> chunk_id=conv-26_D1_3
```

Indexed text format:

```text
[LOCOMO sample=conv-26 session=1 time=1:56 pm on 8 May, 2023 round=3 speaker=Caroline dia_id=D1:3]
Caroline: ...
```

Stored metadata:

```json
{
  "benchmark": "locomo",
  "sample_id": "conv-26",
  "session_id": "locomo_conv-26",
  "session_num": 1,
  "session_time_raw": "1:56 pm on 8 May, 2023",
  "timestamp": {
    "round_num": 3,
    "physical_time": "2023-05-08T13:56:00"
  },
  "speaker": "Caroline",
  "dia_id": "D1:3",
  "text_raw": "..."
}
```

## Generated Files

```text
data/locomo10.json             Official source sample file
data/locomo_qa.jsonl           Flattened QA records for evaluation
data/import_manifest.json      Import summary
```

Runtime outputs:

```text
runtime/arpm-app/data/vector_db/chat/locomo_*/metadata.json
runtime/arpm-app/data/vector_db/chat/locomo_*/faiss.index
runtime/arpm-app/data/memory_db/session_locomo_*.json
runtime/arpm-app/locomo_import_manifest.json
```

The knowledge base is intentionally left empty for the first QA baseline.

## Re-import

From the project root:

```bash
python benchmarks/locomo/import_locomo_qa.py --batch-size 64
```

Before re-importing for a clean QA run, clear:

```text
runtime/arpm-app/data/vector_db/knowledge
runtime/arpm-app/data/vector_db/chat
runtime/arpm-app/data/memory_db
runtime/arpm-app/admin
runtime/arpm-app/logs
```

## First QA Baselines

Recommended order:

1. `last_k_context`
2. `full_context`
3. `chat_vector`
4. `chat_vector_temporal`
5. `arpm_full`
6. `evidence_oracle`

For retrieval-only evaluation, use `gold_evidence` from `locomo_qa.jsonl` and compare it with retrieved chunk `dia_id`.
