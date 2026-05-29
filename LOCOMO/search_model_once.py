"""Run one isolated LOCOMO vector search in a short-lived process."""
from __future__ import annotations

import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

from model_index import search_chat_history


def main() -> int:
    payload = json.loads(sys.stdin.read())
    model_name = payload["embedding_model"]
    query = payload["query"]
    session_id = payload["session_id"]
    k = int(payload.get("k", 20) or 20)
    logs = StringIO()
    with redirect_stdout(logs), redirect_stderr(logs):
        results = search_chat_history(model_name, query, session_id=session_id, k=k)
    sys.stdout.write(json.dumps({"results": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
