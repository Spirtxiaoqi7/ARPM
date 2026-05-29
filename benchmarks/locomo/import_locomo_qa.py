"""Import LOCOMO QA data into ARPM chat-memory indexes.

LOCOMO QA evidence is annotated by dialog id, so the benchmark importer keeps
one official dialog turn as one ARPM chat chunk. This preserves exact
evidence-to-retrieval alignment for Recall@k and error analysis.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import MEMORY_DB_PATH, MODEL_PATH, RUNTIME_DIR, VECTOR_DB_PATH  # noqa: E402


def _is_ascii_path(path: str) -> bool:
    try:
        os.fspath(path).encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _safe_faiss_write_index(index: faiss.Index, index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    path_text = str(index_path)
    if _is_ascii_path(path_text):
        faiss.write_index(index, path_text)
        return

    tmp_path = Path(tempfile.gettempdir()) / f"arpm_locomo_faiss_{uuid.uuid4().hex}.index"
    try:
        faiss.write_index(index, str(tmp_path))
        shutil.copyfile(tmp_path, index_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _safe_id(value: Any, fallback: str) -> str:
    raw = str(value or fallback).strip()
    raw = re.sub(r"[^0-9A-Za-z_.-]+", "_", raw)
    return raw.strip("._-") or fallback


def _parse_locomo_time(value: str) -> str:
    """Convert LOCOMO time text to ISO when possible, preserving order."""
    value = (value or "").strip()
    if not value:
        return ""

    normalized = re.sub(r"\b(am|pm)\b", lambda m: m.group(1).upper(), value)
    for fmt in ("%I:%M %p on %d %B, %Y", "%I:%M %p on %d %b, %Y"):
        try:
            return datetime.strptime(normalized, fmt).isoformat()
        except ValueError:
            pass
    return value


def _session_numbers(conversation: Dict[str, Any]) -> List[int]:
    numbers = []
    for key in conversation:
        match = re.fullmatch(r"session_(\d+)", key)
        if match:
            numbers.append(int(match.group(1)))
    return sorted(numbers)


def _iter_turns(sample: Dict[str, Any], sample_index: int) -> Iterable[Tuple[int, str, Dict[str, Any], int]]:
    conversation = sample.get("conversation", {})
    round_num = 0
    for session_num in _session_numbers(conversation):
        session_key = f"session_{session_num}"
        time_key = f"session_{session_num}_date_time"
        session_time_raw = conversation.get(time_key, "")
        session_time_iso = _parse_locomo_time(session_time_raw)
        for turn in conversation.get(session_key, []) or []:
            round_num += 1
            yield session_num, session_time_iso, {
                **turn,
                "session_time_raw": session_time_raw,
            }, round_num


def _build_chunk(
    sample: Dict[str, Any],
    sample_index: int,
    session_id: str,
    session_num: int,
    session_time_iso: str,
    turn: Dict[str, Any],
    round_num: int,
) -> Dict[str, Any]:
    sample_id = str(sample.get("sample_id", f"sample_{sample_index}"))
    dia_id = str(turn.get("dia_id", f"turn_{round_num}"))
    speaker = str(turn.get("speaker", "unknown"))
    text_raw = str(turn.get("text", ""))
    session_time_raw = str(turn.get("session_time_raw", ""))
    chunk_id = _safe_id(f"{sample_id}_{dia_id}", f"{session_id}_{round_num}")
    speaker_a = sample.get("conversation", {}).get("speaker_a", "")
    speaker_b = sample.get("conversation", {}).get("speaker_b", "")

    indexed_text = (
        f"[LOCOMO sample={sample_id} session={session_num} "
        f"time={session_time_raw or session_time_iso} round={round_num} "
        f"speaker={speaker} dia_id={dia_id}]\n"
        f"{speaker}: {text_raw}"
    )

    return {
        "chunk_id": chunk_id,
        "text": indexed_text,
        "user_name": speaker_a or "speaker_a",
        "character_name": speaker_b or "speaker_b",
        "user_input": text_raw if speaker == speaker_a else "",
        "assistant_reply": text_raw if speaker == speaker_b else "",
        "session_id": session_id,
        "timestamp": {
            "round_num": round_num,
            "physical_time": session_time_iso,
        },
        "source_type": "chat",
        "benchmark": "locomo",
        "sample_id": sample_id,
        "session_num": session_num,
        "session_time_raw": session_time_raw,
        "speaker": speaker,
        "dia_id": dia_id,
        "text_raw": text_raw,
    }


def _build_message(chunk: Dict[str, Any], speaker_a: str, speaker_b: str) -> Dict[str, Any]:
    speaker = chunk["speaker"]
    if speaker == speaker_a:
        role = "user"
    elif speaker == speaker_b:
        role = "assistant"
    else:
        role = "user"
    return {
        "role": role,
        "content": chunk["text_raw"],
        "speaker": speaker,
        "dia_id": chunk["dia_id"],
        "round": chunk["timestamp"]["round_num"],
        "session_num": chunk["session_num"],
        "timestamp": chunk["timestamp"]["physical_time"],
    }


def _write_session_memory(session_id: str, sample: Dict[str, Any], chunks: List[Dict[str, Any]]) -> None:
    conversation = sample.get("conversation", {})
    speaker_a = conversation.get("speaker_a", "")
    speaker_b = conversation.get("speaker_b", "")
    data = {
        "session_id": session_id,
        "session_name": f"LOCOMO {sample.get('sample_id', session_id)}",
        "created_at": datetime.now().isoformat(),
        "last_round": len(chunks),
        "current_scene_id": None,
        "messages": [_build_message(chunk, speaker_a, speaker_b) for chunk in chunks],
        "memories": [],
        "benchmark": "locomo",
        "locomo_sample_id": sample.get("sample_id"),
        "locomo_speaker_a": speaker_a,
        "locomo_speaker_b": speaker_b,
        "locomo_qa": sample.get("qa", []),
    }
    MEMORY_DB_PATH.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_DB_PATH / f"session_{session_id}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _write_chat_index(session_id: str, chunks: List[Dict[str, Any]], model: SentenceTransformer, batch_size: int) -> int:
    session_dir = VECTOR_DB_PATH / "chat" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    texts = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
    embeddings = np.asarray(embeddings, dtype="float32")
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    with open(session_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    _safe_faiss_write_index(index, session_dir / "faiss.index")
    return int(index.ntotal)


def _export_qa_jsonl(samples: List[Dict[str, Any]], output_path: Path) -> int:
    count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for i, sample in enumerate(samples):
            sample_id = str(sample.get("sample_id", f"sample_{i}"))
            session_id = f"locomo_{_safe_id(sample_id, f'sample_{i}')}"
            for q_idx, qa in enumerate(sample.get("qa", []) or []):
                record = {
                    "qa_id": f"{session_id}_q{q_idx:03d}",
                    "sample_id": sample_id,
                    "session_id": session_id,
                    "question": qa.get("question", ""),
                    "gold_answer": qa.get("answer", ""),
                    "category": qa.get("category", ""),
                    "gold_evidence": qa.get("evidence", []),
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
    return count


def import_locomo(data_path: Path, batch_size: int) -> Dict[str, Any]:
    if not data_path.exists():
        raise FileNotFoundError(data_path)
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Embedding model not found: {MODEL_PATH}")

    with open(data_path, "r", encoding="utf-8") as f:
        samples = json.load(f)
    if not isinstance(samples, list):
        raise ValueError("LOCOMO file must contain a list of samples")

    model = SentenceTransformer(str(MODEL_PATH))
    imported_sessions = []
    total_chunks = 0
    total_vectors = 0

    (VECTOR_DB_PATH / "chat").mkdir(parents=True, exist_ok=True)
    MEMORY_DB_PATH.mkdir(parents=True, exist_ok=True)

    for i, sample in enumerate(samples):
        sample_id = str(sample.get("sample_id", f"sample_{i}"))
        session_id = f"locomo_{_safe_id(sample_id, f'sample_{i}')}"
        chunks = [
            _build_chunk(sample, i, session_id, session_num, session_time_iso, turn, round_num)
            for session_num, session_time_iso, turn, round_num in _iter_turns(sample, i)
        ]
        if not chunks:
            continue

        vector_count = _write_chat_index(session_id, chunks, model, batch_size=batch_size)
        _write_session_memory(session_id, sample, chunks)
        imported_sessions.append({
            "session_id": session_id,
            "sample_id": sample_id,
            "chunks": len(chunks),
            "vectors": vector_count,
            "qa": len(sample.get("qa", []) or []),
        })
        total_chunks += len(chunks)
        total_vectors += vector_count
        print(f"[LOCOMO] Imported {session_id}: chunks={len(chunks)}, vectors={vector_count}")

    qa_path = PROJECT_ROOT / "benchmarks" / "locomo" / "data" / "locomo_qa.jsonl"
    qa_count = _export_qa_jsonl(samples, qa_path)
    manifest = {
        "benchmark": "locomo",
        "data_path": str(data_path),
        "qa_jsonl": str(qa_path),
        "model_path": str(MODEL_PATH),
        "runtime_dir": str(RUNTIME_DIR),
        "split": "one official dialogue turn per chat chunk; chunk_id keeps dia_id",
        "sessions": imported_sessions,
        "total_sessions": len(imported_sessions),
        "total_chunks": total_chunks,
        "total_vectors": total_vectors,
        "total_qa": qa_count,
        "imported_at": datetime.now().isoformat(),
    }
    manifest_path = PROJECT_ROOT / "benchmarks" / "locomo" / "data" / "import_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    with open(RUNTIME_DIR / "locomo_import_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        type=Path,
        default=PROJECT_ROOT / "benchmarks" / "locomo" / "data" / "locomo10.json",
    )
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    manifest = import_locomo(args.data, batch_size=args.batch_size)
    print(json.dumps({
        "total_sessions": manifest["total_sessions"],
        "total_chunks": manifest["total_chunks"],
        "total_vectors": manifest["total_vectors"],
        "total_qa": manifest["total_qa"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
