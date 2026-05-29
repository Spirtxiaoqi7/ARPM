"""Generate LOCOMO QA answers with OpenAI-compatible APIs."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

from common import DATA_DIR, RESULTS_DIR, add_backend_to_path, load_qas, load_system_prompt, normalize_evidence_ids, write_json, write_jsonl
from metrics import exact_match, mrr, recall_at_k, summarize, token_f1
from prompts import build_prompt


def retrieve(question: str, session_id: str, k: int) -> List[Dict]:
    add_backend_to_path()
    from storage.vector_store import vector_store

    return vector_store.search_chat_history(question, session_id=session_id, k=k)


def call_llm(prompt: str, api_key: str, base_url: str, model: str, temperature: float, max_tokens: int) -> str:
    import openai

    client = openai.OpenAI(api_key=api_key, base_url=base_url.rstrip("/"))
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Follow the benchmark prompt. Output only the final short answer."},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def run(args: argparse.Namespace) -> List[Dict]:
    qas = load_qas(args.qa_file, limit=args.limit)
    system_prompt = load_system_prompt(args.system_prompt_file)
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("ARPM_API_KEY") or ""
    base_url = args.base_url or os.environ.get("OPENAI_BASE_URL") or os.environ.get("ARPM_BASE_URL") or "https://api.deepseek.com"
    model = args.model or os.environ.get("OPENAI_MODEL") or os.environ.get("ARPM_MODEL") or "deepseek-chat"
    if not api_key and not args.dry_run:
        raise RuntimeError("Missing API key. Set OPENAI_API_KEY/ARPM_API_KEY or pass --api-key.")

    rows = []
    for idx, qa in enumerate(qas, start=1):
        retrieved = retrieve(qa["question"], qa["session_id"], k=args.k)
        prompt = build_prompt(args.method, qa["question"], retrieved, system_prompt=system_prompt)
        pred = "" if args.dry_run else call_llm(
            prompt,
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        gold = normalize_evidence_ids(qa.get("gold_evidence"))
        retrieved_ids = [str(item.get("dia_id", "")) for item in retrieved]
        row = {
            "qa_id": qa["qa_id"],
            "sample_id": qa["sample_id"],
            "session_id": qa["session_id"],
            "category": qa.get("category", ""),
            "question": qa["question"],
            "gold_answer": qa.get("gold_answer", ""),
            "pred_answer": pred,
            "gold_evidence": gold,
            "retrieved_dia_ids": retrieved_ids,
            "retrieved_chunks": [
                {
                    "dia_id": item.get("dia_id", ""),
                    "round_num": (item.get("timestamp") or {}).get("round_num", ""),
                    "physical_time": (item.get("timestamp") or {}).get("physical_time", ""),
                    "speaker": item.get("speaker", ""),
                    "text_raw": item.get("text_raw", ""),
                    "score": item.get("score", 0.0),
                }
                for item in retrieved
            ],
            "prompt": prompt if args.save_prompts else "",
            "recall_at_1": recall_at_k(gold, retrieved_ids, 1),
            "recall_at_5": recall_at_k(gold, retrieved_ids, 5),
            "recall_at_10": recall_at_k(gold, retrieved_ids, 10),
            "recall_at_20": recall_at_k(gold, retrieved_ids, 20),
            "mrr": mrr(gold, retrieved_ids),
            "em": exact_match(pred, qa.get("gold_answer", "")) if pred else 0.0,
            "f1": token_f1(pred, qa.get("gold_answer", "")) if pred else 0.0,
        }
        rows.append(row)
        if idx % 10 == 0:
            print(f"[LOCOMO] generated {idx}/{len(qas)}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=["plain_rag", "arpm_protocol", "arpm_full"], default="plain_rag")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--qa-file", type=Path, default=DATA_DIR / "locomo_qa.jsonl")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--system-prompt-file", type=Path, default=None)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--save-prompts", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    output = args.output or RESULTS_DIR / f"qa_{args.method}.jsonl"
    rows = run(args)
    write_jsonl(output, rows)
    write_json(output.with_suffix(".summary.json"), summarize(rows) | {"method": args.method, "k": args.k})
    print(f"[LOCOMO] wrote {output}")
    print(summarize(rows))


if __name__ == "__main__":
    main()
