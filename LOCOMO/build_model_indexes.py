"""Build isolated LOCOMO vector databases for selected embedding models."""
from __future__ import annotations

import argparse

from model_index import available_models, build_indexes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="*", default=["bge-large-en-v1.5", "bge-m3", "all-MiniLM-L6-v2"])
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    known = {m["name"]: m for m in available_models()}
    for name in args.models:
        if name not in known:
            raise SystemExit(f"Unknown model: {name}. Available: {', '.join(known)}")
        manifest = build_indexes(name, batch_size=args.batch_size)
        print(f"[done] {name}: sessions={manifest['total_sessions']}, vectors={manifest['total_vectors']}")


if __name__ == "__main__":
    main()
