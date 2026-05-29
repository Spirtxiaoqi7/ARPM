"""Shared helpers for LOCOMO benchmark scripts."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


LOCOMO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = LOCOMO_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
DATA_DIR = LOCOMO_DIR / "data"
RESULTS_DIR = LOCOMO_DIR / "results"


def add_backend_to_path() -> None:
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def load_qas(path: Optional[Path] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    qa_path = path or DATA_DIR / "locomo_qa.jsonl"
    qas = []
    for record in read_jsonl(qa_path):
        qas.append(record)
        if limit is not None and len(qas) >= limit:
            break
    return qas


def normalize_evidence_ids(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def load_system_prompt(path: Optional[Path]) -> str:
    if not path:
        return ""
    return path.read_text(encoding="utf-8")


def truncate_text(text: str, limit: int = 400) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "..."
