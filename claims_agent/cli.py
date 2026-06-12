"""CLI: process one FNOL file or a directory of them.

Usage:
    python -m claims_agent.cli samples/fnol_01_fasttrack.txt
    python -m claims_agent.cli samples/ --out outputs/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import process_document
from .ingest import SUPPORTED_EXTENSIONS

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Autonomous FNOL claims processing agent")
    parser.add_argument("path", help="FNOL document (.pdf/.txt) or directory of documents")
    parser.add_argument("--out", help="Directory to write JSON results (default: print to stdout)")
    args = parser.parse_args(argv)

    target = Path(args.path)
    if target.is_dir():
        files = sorted(p for p in target.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
        if not files:
            print(f"No supported documents found in {target}", file=sys.stderr)
            return 1
    else:
        files = [target]

    out_dir = Path(args.out) if args.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for file in files:
        try:
            result = process_document(file)
        except Exception as exc:  # noqa: BLE001 - report per-file, keep batch going
            print(f"[error] {file}: {exc}", file=sys.stderr)
            failures += 1
            continue
        payload = json.dumps(result, indent=2, ensure_ascii=False)
        if out_dir:
            out_path = out_dir / f"{file.stem}.json"
            out_path.write_text(payload, encoding="utf-8")
            print(f"{file.name} -> {result['recommendedRoute']}  ({out_path})")
        else:
            print(payload)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
