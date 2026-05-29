"""LOCOMO per-embedding-model isolated vector indexes."""
from __future__ import annotations

import json
import gc
import os
import re
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


LOCOMO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = LOCOMO_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
WORKSPACE_ROOT = PROJECT_ROOT.parents[1]
MODEL_ROOT = WORKSPACE_ROOT / "assets" / "models"
REGISTRY_PATH = MODEL_ROOT / "embedding_models.json"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import RUNTIME_DIR, VECTOR_DB_PATH  # noqa: E402


INDEX_ROOT = RUNTIME_DIR / "locomo_vector_db"
RUN_INDEX_ROOT = RUNTIME_DIR / "locomo_runs"
_MODEL_CACHE: Dict[str, SentenceTransformer] = {}
_INDEX_CACHE: Dict[str, faiss.Index] = {}
_CHUNK_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def model_slug(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z_.-]+", "_", name).strip("._-")


def load_registry() -> Dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {"models": []}
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def available_models() -> List[Dict[str, Any]]:
    models = []
    for item in load_registry().get("models", []):
        name = item.get("name", "")
        slug = model_slug(name)
        index_dir = INDEX_ROOT / slug / "chat"
        models.append({
            **item,
            "slug": slug,
            "index_root": str(INDEX_ROOT / slug),
            "index_exists": index_dir.exists() and any(index_dir.glob("*/faiss.index")),
        })
    return models


def get_model_info(name: str) -> Dict[str, Any]:
    for item in load_registry().get("models", []):
        if item.get("name") == name or item.get("repo_id") == name or model_slug(item.get("name", "")) == name:
            return item
    raise KeyError(f"Unknown embedding model: {name}")


