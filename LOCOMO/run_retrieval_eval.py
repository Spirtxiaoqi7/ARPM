"""Run LOCOMO retrieval-only evaluation.

This script does not call an LLM. It evaluates whether ARPM retrieves the
official evidence dia_id for each LOCOMO QA item.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

from common import DATA_DIR, RESULTS_DIR, add_backend_to_path, load_qas, normalize_evidence_ids, write_json, write_jsonl
from metrics import mrr, recall_at_k, summarize


def _current_round_for_session(session_id: str) -> int:
    add_backend_to_path()
    from storage.vector_store import vector_store

    chunks = vector_store.get_chat_chunks_by_session(session_id)
    if not chunks:
        return 1
    return max(int((c.get("timestamp") or {}).get("round_num", 0) or 0) for c in chunks) + 1


def retrieve_chat_vector(question: str, session_id: str, k: int) -> List[Dict]:
    add_backend_to_path()
    from storage.vector_store import vector_store

    return vector_store.search_chat_history(question, session_id=session_id, k=k)


def retrieve_arpm(question: str, session_id: str, k: int, temporal: bool) -> List[Dict]:
    add_backend_to_path()
    from core.memory_manager import memory_manager
    from core.retriever import retriever

    current_round = _current_round_for_session(session_id)
    context = retriever.retrieve(
        question,
        session_id=session_id,
        current_round=current_round,
        ablation_config={
            "rag_enabled": True,
            "kb_enabled": False,
            "chat_enabled": True,
            "temporal_enabled": temporal,
            "bm25_enabled": False,
            "disambiguation_enabled": False,
        },
        similarity_threshold=0.0,
        tuning_config={
            "chat_history_k": k,
            "similarity_threshold": 0.0,
            "decay_rate_round": 20.0,
            "decay_rate_hours": 168.0,
        },
    )
    results = context.get("chat_history", [])
    if temporal:
        results = memory_manager.apply_weights_to_results(
            results,
            current_round=current_round,
            temporal_enabled=True,
            tuning_config={
                "decay_rate_round": 20.0,
                "decay_rate_hours": 168.0,
            },
        )
    return results[:k]


def run(method: str, k: int, limit: int | None, qa_file: Path, output: Path) -> List[Dict]:
    qas = load_qas(qa_file, limit=limit)
    rows = []
    for idx, qa in enumerate(qas, start=1):
        question = qa["question"]
        session_id = qa["session_id"]
        gold = normalize_evidence_ids(qa.get("gold_evidence"))

        if method == "chat_vector":
            retrieved = retrieve_chat_vector(question, session_id, k=k)
        elif method == "arpm_retrieval":
            retrieved = retrieve_arpm(question, session_id, k=k, temporal=False)
        elif method == "arpm_temporal":
            retrieved = retrieve_arpm(question, session_id, k=k, temporal=True)
        else:
            raise ValueError(f"Unknown retrieval method: {method}")

        retrieved_ids = [str(item.get("dia_id", "")) for item in retrieved]
        row = {
            "qa_id": qa["qa_id"],
            "sample_id": qa["sample_id"],
            "session_id": session_id,
            "category": qa.get("category", ""),
            "question": question,
            "gold_answer": qa.get("gold_answer", ""),
            "gold_evidence": gold,
            "retrieved_dia_ids": retrieved_ids,
            "retrieved_chunks": [
                {
                    "dia_id": item.get("dia_id", ""),
                    "score": item.get("score", 0.0),
                    "weighted_score": item.get("weighted_score", item.get("score", 0.0)),
                    "round_num": (item.get("timestamp") or {}).get("round_num", ""),
                    "physical_time": (item.get("timestamp") or {}).get("physical_time", ""),
                    "speaker": item.get("speaker", ""),
                    "text_raw": item.get("text_raw", ""),
                }
                for item in retrieved
            ],
            "recall_at_1": recall_at_k(gold, retrieved_ids, 1),
            "recall_at_5": recall_at_k(gold, retrieved_ids, 5),
            "recall_at_10": recall_at_k(gold, retrieved_ids, 10),
            "recall_at_20": recall_at_k(gold, retrieved_ids, 20),
            "mrr": mrr(gold, retrieved_ids),
        }
        rows.append(row)
        if idx % 50 == 0:
            print(f"[LOCOMO] evaluated {idx}/{len(qas)}")

    write_jsonl(output, rows)
    write_json(output.with_suffix(".summary.json"), summarize(rows) | {"method": method, "k": k})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=["chat_vector", "arpm_retrieval", "arpm_temporal"], default="chat_vector")
    parser.add_argument("--k", type=int, default=20)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--qa-file", type=Path, default=DATA_DIR / "locomo_qa.jsonl")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    output = args.output or RESULTS_DIR / f"retrieval_{args.method}.jsonl"
    rows = run(args.method, args.k, args.limit, args.qa_file, output)
    summary = summarize(rows)
    print(f"[LOCOMO] wrote {output}")
    print(summary)


if __name__ == "__main__":
    main()
