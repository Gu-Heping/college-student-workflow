#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

from rebuild_indexes import is_generated_index_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize recent markdown activity.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    cutoff = datetime.now() - timedelta(days=args.days)
    files = []
    for path in root.rglob("*.md"):
        if is_generated_index_path(path, root):
            continue
        if datetime.fromtimestamp(path.stat().st_mtime) >= cutoff:
            files.append(path)

    print(f"# Activity Summary ({args.days} days)")
    print("")
    if not files:
        print("- No recent markdown changes found.")
        return 0

    for path in sorted(files):
        rel = str(path.relative_to(root)).replace("\\", "/")
        print(f"- {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
