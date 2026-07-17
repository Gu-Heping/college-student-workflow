#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_DIRS = [
    "courses",
    "semesters",
    "projects",
    "tasks/inbox",
    "tasks/deadlines",
    "tasks/weekly",
    "reviews",
    "references",
    "references/imports/raw",
    "references/imports/repaired",
    "references/textbooks",
    "references/slides",
    "dashboards",
    "feedback/raw",
    "feedback/triaged",
    "feedback/resolved",
    "feedback/summaries",
    ".student-os/index",
    ".student-os/state",
]

DEFAULT_GITIGNORE = """*.sync-conflict-*
__pycache__/
.DS_Store
Thumbs.db
node_modules/
.obsidian/workspace*.json
tmp/
temp/
*.log
.env
*.env
!.env.example
"""


def ensure(path: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"MKDIR {path}")
        return
    path.mkdir(parents=True, exist_ok=True)


def write_file(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"WRITE {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a markdown-first student knowledge base.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("--dry-run", action="store_true", help="Print planned operations only")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    for rel in DEFAULT_DIRS:
        ensure(root / rel, args.dry_run)

    write_file(root / ".gitignore", DEFAULT_GITIGNORE, args.dry_run)
    write_file(
        root / ".student-os" / "repo-profile.md",
        Path(__file__).resolve().parents[1].joinpath("templates", "repo-profile.md").read_text(encoding="utf-8"),
        args.dry_run,
    )
    print(f"READY {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
