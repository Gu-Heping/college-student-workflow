#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


CANONICAL_DIRS = ["courses", "semesters", "projects", "tasks", "reviews", "references", "dashboards", ".student-os"]


def git_lines(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return []
    try:
        output = subprocess.run(
            ["git", "-C", str(root), "status", "--short"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []
    if output.returncode != 0:
        return []
    return [line for line in output.stdout.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a student knowledge repository.")
    parser.add_argument("repo", help="Target repository root")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    files = [p for p in root.rglob("*") if p.is_file()]
    markdown = [p for p in files if p.suffix.lower() == ".md"]
    conflicts = [p for p in files if ".sync-conflict-" in p.name]
    dirty = git_lines(root)

    result = {
        "root": str(root),
        "is_git_repo": (root / ".git").exists(),
        "canonical_dirs_present": [name for name in CANONICAL_DIRS if (root / name).exists()],
        "markdown_files": len(markdown),
        "conflict_files": [str(p.relative_to(root)) for p in conflicts[:50]],
        "dirty_files": dirty,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