def _is_ascii_path(path: str) -> bool:
    try:
        os.fspath(path).encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _faiss_write_index(index: faiss.Index, index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    path_text = str(index_path)
    if _is_ascii_path(path_text):
        faiss.write_index(index, path_text)
        return
    tmp = Path(tempfile.gettempdir()) / f"locomo_faiss_{uuid.uuid4().hex}.index"
    try:
        faiss.write_index(index, str(tmp))
        shutil.copyfile(tmp, index_path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _faiss_read_index(index_path: Path) -> faiss.Index:
    path_text = str(index_path)
    if _is_ascii_path(path_text):
        return faiss.read_index(path_text)
    tmp = Path(tempfile.gettempdir()) / f"locomo_faiss_{uuid.uuid4().hex}.index"
    try:
        shutil.copyfile(index_path, tmp)
        return faiss.read_index(str(tmp))
    finally:
        if tmp.exists():
            tmp.unlink()


def _load_model(model_name: str) -> SentenceTransformer:
    if model_name not in _MODEL_CACHE:
        if _MODEL_CACHE:
            _MODEL_CACHE.clear()
            gc.collect()
        info = get_model_info(model_name)
        _MODEL_CACHE[model_name] = SentenceTransformer(info["local_dir"])
    return _MODEL_CACHE[model_name]


def _default_session_dirs() -> List[Path]:
    chat_root = VECTOR_DB_PATH / "chat"
    if not chat_root.exists():
        return []
    return sorted([p for p in chat_root.iterdir() if p.is_dir() and p.name.startswith("locomo_")])


def build_indexes(model_name: str, batch_size: int = 64) -> Dict[str, Any]:
    info = get_model_info(model_name)
    slug = model_slug(info["name"])
    target_root = INDEX_ROOT / slug / "chat"
    model = _load_model(info["name"])
    sessions = []
    for session_dir in _default_session_dirs():
        meta_path = session_dir / "metadata.json"
        if not meta_path.exists():
            continue
        chunks = json.loads(meta_path.read_text(encoding="utf-8"))
        texts = [chunk.get("text", "") for chunk in chunks]
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
        )
        embeddings = np.asarray(embeddings, dtype="float32")
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        out_dir = target_root / session_dir.name
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "metadata.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
        _faiss_write_index(index, out_dir / "faiss.index")
        sessions.append({"session_id": session_dir.name, "chunks": len(chunks), "vectors": int(index.ntotal)})
        print(f"[index] {info['name']} {session_dir.name}: {index.ntotal}")

    manifest = {
        "model": info,
        "slug": slug,
        "index_root": str(INDEX_ROOT / slug),
        "sessions": sessions,
        "total_sessions": len(sessions),
        "total_vectors": sum(item["vectors"] for item in sessions),
    }
    (INDEX_ROOT / slug).mkdir(parents=True, exist_ok=True)
    (INDEX_ROOT / slug / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _load_session_index(model_name: str, session_id: str) -> tuple[faiss.Index, List[Dict[str, Any]]]:
    info = get_model_info(model_name)
    slug = model_slug(info["name"])
    key = f"{slug}/{session_id}"
    if key not in _INDEX_CACHE:
        session_dir = INDEX_ROOT / slug / "chat" / session_id
        index_path = session_dir / "faiss.index"
        meta_path = session_dir / "metadata.json"
        if not index_path.exists() or not meta_path.exists():
            raise FileNotFoundError(f"Index not built for {info['name']} / {session_id}")
        _INDEX_CACHE[key] = _faiss_read_index(index_path)
        _CHUNK_CACHE[key] = json.loads(meta_path.read_text(encoding="utf-8"))
    return _INDEX_CACHE[key], _CHUNK_CACHE[key]


def _run_session_dir(model_name: str, run_id: str, session_id: str) -> Path:
    info = get_model_info(model_name)
    return RUN_INDEX_ROOT / model_slug(run_id) / model_slug(info["name"]) / "chat" / session_id


def _load_run_session_index(model_name: str, run_id: str, session_id: str) -> tuple[faiss.Index, List[Dict[str, Any]]]:
    info = get_model_info(model_name)
    slug = model_slug(info["name"])
    safe_run_id = model_slug(run_id)
    key = f"run/{safe_run_id}/{slug}/{session_id}"
    if key not in _INDEX_CACHE:
        session_dir = _run_session_dir(info["name"], safe_run_id, session_id)
        index_path = session_dir / "faiss.index"
        meta_path = session_dir / "metadata.json"
        model = _load_model(info["name"])
        if index_path.exists() and meta_path.exists():
            _INDEX_CACHE[key] = _faiss_read_index(index_path)
            _CHUNK_CACHE[key] = json.loads(meta_path.read_text(encoding="utf-8"))
        else:
            dim = int(model.get_sentence_embedding_dimension())
            _INDEX_CACHE[key] = faiss.IndexFlatIP(dim)
            _CHUNK_CACHE[key] = []
    return _INDEX_CACHE[key], _CHUNK_CACHE[key]


def append_run_chat_atom(model_name: str, run_id: str, session_id: str, atom: Dict[str, Any]) -> Dict[str, Any]:
    info = get_model_info(model_name)
    model = _load_model(info["name"])
    index, chunks = _load_run_session_index(info["name"], run_id, session_id)
    text = str(atom.get("text") or "")
    if not text.strip():
        raise ValueError("empty realtime chat atom")
    embedding = model.encode([text], normalize_embeddings=True)
    index.add(np.asarray(embedding, dtype="float32"))
    chunk = {
        "chunk_id": atom.get("chunk_id") or str(uuid.uuid4())[:8],
        "dia_id": atom.get("dia_id") or f"RUN:{len(chunks) + 1}",
        "text": text,
        "text_raw": text,
        "user_name": atom.get("user_name", "LOCOMO_QA"),
        "character_name": atom.get("character_name", atom.get("model", "AI")),
        "user_input": atom.get("user_input", ""),
        "assistant_reply": atom.get("assistant_reply", ""),
        "session_id": session_id,
        "run_id": model_slug(run_id),
        "timestamp": atom.get("timestamp", {}),
        "source_type": "locomo_realtime_chat",
        "embedding_model": info["name"],
    }
    chunks.append(chunk)
    out_dir = _run_session_dir(info["name"], run_id, session_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metadata.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    _faiss_write_index(index, out_dir / "faiss.index")
    return chunk


def search_chat_history(model_name: str, query: str, session_id: str, k: int = 20) -> List[Dict[str, Any]]:
    info = get_model_info(model_name)
    model = _load_model(info["name"])
    index, chunks = _load_session_index(info["name"], session_id)
    if index.ntotal == 0:
        return []
    query_vec = model.encode([query], normalize_embeddings=True)
    search_k = min(max(k * 2, k), index.ntotal)
    scores, indices = index.search(np.asarray(query_vec, dtype="float32"), search_k)
    results: List[Dict[str, Any]] = []
    for idx, score in zip(indices[0], scores[0]):
        if idx == -1 or idx >= len(chunks):
            continue
        chunk = dict(chunks[idx])
        raw = float(score)
        chunk["raw_score"] = raw
        chunk["semantic_score"] = max(0.0, min(1.0, raw))
        chunk["score"] = chunk["semantic_score"]
        chunk["embedding_model"] = info["name"]
        results.append(chunk)
        if len(results) >= k:
            break
    return results


def search_run_chat_history(model_name: str, run_id: str, query: str, session_id: str, k: int = 10) -> List[Dict[str, Any]]:
    info = get_model_info(model_name)
    model = _load_model(info["name"])
    index, chunks = _load_run_session_index(info["name"], run_id, session_id)
    if index.ntotal == 0:
        return []
    query_vec = model.encode([query], normalize_embeddings=True)
    search_k = min(max(k * 2, k), index.ntotal)
    scores, indices = index.search(np.asarray(query_vec, dtype="float32"), search_k)
    results: List[Dict[str, Any]] = []
    for idx, score in zip(indices[0], scores[0]):
        if idx == -1 or idx >= len(chunks):
            continue
        chunk = dict(chunks[idx])
        raw = float(score)
        chunk["raw_score"] = raw
        chunk["semantic_score"] = max(0.0, min(1.0, raw))
        chunk["score"] = chunk["semantic_score"]
        chunk["embedding_model"] = info["name"]
        chunk["retrieval_source"] = "realtime_vector"
        results.append(chunk)
        if len(results) >= k:
            break
    return results
