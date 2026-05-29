"""Download LOCOMO embedding model candidates into the local model root."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from huggingface_hub import snapshot_download


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parents[1]
MODEL_ROOT = WORKSPACE_ROOT / "assets" / "models"
CACHE_DIR = MODEL_ROOT / ".hf-cache"
REGISTRY_PATH = MODEL_ROOT / "embedding_models.json"


MODELS = [
    {
        "name": "bge-large-en-v1.5",
        "repo_id": "BAAI/bge-large-en-v1.5",
        "local_dir": MODEL_ROOT / "BAAI" / "bge-large-en-v1.5",
        "language": "English",
        "dim": 1024,
    },
    {
        "name": "bge-m3",
        "repo_id": "BAAI/bge-m3",
        "local_dir": MODEL_ROOT / "BAAI" / "bge-m3",
        "language": "Multilingual",
        "dim": 1024,
    },
    {
        "name": "all-MiniLM-L6-v2",
        "repo_id": "sentence-transformers/all-MiniLM-L6-v2",
        "local_dir": MODEL_ROOT / "sentence-transformers" / "all-MiniLM-L6-v2",
        "language": "English",
        "dim": 384,
    },
]


IGNORE_PATTERNS = [
    ".git/*",
    ".DS_Store",
    "*/.DS_Store",
    "imgs/*",
    "*.onnx",
    "onnx/*",
    "openvino/*",
    "*.tflite",
    "flax_model.msgpack",
    "rust_model.ot",
]


def copy_snapshot(snapshot_path: Path, target_dir: Path) -> None:
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(snapshot_path, target_dir, ignore=shutil.ignore_patterns(".cache"))


def main() -> None:
    MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    registry = []
    for model in MODELS:
        print(f"[download] {model['repo_id']}")
        snapshot = Path(snapshot_download(
            repo_id=model["repo_id"],
            cache_dir=CACHE_DIR,
            ignore_patterns=IGNORE_PATTERNS,
            max_workers=4,
        ))
        print(f"[copy] {snapshot} -> {model['local_dir']}")
        copy_snapshot(snapshot, model["local_dir"])
        registry.append({
            "name": model["name"],
            "repo_id": model["repo_id"],
            "local_dir": str(model["local_dir"]),
            "language": model["language"],
            "dim": model["dim"],
        })
    REGISTRY_PATH.write_text(json.dumps({
        "updated_at": datetime.now().isoformat(),
        "models": registry,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] registry: {REGISTRY_PATH}")


if __name__ == "__main__":
    main()
