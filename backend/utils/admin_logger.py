"""Append-only experiment logs for prompt inspection."""
import json
from datetime import datetime
from typing import Any, Dict

from config import RUNTIME_DIR


ADMIN_DIR = RUNTIME_DIR / "admin"
LOG_FILES = {
    "A": ADMIN_DIR / "A_recall.log",
    "B": ADMIN_DIR / "B_dialog.log",
    "C": ADMIN_DIR / "C_cot.log",
}


def log_admin(channel: str, payload: Dict[str, Any]) -> None:
    """Write one JSONL record to the requested admin log."""
    path = LOG_FILES.get(channel)
    if path is None:
        raise ValueError(f"unknown admin log channel: {channel}")

    try:
        ADMIN_DIR.mkdir(parents=True, exist_ok=True)
        record = {
            "logged_at": datetime.now().isoformat(),
            **payload,
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"[AdminLog] Failed to write {channel} log: {exc}")
