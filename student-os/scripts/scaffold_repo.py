#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
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


def write_file(path: Path, content: str, dry_run: bool) -> bool:
    if dry_run:
        print(f"WRITE {path}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8", newline="\n")
        return True
    return False


def ensure_gitignore(path: Path, dry_run: bool) -> bool:
    if dry_run:
        print(f"WRITE {path}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(DEFAULT_GITIGNORE, encoding="utf-8", newline="\n")
        return True

    existing = path.read_text(encoding="utf-8")
    existing_lines = {line.strip() for line in existing.splitlines() if line.strip()}
    missing = [rule for rule in SECRET_GITIGNORE_RULES if rule not in existing_lines]
    if not missing:
        return False
    suffix = existing
    if suffix and not suffix.endswith("\n"):
        suffix += "\n"
    suffix += "\n".join(missing) + "\n"
    path.write_text(suffix, encoding="utf-8", newline="\n")
    return True


def ensure_gitattributes(path: Path, dry_run: bool) -> bool:
    if dry_run:
        print(f"WRITE {path}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(DEFAULT_GITATTRIBUTES, encoding="utf-8", newline="\n")
        return True

    existing = path.read_text(encoding="utf-8")
    existing_lines = {line.strip() for line in existing.splitlines() if line.strip()}
    if MARKDOWN_GITATTRIBUTES_RULE in existing_lines:
        return False
    suffix = existing
    if suffix and not suffix.endswith("\n"):
        suffix += "\n"
    suffix += MARKDOWN_GITATTRIBUTES_RULE + "\n"
    path.write_text(suffix, encoding="utf-8", newline="\n")
    return True


def git_status_lines(root: Path) -> set[str]:
    if not (root / ".git").exists():
        return set()
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.quotepath=false",
            "-C",
            str(root),
            "status",
            "--short",
            "--untracked-files=all",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return set()
    return {line for line in result.stdout.splitlines() if line.strip()}


def relative_status_path(status_line: str) -> str:
    payload = status_line[3:].strip()
    if " -> " in payload:
        payload = payload.split(" -> ", 1)[1].strip()
    return payload.replace("\\", "/")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a markdown-first student knowledge base.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("--dry-run", action="store_true", help="Print planned operations only")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    changed_files: set[str] = set()
    for rel in DEFAULT_DIRS:
        ensure(root / rel, args.dry_run)

    gitignore = root / ".gitignore"
    if ensure_gitignore(gitignore, args.dry_run):
        changed_files.add(gitignore.relative_to(root).as_posix())
    gitattributes = root / ".gitattributes"
    if ensure_gitattributes(gitattributes, args.dry_run):
        changed_files.add(gitattributes.relative_to(root).as_posix())
    repo_profile = root / ".student-os" / "repo-profile.md"
    if write_file(
        repo_profile,
        Path(__file__).resolve().parents[1].joinpath("templates", "repo-profile.md").read_text(encoding="utf-8"),
        args.dry_run,
    ):
        changed_files.add(repo_profile.relative_to(root).as_posix())
    if not args.dry_run:
        current_status = sorted(git_status_lines(root))
        for line in current_status:
            if relative_status_path(line) not in changed_files:
                continue
            print(f"CHANGED {line}")
    print(f"READY {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
