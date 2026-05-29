"""LOCOMO visual QA console for ARPM-v4.

Run from project root:
    python LOCOMO/web_app.py

Open:
    http://127.0.0.1:5050
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import math

from flask import Flask, jsonify, request, send_file, send_from_directory


LOCOMO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = LOCOMO_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
DATA_DIR = LOCOMO_DIR / "data"
RESULTS_DIR = LOCOMO_DIR / "results"
LOG_DIR = LOCOMO_DIR / "log"
WEB_DIR = LOCOMO_DIR / "web"
SETTINGS_PATH = RESULTS_DIR / "web_settings.json"
CHECKPOINT_JSON = RESULTS_DIR / "web_checkpoint.json"
CHECKPOINT_CSV = RESULTS_DIR / "web_checkpoint.csv"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(LOCOMO_DIR) not in sys.path:
    sys.path.insert(0, str(LOCOMO_DIR))

from metrics import exact_match, mrr, recall_at_k, summarize, token_f1  # noqa: E402
from model_index import (  # noqa: E402
    append_run_chat_atom,
    available_models,
    search_chat_history as search_isolated_chat_history,
    search_run_chat_history,
)
from prompts import build_prompt  # noqa: E402
from utils.bm25_plus import BM25PlusScorer  # noqa: E402


app = Flask(__name__, static_folder=None)
JOBS: Dict[str, Dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()
RUN_LOCK = threading.Lock()
BM25_CACHE: Dict[str, Tuple[BM25PlusScorer, List[Dict[str, Any]]]] = {}


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_qas() -> List[Dict[str, Any]]:
    return list(read_jsonl(DATA_DIR / "locomo_qa.jsonl"))


def load_manifest() -> Dict[str, Any]:
    path = DATA_DIR / "import_manifest.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"sessions": []}


def _memory_path(session_id: str) -> Optional[Path]:
    from config import MEMORY_DB_PATH

    path = MEMORY_DB_PATH / f"session_{session_id}.json"
    return path if path.exists() else None


def _load_memory(session_id: str) -> Dict[str, Any]:
    path = _memory_path(session_id)
    if not path:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _chat_chunks(session_id: str) -> List[Dict[str, Any]]:
    from config import VECTOR_DB_PATH

    path = VECTOR_DB_PATH / "chat" / session_id / "metadata.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _current_round(session_id: str) -> int:
    chunks = _chat_chunks(session_id)
    if not chunks:
        return 1
    return max(int((chunk.get("timestamp") or {}).get("round_num", 0) or 0) for chunk in chunks) + 1


def _qa_subset(session_ids: List[str], limit_per_session: int) -> List[Dict[str, Any]]:
    selected = set(session_ids)
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for qa in load_qas():
        if selected and qa.get("session_id") not in selected:
            continue
        grouped.setdefault(qa["session_id"], []).append(qa)

    result: List[Dict[str, Any]] = []
    for session_id in sorted(grouped):
        qas = grouped[session_id]
        if limit_per_session > 0:
            qas = qas[:limit_per_session]
        result.extend(qas)
    return result


def _annotate_weight(
    chunk: Dict[str, Any],
    method: str,
    current_round: int,
    decay_round: float,
    decay_hours: float,
    rank: int,
    gold: Optional[List[str]] = None,
    time_decay_enabled: bool = False,
    round_decay_enabled: bool = False,
) -> Dict[str, Any]:
    item = dict(chunk)
    ts = item.get("timestamp") or {}
    chunk_round = int(ts.get("round_num", 0) or 0)
    delta_round = abs(current_round - chunk_round) if chunk_round else 0
    physical_time = ts.get("physical_time", "")
    hours_delta = 0.0
    if physical_time:
        try:
            dt = datetime.fromisoformat(str(physical_time).replace("Z", "+00:00"))
            hours_delta = max(0.0, (datetime.now() - dt).total_seconds() / 3600)
        except Exception:
            hours_delta = 0.0
    round_weight = math.exp(-delta_round / decay_round) if round_decay_enabled and decay_round > 0 else 1.0
    time_weight = math.exp(-hours_delta / decay_hours) if time_decay_enabled and decay_hours > 0 else 1.0
    temporal_weight = float(item.get("temporal_weight", round_weight * time_weight))
    base_score = float(item.get("score", 0.0) or 0.0)
    weighted_score = float(item.get("weighted_score", base_score if method != "ordinary_recent" else item.get("weighted_score", base_score)) or 0.0)
    if method in {"arpm_full", "arpm_temporal", "arpm_hybrid_rrf"} and "weighted_score" not in item:
        weighted_score = base_score * temporal_weight
    scene_factor = float(item.get("scene_factor", 1.0) or 1.0)
    gold_set = set(gold or [])
    dia_id = str(item.get("dia_id", ""))
    item["weight_trace"] = {
        "method": method,
        "rank": rank,
        "embedding_model": item.get("embedding_model", ""),
        "base_score": base_score,
        "raw_score": float(item.get("raw_score", base_score) or 0.0),
        "semantic_score": float(item.get("semantic_score", base_score) or 0.0),
        "current_round": current_round,
        "chunk_round": chunk_round,
        "delta_round": delta_round,
        "decay_rate_round": decay_round,
        "round_weight": round_weight,
        "round_decay_enabled": round_decay_enabled,
        "physical_time": physical_time,
        "hours_delta": hours_delta,
        "decay_rate_hours": decay_hours,
        "time_weight": time_weight,
        "time_decay_enabled": time_decay_enabled,
        "temporal_weight": temporal_weight,
        "scene_factor": scene_factor,
        "weighted_score": weighted_score,
        "formula": "weighted_score = base_score * temporal_weight * scene_factor" if method in {"arpm_full", "arpm_temporal", "arpm_hybrid_rrf"} else "weighted_score = base_score",
        "is_gold_evidence": dia_id in gold_set,
    }
    item["weighted_score"] = weighted_score
    return item


def _retrieved_recent(session_id: str, k: int, gold: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    chunks = sorted(
        _chat_chunks(session_id),
        key=lambda item: int((item.get("timestamp") or {}).get("round_num", 0) or 0),
        reverse=True,
    )
    recent = chunks[:k]
    for rank, chunk in enumerate(recent, start=1):
        chunk["score"] = 1.0 / rank
        chunk["weighted_score"] = chunk["score"]
    current_round = _current_round(session_id)
    return [_annotate_weight(chunk, "ordinary_recent", current_round, 1.0, 1.0, rank, gold=gold) for rank, chunk in enumerate(recent, 1)]


def _search_embedding_model(embedding_model: str, question: str, session_id: str, k: int) -> List[Dict[str, Any]]:
    return search_isolated_chat_history(embedding_model, question, session_id=session_id, k=k)


def _search_realtime_chat(embedding_model: str, run_id: str, question: str, session_id: str, k: int) -> List[Dict[str, Any]]:
    return search_run_chat_history(embedding_model, run_id, question, session_id=session_id, k=k)


def _append_realtime_chat(
    embedding_model: str,
    run_id: str,
    session_id: str,
    question: str,
    answer: str,
    model_name: str,
    run_turn: int,
) -> Dict[str, Any]:
    physical_time = datetime.now().isoformat()
    atom = {
        "dia_id": f"RUN:{run_turn}",
        "text": f"LOCOMO_QA: {question}\n{model_name or 'AI'}: {answer}",
        "user_name": "LOCOMO_QA",
        "character_name": model_name or "AI",
        "user_input": question,
        "assistant_reply": answer,
        "model": model_name or "AI",
        "timestamp": {"round_num": run_turn, "physical_time": physical_time},
    }
    return append_run_chat_atom(embedding_model, run_id, session_id, atom)


def _bm25_index(session_id: str) -> Tuple[BM25PlusScorer, List[Dict[str, Any]]]:
    if session_id not in BM25_CACHE:
        chunks = _chat_chunks(session_id)
        scorer = BM25PlusScorer()
        scorer.index_documents([str(chunk.get("text_raw") or chunk.get("text") or "") for chunk in chunks])
        BM25_CACHE[session_id] = (scorer, chunks)
    return BM25_CACHE[session_id]


def _search_bm25(question: str, session_id: str, k: int) -> List[Dict[str, Any]]:
    scorer, chunks = _bm25_index(session_id)
    raw_results = scorer.search(question, top_k=max(k * 3, k))
    if not raw_results:
        return []
    max_score = max(float(item.get("score", 0.0) or 0.0) for item in raw_results) or 1.0
    results: List[Dict[str, Any]] = []
    seen = set()
    for item in raw_results:
        idx = int(item["index"])
        if idx < 0 or idx >= len(chunks):
            continue
        chunk = dict(chunks[idx])
        dia_id = str(chunk.get("dia_id", ""))
        if dia_id in seen:
            continue
        score = float(item.get("score", 0.0) or 0.0)
        chunk["bm25_score"] = score
        chunk["score"] = score / max_score
        chunk["retrieval_source"] = "bm25"
        results.append(chunk)
        seen.add(dia_id)
        if len(results) >= k:
            break
    return results


def _rrf_fuse(vector_results: List[Dict[str, Any]], bm25_results: List[Dict[str, Any]], k: int, rrf_k: int = 60) -> List[Dict[str, Any]]:
    fused: Dict[str, Dict[str, Any]] = {}

    def add(items: List[Dict[str, Any]], source: str) -> None:
        for rank, item in enumerate(items, start=1):
            dia_id = str(item.get("dia_id", ""))
            if not dia_id:
                continue
            entry = fused.setdefault(dia_id, dict(item))
            entry.setdefault("retrieval_sources", [])
            if source not in entry["retrieval_sources"]:
                entry["retrieval_sources"].append(source)
            entry[f"{source}_rank"] = rank
            entry[f"{source}_score"] = float(item.get("score", 0.0) or 0.0)
            entry["rrf_score"] = float(entry.get("rrf_score", 0.0) or 0.0) + 1.0 / (rrf_k + rank)

    add(vector_results, "vector")
    add(bm25_results, "bm25")
    results = sorted(fused.values(), key=lambda item: float(item.get("rrf_score", 0.0) or 0.0), reverse=True)
    max_score = float(results[0].get("rrf_score", 1.0) or 1.0) if results else 1.0
    for item in results:
        item["score"] = float(item.get("rrf_score", 0.0) or 0.0) / max_score
        item["retrieval_source"] = "+".join(item.get("retrieval_sources", [])) or "rrf"
    return results[:k]


def _apply_locomo_weights(
    results: List[Dict[str, Any]],
    current_round: int,
    decay_round: float,
    decay_hours: float,
    time_decay_enabled: bool,
    round_decay_enabled: bool,
) -> List[Dict[str, Any]]:
    weighted = []
    for item in results:
        chunk = dict(item)
        ts = chunk.get("timestamp") or {}
        chunk_round = int(ts.get("round_num", 0) or 0)
        delta_round = abs(current_round - chunk_round) if chunk_round else 0
        physical_time = ts.get("physical_time", "")
        hours_delta = 0.0
        if physical_time:
            try:
                dt = datetime.fromisoformat(str(physical_time).replace("Z", "+00:00"))
                hours_delta = max(0.0, (datetime.now() - dt).total_seconds() / 3600)
            except Exception:
                hours_delta = 0.0
        round_weight = math.exp(-delta_round / decay_round) if round_decay_enabled and decay_round > 0 else 1.0
        time_weight = math.exp(-hours_delta / decay_hours) if time_decay_enabled and decay_hours > 0 else 1.0
        temporal_weight = round_weight * time_weight
        base_score = float(chunk.get("score", 0.0) or 0.0)
        scene_factor = float(chunk.get("scene_factor", 1.0) or 1.0)
        chunk["temporal_weight"] = temporal_weight
        chunk["scene_factor"] = scene_factor
        chunk["weighted_score"] = base_score * temporal_weight * scene_factor
        weighted.append(chunk)
    weighted.sort(key=lambda item: float(item.get("weighted_score", 0.0) or 0.0), reverse=True)
    return weighted


def _retrieve(
    question: str,
    session_id: str,
    method: str,
    k: int,
    decay_round: float,
    decay_hours: float,
    embedding_model: str,
    gold: Optional[List[str]] = None,
    time_decay_enabled: bool = False,
    round_decay_enabled: bool = False,
) -> List[Dict[str, Any]]:
    if method == "ordinary_recent":
        return _retrieved_recent(session_id, k, gold=gold)

    if method == "bm25_only":
        results = _search_bm25(question, session_id, k)
    elif method in {"hybrid_rrf", "arpm_hybrid_rrf"}:
        vector_results = _search_embedding_model(embedding_model, question, session_id, max(k * 2, k))
        bm25_results = _search_bm25(question, session_id, max(k * 2, k))
        results = _rrf_fuse(vector_results, bm25_results, k=max(k * 2, k))
    else:
        results = _search_embedding_model(embedding_model, question, session_id, k)
    current_round = _current_round(session_id)
    if method in {"arpm_full", "arpm_temporal", "arpm_hybrid_rrf"}:
        results = _apply_locomo_weights(
            results,
            current_round=current_round,
            decay_round=decay_round,
            decay_hours=decay_hours,
            time_decay_enabled=time_decay_enabled,
            round_decay_enabled=round_decay_enabled,
        )
    return [
        _annotate_weight(chunk, method, current_round, decay_round, decay_hours, rank, gold=gold, time_decay_enabled=time_decay_enabled, round_decay_enabled=round_decay_enabled)
        for rank, chunk in enumerate(results[:k], 1)
    ]


def _route_label(route: str, chunk: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(chunk)
    item["route"] = route
    return item


def _compact_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
    ts = chunk.get("timestamp") or {}
    return {
        "route": chunk.get("route", ""),
        "dia_id": chunk.get("dia_id", ""),
        "embedding_model": chunk.get("embedding_model", ""),
        "retrieval_source": chunk.get("retrieval_source", ""),
        "retrieval_sources": chunk.get("retrieval_sources", []),
        "bm25_score": float(chunk.get("bm25_score", 0.0) or 0.0),
        "rrf_score": float(chunk.get("rrf_score", 0.0) or 0.0),
        "vector_rank": chunk.get("vector_rank", ""),
        "bm25_rank": chunk.get("bm25_rank", ""),
        "score": float(chunk.get("score", 0.0) or 0.0),
        "weighted_score": float(chunk.get("weighted_score", chunk.get("score", 0.0)) or 0.0),
        "weight_trace": chunk.get("weight_trace", {}),
        "round_num": ts.get("round_num", ""),
        "physical_time": ts.get("physical_time", ""),
        "speaker": chunk.get("speaker", ""),
        "text_raw": chunk.get("text_raw", chunk.get("text", "")),
    }


def _call_llm(prompt: str, api_config: Dict[str, Any]) -> str:
    import openai

    api_key = api_config.get("api_key") or os.environ.get("OPENAI_API_KEY") or os.environ.get("ARPM_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 API key")
    base_url = (api_config.get("base_url") or os.environ.get("OPENAI_BASE_URL") or os.environ.get("ARPM_BASE_URL") or "https://api.deepseek.com").rstrip("/")
    model = api_config.get("model") or os.environ.get("OPENAI_MODEL") or os.environ.get("ARPM_MODEL") or "deepseek-chat"
    temperature = float(api_config.get("temperature", 0.0) or 0.0)
    max_tokens = int(api_config.get("max_tokens", 64) or 64)

    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    request_kwargs = {}
    if "qwen" in model.lower():
        request_kwargs["extra_body"] = {"enable_thinking": False}
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Follow the benchmark prompt exactly. If XML-like tags are requested, include them exactly."},
            {"role": "user", "content": f"/no_think\n{prompt}" if "qwen" in model.lower() else prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        **request_kwargs,
    )
    message = response.choices[0].message
    content = message.content
    if not content:
        content = getattr(message, "reasoning_content", "") or ""
    return content.strip() if content else ""


def _call_llm_with_retry(prompt: str, api_config: Dict[str, Any], expect_tags: bool = False) -> str:
    raw = _call_llm(prompt, api_config)
    if raw and (not expect_tags or _extract_tag(raw, "response")):
        return raw
    retry_prompt = f"""\
