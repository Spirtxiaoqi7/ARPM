#!/usr/bin/env python
"""Download the bundled embedding model into the expected local directory."""

from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download


DEFAULT_REPO_ID = "shibing624/text2vec-base-chinese"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download the ARPM embedding model into a local folder."
    )
    parser.add_argument(
        "--target-dir",
        required=True,
        help="Local directory where the model should be stored.",
    )
    parser.add_argument(
        "--repo-id",
        default=DEFAULT_REPO_ID,
        help=f"Hugging Face repo id. Default: {DEFAULT_REPO_ID}",
    )
    parser.add_argument(
        "--endpoint",
        default="",
        help="Optional Hugging Face endpoint mirror.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_dir = Path(args.target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    kwargs = {
        "repo_id": args.repo_id,
        "local_dir": str(target_dir),
        "local_dir_use_symlinks": False,
        "resume_download": True,
    }
    if args.endpoint:
        kwargs["endpoint"] = args.endpoint

    print(f"[ARPM] Downloading model {args.repo_id} -> {target_dir}")
    snapshot_download(**kwargs)
    print("[ARPM] Model download complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
