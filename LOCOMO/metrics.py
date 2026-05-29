"""Metrics for LOCOMO QA and evidence retrieval."""
from __future__ import annotations

import re
import string
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Sequence


def _normalize_answer(text: Any) -> str:
    text = str(text).lower()
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    text = "".join(ch for ch in text if ch not in string.punctuation)
    text = " ".join(text.split())
    return text


def exact_match(prediction: Any, gold: Any) -> float:
    return float(_normalize_answer(prediction) == _normalize_answer(gold))


def token_f1(prediction: Any, gold: Any) -> float:
    pred_tokens = _normalize_answer(prediction).split()
    gold_tokens = _normalize_answer(gold).split()
    if not pred_tokens and not gold_tokens:
        return 1.0
    if not pred_tokens or not gold_tokens:
        return 0.0
    common = Counter(pred_tokens) & Counter(gold_tokens)
    same = sum(common.values())
    if same == 0:
        return 0.0
    precision = same / len(pred_tokens)
    recall = same / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def recall_at_k(gold_ids: Sequence[str], retrieved_ids: Sequence[str], k: int) -> float:
    gold = set(gold_ids)
    if not gold:
        return 0.0
    retrieved = set(retrieved_ids[:k])
    return float(bool(gold & retrieved))


def mrr(gold_ids: Sequence[str], retrieved_ids: Sequence[str]) -> float:
    gold = set(gold_ids)
    if not gold:
        return 0.0
    for rank, dia_id in enumerate(retrieved_ids, start=1):
        if dia_id in gold:
            return 1.0 / rank
    return 0.0


def summarize(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(records)
    if not rows:
        return {"count": 0}

    numeric_keys = [
        "recall_at_1",
        "recall_at_5",
        "recall_at_10",
        "recall_at_20",
        "mrr",
        "em",
        "f1",
    ]
    summary = {"count": len(rows)}
    for key in numeric_keys:
        values = [float(row.get(key, 0.0) or 0.0) for row in rows if key in row]
        if values:
            summary[key] = sum(values) / len(values)

    by_category = defaultdict(list)
    for row in rows:
        by_category[str(row.get("category", ""))].append(row)

    summary["by_category"] = {}
    for category, group in sorted(by_category.items()):
        sub = {"count": len(group)}
        for key in numeric_keys:
            values = [float(row.get(key, 0.0) or 0.0) for row in group if key in row]
            if values:
                sub[key] = sum(values) / len(values)
        summary["by_category"][category] = sub
    return summary