The previous answer was empty or did not follow the required format.
Answer again using exactly this format and no extra text:
<analysis>one short evidence summary, or state that evidence is insufficient</analysis>
<response>short factual answer, or I don't know</response>

Original task:
{prompt}
"""
    retry_raw = _call_llm(retry_prompt, api_config)
    return retry_raw or raw


def _test_llm_api(api_config: Dict[str, Any]) -> Dict[str, Any]:
    started = time.time()
    raw = _call_llm("Reply with exactly: OK", {**api_config, "max_tokens": 16, "temperature": 0})
    return {
        "success": True,
        "latency_ms": int((time.time() - started) * 1000),
        "reply": raw[:200],
    }


def _extract_tag(text: str, tag: str) -> str:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text or "", flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_response_answer(raw: str) -> tuple[str, str]:
    analysis = _extract_tag(raw, "analysis")
    response = _extract_tag(raw, "response")
    if response:
        return response, analysis
    cleaned = re.sub(r"<analysis>.*?</analysis>", "", raw or "", flags=re.IGNORECASE | re.DOTALL).strip()
    cleaned = re.sub(r"</?response>", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned, analysis


def _prompt_method(method: str) -> str:
    if method == "ordinary_recent":
        return "plain_rag"
    if method == "pure_rag":
        return "plain_rag"
    if method in {"bm25_only", "hybrid_rrf"}:
        return "plain_rag"
    if method == "arpm_full":
        return "arpm_full"
    if method == "arpm_hybrid_rrf":
        return "arpm_full"
    return "plain_rag"


def _save_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    fieldnames = [
        "QA编号",
        "会话",
        "类别",
        "问题",
        "官方答案",
        "模型答案",
        "模型原始输出",
        "analysis摘要",
        "官方证据",
        "召回dia_id",
        "对话历史dia_id",
        "实时二路run_id",
        "实时写入dia_id",
        "Hit@5",
        "Hit@10",
        "MRR",
        "EM",
        "F1",
        "Top5片段",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            chunks = row.get("retrieved_chunks", [])[:5]
            writer.writerow({
                "QA编号": row.get("qa_id", ""),
                "会话": row.get("session_id", ""),
                "类别": row.get("category", ""),
                "问题": row.get("question", ""),
                "官方答案": row.get("gold_answer", ""),
                "模型答案": row.get("pred_answer", ""),
                "模型原始输出": row.get("raw_pred_answer", ""),
                "analysis摘要": row.get("analysis_answer", ""),
                "官方证据": "; ".join(row.get("gold_evidence", [])),
                "召回dia_id": "; ".join(row.get("retrieved_dia_ids", [])),
                "对话历史dia_id": "; ".join(row.get("chat_history_dia_ids", [])),
                "实时二路run_id": row.get("realtime_run_id", ""),
                "实时写入dia_id": (row.get("written_realtime_chunk") or {}).get("dia_id", ""),
                "Hit@5": "是" if row.get("recall_at_5") else "否",
                "Hit@10": "是" if row.get("recall_at_10") else "否",
                "MRR": row.get("mrr", 0.0),
                "EM": row.get("em", ""),
                "F1": row.get("f1", ""),
                "Top5片段": "\n\n".join(
                    f"{c.get('dia_id')} | round={c.get('round_num')} | {c.get('physical_time')} | {c.get('speaker')}: {c.get('text_raw')}"
                    for c in chunks
                ),
            })


def _safe_result_target(raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("缺少保存路径")
    target = Path(raw_path).expanduser()
    if target.suffix.lower() != ".csv":
        target = target / "locomo_web_latest.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _write_latest(payload: Dict[str, Any]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    write_json(RESULTS_DIR / "web_latest.json", payload)
    _save_csv(RESULTS_DIR / "web_latest.csv", payload.get("rows", []))
    _write_run_log(payload)


def _write_checkpoint(payload: Dict[str, Any]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    write_json(CHECKPOINT_JSON, payload)
    _save_csv(CHECKPOINT_CSV, payload.get("rows", []))


def _same_run_config(saved: Dict[str, Any], current: Dict[str, Any]) -> bool:
    saved_config = saved.get("run_config") or {}
    keys = [
        "mode",
        "method",
        "embedding_model",
        "session_ids",
        "limit_per_session",
        "top_k",
        "decay_rate_round",
        "round_decay_enabled",
        "decay_rate_hours",
        "time_decay_enabled",
        "dual_route_enabled",
        "chat_history_k",
        "realtime_write_enabled",
        "run_id",
        "system_prompt",
    ]
    for key in keys:
        if saved_config.get(key) != current.get(key):
            return False

    saved_api = saved_config.get("api_config") or {}
    current_api = current.get("api_config") or {}
    for key in ("base_url", "model", "temperature", "max_tokens"):
        if saved_api.get(key) != current_api.get(key):
            return False
    return True


def _method_label(method: str) -> str:
    return {
        "ordinary_recent": "普通最近 K 轮",
        "pure_rag": "纯向量 RAG",
        "bm25_only": "BM25-only",
        "hybrid_rrf": "向量+BM25 RRF",
        "arpm_full": "ARPM 向量-only",
        "arpm_hybrid_rrf": "ARPM Hybrid RRF",
    }.get(method, method)


def _resume_rows(data: Dict[str, Any], qas: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
    candidates = [CHECKPOINT_JSON, RESULTS_DIR / "web_latest.json"]
    qa_ids = {str(qa.get("qa_id", "")) for qa in qas}
    best_rows: List[Dict[str, Any]] = []
    best_source = ""
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not _same_run_config(payload, data):
            continue
        rows = []
        seen = set()
        for row in payload.get("rows", []):
            qa_id = str(row.get("qa_id", ""))
            if qa_id in qa_ids and qa_id not in seen:
                rows.append(row)
                seen.add(qa_id)
        if len(rows) > len(best_rows):
            best_rows = rows
            best_source = str(path)
    return best_rows, best_source


def _write_run_log(payload: Dict[str, Any]) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = LOG_DIR / f"locomo_run_{stamp}.json"
    log_payload = {
        "logged_at": datetime.now().isoformat(),
        "source": "LOCOMO web console",
        "note": "Raw run archive. This file may contain prompts, raw model outputs, and local API settings.",
        **payload,
    }
    write_json(path, log_payload)
    return path


def _load_web_settings() -> Dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return {}
    return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))


def _public_job(job: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "created_at": job["created_at"],
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "current": job.get("current", ""),
        "total": job.get("total", 0),
        "done": job.get("done", 0),
        "summary": summarize(job.get("rows", [])),
        "rows": job.get("rows", []),
        "errors": job.get("errors", []),
        "cancel_requested": job.get("cancel_requested", False),
        "resume_source": job.get("resume_source", ""),
    }


def _update_job(job_id: str, **updates: Any) -> None:
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(updates)


def _append_job_row(job_id: str, row: Dict[str, Any]) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        job["rows"].append(row)
        job["done"] = len(job["rows"])


def _append_job_error(job_id: str, error: Dict[str, str]) -> None:
    with JOBS_LOCK:
        JOBS[job_id]["errors"].append(error)


def _is_cancelled(job_id: str) -> bool:
    with JOBS_LOCK:
        return bool(JOBS.get(job_id, {}).get("cancel_requested"))


def _build_row(
    qa: Dict[str, Any],
    mode: str,
    method: str,
    top_k: int,
    decay_round: float,
    decay_hours: float,
    embedding_model: str,
    save_prompts: bool,
    system_prompt: str,
    api_config: Dict[str, Any],
    job_id: Optional[str] = None,
    time_decay_enabled: bool = False,
    round_decay_enabled: bool = False,
    dual_route_enabled: bool = False,
    chat_history_k: int = 10,
    realtime_write_enabled: bool = False,
    run_id: str = "",
    run_turn: int = 0,
) -> Dict[str, Any]:
    gold = [str(item) for item in (qa.get("gold_evidence") or [])]
    retrieved = _retrieve(
        qa["question"],
        qa["session_id"],
        method,
        top_k,
        decay_round,
        decay_hours,
        embedding_model,
        gold=gold,
        time_decay_enabled=time_decay_enabled,
        round_decay_enabled=round_decay_enabled,
    )
    retrieved = [_route_label("locomo_evidence", item) for item in retrieved]
    chat_history = []
    if dual_route_enabled:
        if realtime_write_enabled and run_id:
            chat_history = _search_realtime_chat(embedding_model, run_id, qa["question"], qa["session_id"], chat_history_k)
        else:
            secondary_pool_k = min(30, max(chat_history_k + len(retrieved), chat_history_k))
            chat_pool = _retrieve(
                qa["question"],
                qa["session_id"],
                method,
                secondary_pool_k,
                decay_round,
                decay_hours,
                embedding_model,
                gold=gold,
                time_decay_enabled=time_decay_enabled,
                round_decay_enabled=round_decay_enabled,
            )
            primary_ids = {str(item.get("dia_id", "")) for item in retrieved}
            chat_history = [item for item in chat_pool if str(item.get("dia_id", "")) not in primary_ids][:chat_history_k]
        chat_history = [_route_label("chat_history", item) for item in chat_history]
    retrieved_ids = [str(item.get("dia_id", "")) for item in retrieved]
    chat_history_ids = [str(item.get("dia_id", "")) for item in chat_history]
    compact_chunks = [_compact_chunk(item) for item in retrieved]
    compact_chat_chunks = [_compact_chunk(item) for item in chat_history]
    pred = ""
    raw_pred = ""
    analysis = ""
    prompt = ""
    if mode == "qa":
        prompt = build_prompt(
            _prompt_method(method),
            qa["question"],
            retrieved,
            system_prompt=system_prompt,
            chat_history_chunks=chat_history if dual_route_enabled else None,
        )
        if job_id:
            _update_job(job_id, current=f"等待 API：{qa.get('qa_id', '')}")
        raw_pred = _call_llm_with_retry(prompt, api_config, expect_tags=(method in {"arpm_full", "arpm_hybrid_rrf"}))
        pred, analysis = _extract_response_answer(raw_pred)
    written_realtime_chunk = {}
    if mode == "qa" and dual_route_enabled and realtime_write_enabled and run_id and pred:
        written_realtime_chunk = _append_realtime_chat(
            embedding_model,
            run_id,
            qa["session_id"],
            qa["question"],
            pred,
            str((api_config or {}).get("model") or ""),
            run_turn or 0,
        )
    row = {
        "qa_id": qa.get("qa_id", ""),
        "sample_id": qa.get("sample_id", ""),
        "session_id": qa.get("session_id", ""),
        "category": qa.get("category", ""),
        "question": qa.get("question", ""),
        "gold_answer": qa.get("gold_answer", ""),
        "pred_answer": pred,
        "raw_pred_answer": raw_pred,
        "analysis_answer": analysis,
        "gold_evidence": gold,
        "retrieved_dia_ids": retrieved_ids,
        "chat_history_dia_ids": chat_history_ids,
        "retrieved_chunks": compact_chunks,
        "chat_history_chunks": compact_chat_chunks,
        "realtime_run_id": run_id if realtime_write_enabled else "",
        "written_realtime_chunk": _compact_chunk(written_realtime_chunk) if written_realtime_chunk else {},
        "prompt": prompt if save_prompts else "",
        "prompt_raw": prompt,
        "recall_at_1": recall_at_k(gold, retrieved_ids, 1),
        "recall_at_5": recall_at_k(gold, retrieved_ids, 5),
        "recall_at_10": recall_at_k(gold, retrieved_ids, 10),
        "recall_at_20": recall_at_k(gold, retrieved_ids, 20),
        "mrr": mrr(gold, retrieved_ids),
    }
    if mode == "qa":
        row["em"] = exact_match(pred, qa.get("gold_answer", "")) if pred else 0.0
        row["f1"] = token_f1(pred, qa.get("gold_answer", "")) if pred else 0.0
    return row


def _run_job(job_id: str, data: Dict[str, Any]) -> None:
    mode = data.get("mode", "retrieval")
    method = data.get("method", "pure_rag")
    embedding_model = data.get("embedding_model", "bge-m3")
    session_ids = data.get("session_ids") or []
    top_k = max(1, min(100, int(data.get("top_k", 20) or 20)))
    limit_per_session = int(data.get("limit_per_session", 20) or 20)
    decay_round = float(data.get("decay_rate_round", 20.0) or 20.0)
    decay_hours = float(data.get("decay_rate_hours", 168.0) or 168.0)
    save_prompts = bool(data.get("save_prompts", False))
    system_prompt = data.get("system_prompt", "")
    api_config = data.get("api_config") or {}
    api_delay_seconds = max(0.0, min(30.0, float(data.get("api_delay_seconds", 1.0) or 0.0)))
    resume_run = bool(data.get("resume_run", False))
    time_decay_enabled = bool(data.get("time_decay_enabled", False))
    round_decay_enabled = bool(data.get("round_decay_enabled", False))
    dual_route_enabled = bool(data.get("dual_route_enabled", False))
    chat_history_k = max(1, min(30, int(data.get("chat_history_k", 10) or 10)))
    realtime_write_enabled = bool(data.get("realtime_write_enabled", False))
    run_id = str(data.get("run_id") or job_id)
    data["run_id"] = run_id
    qas = _qa_subset(session_ids, limit_per_session)
    resume_rows, resume_source = _resume_rows(data, qas) if resume_run else ([], "")
    completed_ids = {str(row.get("qa_id", "")) for row in resume_rows}
    pending_qas = [qa for qa in qas if str(qa.get("qa_id", "")) not in completed_ids]

    if not RUN_LOCK.acquire(blocking=False):
        _update_job(job_id, status="failed", current="已有任务正在运行，请等待结束后再开始", finished_at=datetime.now().isoformat())
        return
    with JOBS_LOCK:
        job = JOBS[job_id]
        job["rows"] = list(resume_rows)
        job["done"] = len(resume_rows)
        job["resume_source"] = resume_source
    start_message = f"断点续跑：已载入 {len(resume_rows)} 条，剩余 {len(pending_qas)} 条" if resume_run else "开始运行"
    _update_job(job_id, status="running", started_at=datetime.now().isoformat(), total=len(qas), current=start_message)
    try:
        for index, qa in enumerate(pending_qas, start=len(resume_rows) + 1):
            if _is_cancelled(job_id):
                _update_job(job_id, status="cancelled", current="用户已停止", finished_at=datetime.now().isoformat())
                break
            _update_job(job_id, current=f"{index}/{len(qas)} 检索：{qa.get('qa_id', '')}")
            try:
                row = _build_row(
                    qa,
                    mode=mode,
                    method=method,
                    top_k=top_k,
                    decay_round=decay_round,
                    decay_hours=decay_hours,
                    embedding_model=embedding_model,
                    save_prompts=save_prompts,
                    system_prompt=system_prompt,
                    api_config=api_config,
                    job_id=job_id,
                    time_decay_enabled=time_decay_enabled,
                    round_decay_enabled=round_decay_enabled,
                    dual_route_enabled=dual_route_enabled,
                    chat_history_k=chat_history_k,
                    realtime_write_enabled=realtime_write_enabled,
                    run_id=run_id,
                    run_turn=index,
                )
                _append_job_row(job_id, row)
                if index % 10 == 0:
                    with JOBS_LOCK:
                        checkpoint_rows = list(JOBS[job_id].get("rows", []))
                        checkpoint_errors = list(JOBS[job_id].get("errors", []))
                    _write_checkpoint({
                        "created_at": datetime.now().isoformat(),
                        "run_config": data,
                        "mode": mode,
                        "method": method,
                        "method_label": _method_label(method),
                        "embedding_model": embedding_model,
                        "top_k": top_k,
                        "limit_per_session": limit_per_session,
                        "session_ids": session_ids,
                        "run_id": run_id,
                        "summary": summarize(checkpoint_rows),
                        "rows": checkpoint_rows,
                        "errors": checkpoint_errors,
                        "checkpoint": True,
                        "resume_source": resume_source,
                    })
                if mode == "qa" and api_delay_seconds > 0 and index < len(qas):
                    _update_job(job_id, current=f"{index}/{len(qas)} API 间隔等待 {api_delay_seconds:g}s")
                    time.sleep(api_delay_seconds)
            except Exception as exc:
                _append_job_error(job_id, {"qa_id": qa.get("qa_id", ""), "error": str(exc)})

        with JOBS_LOCK:
            job = JOBS[job_id]
            terminal_status = job["status"]
            if terminal_status == "running":
                job["status"] = "completed"
                job["current"] = "完成"
            job["finished_at"] = datetime.now().isoformat()
            payload = {
                "created_at": job["created_at"],
                "run_config": data,
                "mode": mode,
                "method": method,
                "method_label": _method_label(method),
                "embedding_model": embedding_model,
                "top_k": top_k,
                "limit_per_session": limit_per_session,
                "session_ids": session_ids,
                "run_id": run_id,
                "summary": summarize(job.get("rows", [])),
                "rows": job.get("rows", []),
                "errors": job.get("errors", []),
                "resume_source": job.get("resume_source", ""),
            }
        _write_latest(payload)
    except Exception as exc:
        _update_job(job_id, status="failed", current=f"失败：{exc}", finished_at=datetime.now().isoformat())
    finally:
        RUN_LOCK.release()


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/static/<path:filename>")
def static_files(filename: str):
    return send_from_directory(WEB_DIR / "static", filename)


@app.get("/api/sessions")
def api_sessions():
    manifest = load_manifest()
    sessions = []
    for item in manifest.get("sessions", []):
        session_id = item.get("session_id", "")
        memory = _load_memory(session_id)
        sessions.append({
            **item,
            "name": memory.get("session_name", session_id),
            "speaker_a": memory.get("locomo_speaker_a", ""),
            "speaker_b": memory.get("locomo_speaker_b", ""),
        })
    return jsonify({"sessions": sessions, "manifest": manifest, "embedding_models": available_models()})


@app.get("/api/qas")
def api_qas():
    session_id = request.args.get("session_id", "")
    limit = int(request.args.get("limit", "50") or 50)
    rows = [qa for qa in load_qas() if not session_id or qa.get("session_id") == session_id]
    return jsonify({"qas": rows[:limit], "total": len(rows)})


@app.get("/api/settings")
def api_get_settings():
    return jsonify({"settings": _load_web_settings(), "path": str(SETTINGS_PATH)})


@app.post("/api/settings")
def api_save_settings():
    data = request.get_json(force=True) or {}
    settings = data.get("settings") or {}
    if not isinstance(settings, dict):
        return jsonify({"error": "settings 必须是对象"}), 400
    payload = {
        "saved_at": datetime.now().isoformat(),
        "settings": settings,
        "note": "This file may contain local API settings in plain text. Remove secrets before publishing.",
    }
    write_json(SETTINGS_PATH, payload)
    return jsonify({"success": True, "path": str(SETTINGS_PATH), "saved_at": payload["saved_at"]})


@app.post("/api/test-api")
def api_test_api():
    data = request.get_json(force=True) or {}
    api_config = data.get("api_config") or {}
    try:
        result = _test_llm_api(api_config)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return jsonify(result)


@app.post("/api/run")
def api_run():
    data = request.get_json(force=True) or {}
    mode = data.get("mode", "retrieval")
    method = data.get("method", "pure_rag")
    embedding_model = data.get("embedding_model", "bge-m3")
    session_ids = data.get("session_ids") or []
    top_k = max(1, min(100, int(data.get("top_k", 20) or 20)))
    limit_per_session = int(data.get("limit_per_session", 20) or 20)
    decay_round = float(data.get("decay_rate_round", 20.0) or 20.0)
    decay_hours = float(data.get("decay_rate_hours", 168.0) or 168.0)
    save_prompts = bool(data.get("save_prompts", False))
    system_prompt = data.get("system_prompt", "")
    api_config = data.get("api_config") or {}
    api_delay_seconds = max(0.0, min(30.0, float(data.get("api_delay_seconds", 1.0) or 0.0)))
    time_decay_enabled = bool(data.get("time_decay_enabled", False))
    round_decay_enabled = bool(data.get("round_decay_enabled", False))
    dual_route_enabled = bool(data.get("dual_route_enabled", False))
    chat_history_k = max(1, min(30, int(data.get("chat_history_k", 10) or 10)))
    realtime_write_enabled = bool(data.get("realtime_write_enabled", False))
    run_id = str(data.get("run_id") or f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    data["run_id"] = run_id
    qas = _qa_subset(session_ids, limit_per_session)

    if not RUN_LOCK.acquire(blocking=False):
        return jsonify({"error": "已有任务正在运行，请等待结束后再开始"}), 409
    rows: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    try:
        for index, qa in enumerate(qas, start=1):
            try:
                rows.append(_build_row(
                    qa,
                    mode=mode,
                    method=method,
                    top_k=top_k,
                    decay_round=decay_round,
                    decay_hours=decay_hours,
                    embedding_model=embedding_model,
                    save_prompts=save_prompts,
                    system_prompt=system_prompt,
                    api_config=api_config,
                    time_decay_enabled=time_decay_enabled,
                    round_decay_enabled=round_decay_enabled,
                    dual_route_enabled=dual_route_enabled,
                    chat_history_k=chat_history_k,
                    realtime_write_enabled=realtime_write_enabled,
                    run_id=run_id,
                    run_turn=index,
                ))
                if mode == "qa" and api_delay_seconds > 0 and index < len(qas):
                    time.sleep(api_delay_seconds)
            except Exception as exc:
                errors.append({"qa_id": qa.get("qa_id", ""), "error": str(exc)})

        summary = summarize(rows)
        payload = {
            "created_at": datetime.now().isoformat(),
            "run_config": data,
            "mode": mode,
            "method": method,
            "method_label": _method_label(method),
            "embedding_model": embedding_model,
            "top_k": top_k,
            "limit_per_session": limit_per_session,
            "session_ids": session_ids,
            "run_id": run_id,
            "summary": summary,
            "rows": rows,
            "errors": errors,
        }
        _write_latest(payload)
        return jsonify(payload)
    finally:
        RUN_LOCK.release()


@app.post("/api/jobs")
def api_start_job():
    data = request.get_json(force=True) or {}
    session_ids = data.get("session_ids") or []
    limit_per_session = int(data.get("limit_per_session", 20) or 20)
    mode = data.get("mode", "retrieval")
    total = len(_qa_subset(session_ids, limit_per_session))
    if total <= 0:
        return jsonify({"error": "没有可运行的 QA，请先选择会话"}), 400
    if mode == "qa" and total > 100 and not data.get("allow_large_qa"):
        return jsonify({"error": f"QA 生成将调用 {total} 次 API。请先把每会话 QA 数调小，或勾选允许大批量 QA。"}), 400
    with JOBS_LOCK:
        has_active_job = any(job.get("status") in {"queued", "running"} for job in JOBS.values())
    if has_active_job or RUN_LOCK.locked():
        return jsonify({"error": "已有任务正在运行，请等待结束或停止后再开始"}), 409

    job_id = uuid.uuid4().hex[:12]
    with JOBS_LOCK:
        JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "current": "排队中",
            "total": total,
            "done": 0,
            "rows": [],
            "errors": [],
            "cancel_requested": False,
        }
    worker = threading.Thread(target=_run_job, args=(job_id, data), daemon=True)
    worker.start()
    return jsonify(_public_job(JOBS[job_id]))


@app.get("/api/jobs/<job_id>")
def api_job_status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "任务不存在"}), 404
        return jsonify(_public_job(job))


@app.post("/api/jobs/<job_id>/cancel")
def api_cancel_job(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "任务不存在"}), 404
        job["cancel_requested"] = True
        job["current"] = "正在停止，当前 API 请求结束后会停下"
    return jsonify(_public_job(job))


@app.get("/api/results/latest")
def api_latest():
    path = RESULTS_DIR / "web_latest.json"
    if not path.exists():
        return jsonify({"rows": [], "summary": {"count": 0}})
    return jsonify(json.loads(path.read_text(encoding="utf-8")))


@app.get("/api/export/csv")
def api_export_csv():
    path = RESULTS_DIR / "web_latest.csv"
    if not path.exists():
        return jsonify({"error": "尚无 CSV 结果，请先运行一次实验"}), 404
    return send_file(path, mimetype="text/csv", as_attachment=True, download_name="locomo_web_latest.csv")


@app.post("/api/results/clear")
def api_clear_results():
    for name in ("web_latest.json", "web_latest.csv"):
        path = RESULTS_DIR / name
        if path.exists():
            path.unlink()
    with JOBS_LOCK:
        JOBS.clear()
    return jsonify({"success": True, "message": "记录已清空"})


@app.post("/api/export/save-as")
def api_save_as():
    data = request.get_json(force=True) or {}
    source = RESULTS_DIR / "web_latest.csv"
    if not source.exists():
        return jsonify({"error": "尚无 CSV 结果，请先运行一次实验"}), 404
    try:
        target = _safe_result_target(data.get("path", ""))
        shutil.copyfile(source, target)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"success": True, "path": str(target)})


if __name__ == "__main__":
    port = int(os.environ.get("LOCOMO_PORT", "5050"))
    app.run(host="127.0.0.1", port=port, debug=False)
