"""Create a Chinese-readable CSV report from LOCOMO JSONL results.

This script does not translate with an LLM by default. It produces a UTF-8 BOM
CSV with English source text plus Chinese column names and hit summaries, so it
can be opened directly in Excel. If you need full translation later, add it as a
separate display-only step; benchmark metrics should remain based on English.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from common import RESULTS_DIR, read_jsonl, truncate_text, write_csv


def _yes(value: Any) -> str:
    return "是" if float(value or 0.0) > 0 else "否"


def build_rows(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for record in records:
        chunks = record.get("retrieved_chunks", []) or []
        top_chunks = []
        for chunk in chunks[:5]:
            top_chunks.append(
                f"{chunk.get('dia_id', '')} | round={chunk.get('round_num', '')} | "
                f"time={chunk.get('physical_time', '')} | {chunk.get('speaker', '')}: "
                f"{truncate_text(chunk.get('text_raw', ''), 220)}"
            )
        rows.append({
            "QA编号": record.get("qa_id", ""),
            "样本": record.get("sample_id", ""),
            "类别": record.get("category", ""),
            "英文问题": record.get("question", ""),
            "官方答案": record.get("gold_answer", ""),
            "模型答案": record.get("pred_answer", ""),
            "官方证据dia_id": "; ".join(record.get("gold_evidence", []) or []),
            "召回dia_id": "; ".join(record.get("retrieved_dia_ids", []) or []),
            "Hit@1": _yes(record.get("recall_at_1", 0)),
            "Hit@5": _yes(record.get("recall_at_5", 0)),
            "Hit@10": _yes(record.get("recall_at_10", 0)),
            "MRR": record.get("mrr", ""),
            "EM": record.get("em", ""),
            "F1": record.get("f1", ""),
            "Top5召回片段": "\n\n".join(top_chunks),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=RESULTS_DIR / "retrieval_chat_vector.jsonl")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    rows = build_rows(list(read_jsonl(args.input)))
    output = args.output or args.input.with_suffix(".zh.csv")
    fieldnames = [
        "QA编号",
        "样本",
        "类别",
        "英文问题",
        "官方答案",
        "模型答案",
        "官方证据dia_id",
        "召回dia_id",
        "Hit@1",
        "Hit@5",
        "Hit@10",
        "MRR",
        "EM",
        "F1",
        "Top5召回片段",
    ]
    write_csv(output, rows, fieldnames)
    print(f"[LOCOMO] wrote {output}")


if __name__ == "__main__":
    main()
