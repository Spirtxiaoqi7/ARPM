"""Run one isolated LOCOMO realtime-memory action in a short-lived process."""
from __future__ import annotations

import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

from model_index import append_run_chat_atom, search_run_chat_history


def main() -> int:
    payload = json.loads(sys.stdin.read())
    action = payload["action"]
    model_name = payload["embedding_model"]
    run_id = payload["run_id"]
    session_id = payload["session_id"]
    logs = StringIO()
    with redirect_stdout(logs), redirect_stderr(logs):
        if action == "search":
            results = search_run_chat_history(
                model_name,
                run_id,
                query=payload["query"],
                session_id=session_id,
                k=int(payload.get("k", 10) or 10),
            )
            output = {"results": results}
        elif action == "add":
            chunk = append_run_chat_atom(model_name, run_id, session_id, payload["atom"])
            output = {"chunk": chunk}
        else:
            raise ValueError(f"Unknown action: {action}")
    sys.stdout.write(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
