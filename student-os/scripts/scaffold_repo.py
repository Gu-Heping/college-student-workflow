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

DEFAULT_GITATTRIBUTES = """*.md text eol=lf
"""

SECRET_GITIGNORE_RULES = [".env", "*.env", "!.env.example"]
MARKDOWN_GITATTRIBUTES_RULE = "*.md text eol=lf"


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


def ensure_gitignore(path: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"WRITE {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(DEFAULT_GITIGNORE, encoding="utf-8", newline="\n")
        return

    existing = path.read_text(encoding="utf-8")
    existing_lines = {line.strip() for line in existing.splitlines() if line.strip()}
    missing = [rule for rule in SECRET_GITIGNORE_RULES if rule not in existing_lines]
    if not missing:
        return
    suffix = existing
    if suffix and not suffix.endswith("\n"):
        suffix += "\n"
    suffix += "\n".join(missing) + "\n"
    path.write_text(suffix, encoding="utf-8", newline="\n")


def ensure_gitattributes(path: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"WRITE {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(DEFAULT_GITATTRIBUTES, encoding="utf-8", newline="\n")
        return

    existing = path.read_text(encoding="utf-8")
    existing_lines = {line.strip() for line in existing.splitlines() if line.strip()}
    if MARKDOWN_GITATTRIBUTES_RULE in existing_lines:
        return
    suffix = existing
    if suffix and not suffix.endswith("\n"):
        suffix += "\n"
    suffix += MARKDOWN_GITATTRIBUTES_RULE + "\n"
    path.write_text(suffix, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a markdown-first student knowledge base.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("--dry-run", action="store_true", help="Print planned operations only")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    for rel in DEFAULT_DIRS:
        ensure(root / rel, args.dry_run)

    ensure_gitignore(root / ".gitignore", args.dry_run)
    ensure_gitattributes(root / ".gitattributes", args.dry_run)
    write_file(
        root / ".student-os" / "repo-profile.md",
        Path(__file__).resolve().parents[1].joinpath("templates", "repo-profile.md").read_text(encoding="utf-8"),
        args.dry_run,
    )
    print(f"READY {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
