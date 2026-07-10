#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


GROUP_RULES = [
    ("ops", [".student-os/", "/scripts/", "scripts/", "/templates/", "templates/", "repo-profile.md"]),
    ("feedback", ["/feedback/", "feedback/", "feedback-summary", "type: feedback"]),
    ("imports", ["/references/imports/", "references/imports/", "/references/textbooks/", "references/textbooks/", "/references/slides/", "references/slides/", "imported-reference", "imported-table-summary", "slide-summary", "pdf-import-note"]),
    ("notes", ["/notes/", "notes/", "class-note"]),
    ("report", ["/labs/", "labs/", "lab-report"]),
    ("homework", ["/homework/", "homework/", "-solution.md", "problem-analysis"]),
    ("review", ["/reviews/", "reviews/", "chapter-review", "weekly-review-digest", "review-sheet"]),
    ("tasks", ["/tasks/", "tasks/", "weekly-plan"]),
    ("course", ["/courses/", "courses/", "/semesters/", "semesters/", "dashboard.md", "/index.md", "semester-overview"]),
]

PREFIX = {
    "feedback": "ops:",
    "imports": "imports:",
    "notes": "notes:",
    "report": "report:",
    "homework": "homework:",
    "review": "review:",
    "tasks": "tasks:",
    "course": "course:",
    "ops": "ops:",
}

HOLD_BACK_PATH_NEEDLES = [
    ".sync-conflict-",
    "__pycache__/",
    "/__pycache__/",
    ".DS_Store",
    "Thumbs.db",
    "node_modules/",
    "/node_modules/",
    ".obsidian/workspace",
]

HOLD_BACK_SUFFIXES = {
    ".7z",
    ".avi",
    ".bin",
    ".db",
    ".dmg",
    ".env",
    ".exe",
    ".gz",
    ".iso",
    ".jpeg",
    ".jpg",
    ".log",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".rar",
    ".sqlite",
    ".tar",
    ".doc",
    ".docx",
    ".wav",
    ".webm",
    ".xls",
    ".xlsx",
    ".zip",
}


def detect_group(path: str) -> str:
    normalized = path.replace("\\", "/")
    for group, needles in GROUP_RULES:
        if any(needle in normalized for needle in needles):
            return group
    return "ops"


def parse_status_path(line: str) -> tuple[str, str, str]:
    status = line[:2]
    payload = line[3:].strip()
    if " -> " in payload:
        source, target = payload.split(" -> ", 1)
        return status, source.strip(), target.strip()
    return status, payload, payload


def is_pure_delete_status(status: str) -> bool:
    return status in {"D ", " D"}


def display_path(source_path: str, target_path: str) -> str:
    if source_path == target_path:
        return target_path
    return f"{source_path} -> {target_path}"


def is_virtualenv_path(repo: Path, path: str) -> bool:
    raw_normalized = path.replace("\\", "/").strip("/")
    if not raw_normalized:
        return False
    lower_normalized = raw_normalized.lower()
    parts = [part for part in raw_normalized.split("/") if part]
    lower_parts = [part for part in lower_normalized.split("/") if part]
    markers = {"pyvenv.cfg", "bin", "scripts", "lib", "lib64", "include", "share"}
    for index, part in enumerate(lower_parts):
        if part not in {"env", "venv", ".venv"}:
            continue
        candidate_dir = repo.joinpath(*parts[: index + 1])
        tail = lower_parts[index + 1 :]
        if candidate_dir.joinpath("pyvenv.cfg").exists():
            return True
        if not tail:
            continue
        if tail[0] == "pyvenv.cfg":
            return True
        if tail[0] in markers and candidate_dir.joinpath("pyvenv.cfg").exists():
            return True
    return False


def has_path_component(path: str, names: set[str]) -> bool:
    normalized = path.replace("\\", "/").strip("/")
    if not normalized:
        return False
    parts = [part.lower() for part in normalized.split("/") if part]
    return any(part in names for part in parts)


def hold_back_reason(repo: Path, path: str) -> str:
    normalized = path.replace("\\", "/")
    lower = normalized.lower()
    name = Path(lower).name
    if name == ".env" or name.startswith(".env."):
        return "environment file"
    if ".sync-conflict-" in name:
        return "sync-conflict file"
    if is_virtualenv_path(repo, normalized):
        return "local virtual environment"
    if has_path_component(normalized, {"tmp", "temp"}):
        return "temporary file"
    if any(needle.lower() in lower for needle in HOLD_BACK_PATH_NEEDLES):
        if "__pycache__" in lower:
            return "generated cache"
        if ".obsidian/workspace" in lower:
            return "local workspace file"
        if "node_modules/" in lower:
            return "dependency cache"
        if lower.endswith(".log"):
            return "log file"
        return "local-only file"
    suffix = Path(lower).suffix
    if suffix in HOLD_BACK_SUFFIXES:
        if suffix in {".zip", ".7z", ".rar", ".tar", ".gz", ".iso", ".dmg"}:
            return "archive or disk image"
        if suffix in {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}:
            return "binary source document"
        if suffix in {".png", ".jpg", ".jpeg", ".mp3", ".mp4", ".mov", ".mkv", ".webm", ".wav", ".m4a", ".avi"}:
            return "binary media asset"
        if suffix in {".db", ".sqlite", ".bin", ".exe"}:
            return "binary or local environment artifact"
        if suffix == ".env":
            return "environment file"
        if suffix == ".log":
            return "log file"
    return ""


def read_git_status(repo: Path) -> tuple[list[str], bool, str]:
    if not (repo / ".git").exists():
        return [], False, "not a git repository"
    result = subprocess.run(
        ["git", "-C", str(repo), "status", "--short", "--untracked-files=all", "--ignored=matching"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or "git status failed"
        return [], False, stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return lines, True, ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Group git changes for student-os repositories.")
    parser.add_argument("repo", help="Target repository root")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    lines, is_git_repo, git_status_error = read_git_status(repo)
    groups: dict[str, list[str]] = {}
    hold_back_files: list[str] = []
    hold_back_reasons: dict[str, str] = {}
    for line in lines:
        status, source_path, target_path = parse_status_path(line)
        change_path = display_path(source_path, target_path)
        if status == "!!":
            hold_back_files.append(change_path)
            hold_back_reasons[change_path] = hold_back_reason(repo, target_path) or "ignored local artifact"
            continue
        if is_pure_delete_status(status) and source_path == target_path:
            group = detect_group(source_path)
            groups.setdefault(group, []).append(source_path)
            continue
        reason = hold_back_reason(repo, source_path) or hold_back_reason(repo, target_path)
        if reason:
            hold_back_files.append(change_path)
            hold_back_reasons[change_path] = reason
            continue
        group = detect_group(target_path)
        groups.setdefault(group, []).append(target_path)

    payload = {
        "is_git_repo": is_git_repo,
        "git_status_error": git_status_error,
        "artifact_grouping": groups,
        "recommended_commit_split": [
            {
                "group": group,
                "suggested_commit_prefix": PREFIX.get(group, "ops:"),
                "paths": paths,
            }
            for group, paths in groups.items()
        ],
        "hold_back_files": hold_back_files,
        "hold_back_reasons": hold_back_reasons,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
