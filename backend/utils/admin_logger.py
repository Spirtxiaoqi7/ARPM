"""Append-only experiment logs for prompt inspection."""
import json
import uuid
from datetime import datetime
from typing import Any, Dict

from config import RUNTIME_DIR


ADMIN_DIR = RUNTIME_DIR / "admin"
SCHEMA_VERSION = "2.0"
LOG_FILES = {
    "A": ADMIN_DIR / "A_recall.log",
    "B": ADMIN_DIR / "B_dialog.log",
    "C": ADMIN_DIR / "C_cot.log",
}


def get_owner_context() -> Dict[str, str]:
    """Return log resource ownership context.

    Field meanings:
    - owner_scope / 资源归属范围: current local runtime, future values may be user/team/org.
    - owner_id / 资源归属 ID: current default local owner, future value can be current_user.id.
    """
    return {
        "owner_scope": "local",
        "owner_id": "default",
    }


def build_trace_id(session_id: Any = None, round_num: Any = None, model: Any = None) -> str:
    """Build a trace id / 链路追踪 ID for one answer round."""
    safe_session = str(session_id or "unknown_session")
    safe_round = f"round_{round_num}" if round_num not in (None, "") else "round_unknown"
    safe_model = str(model or "unknown_model")
    return f"{safe_session}::{safe_round}::{safe_model}"


def _display_title(session_name: Any = None, session_label: Any = None, session_id: Any = None) -> str:
    name = str(session_name or "").strip()
    label = str(session_label or "").strip()
    if name and label and name == label:
        return name
    if name and label:
        return f"{name}（{label}）"
    return name or label or str(session_id or "")


def enrich_admin_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Append v2 audit fields while preserving all original payload fields.

    New fields:
    - schema_version / 日志结构版本号
    - event_id / 单条日志事件 ID
    - trace_id / 链路追踪 ID
    - owner_scope / 资源归属范围
    - owner_id / 资源归属 ID
    - session_name / 会话主名称
    - session_label / 会话显示标签
    - display_title / 前端展示标题
    - theme / 当前视觉主题: chat or research
    """
    payload = dict(payload or {})
    owner_context = get_owner_context()
    round_num = payload.get("round", payload.get("current_round"))
    theme = payload.get("theme") if payload.get("theme") in {"chat", "research"} else "chat"
    session_name = payload.get("session_name") or ""
    session_label = payload.get("session_label") or ""
    session_id = payload.get("session_id")

    # Start from the original payload so all legacy fields keep their names and
    # meanings, then append/normalize v2 fields in one backend-controlled place.
    enriched = dict(payload)
    enriched.update({
        "logged_at": datetime.now().isoformat(),
        "schema_version": SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "trace_id": build_trace_id(session_id, round_num, payload.get("model")),
        "owner_scope": owner_context["owner_scope"],
        "owner_id": owner_context["owner_id"],
        "session_name": session_name,
        "session_label": session_label,
        "display_title": payload.get("display_title") or _display_title(session_name, session_label, session_id),
        "theme": theme,
    })
    return enriched


def log_admin(channel: str, payload: Dict[str, Any]) -> None:
    """Write one JSONL record to the requested admin log."""
    path = LOG_FILES.get(channel)
    if path is None:
        raise ValueError(f"unknown admin log channel: {channel}")

    try:
        ADMIN_DIR.mkdir(parents=True, exist_ok=True)
        record = enrich_admin_record(payload)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"[AdminLog] Failed to write {channel} log: {exc}")
