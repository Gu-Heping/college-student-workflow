#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path


GROUP_RULES = [
    ("ops", [".student-os/", "/scripts/", "scripts/", "/templates/", "templates/", "repo-profile.md"]),
    ("feedback", ["/feedback/", "feedback/", "feedback-summary", "type: feedback"]),
    ("imports", ["/references/imports/", "references/imports/", "/references/textbooks/", "references/textbooks/", "/references/slides/", "references/slides/", "imported-reference", "imported-table-summary", "slide-summary", "pdf-import-note"]),
    ("notes", ["/notes/", "notes/", "class-note"]),
    ("report", ["/labs/", "labs/", "lab-report"]),
    ("homework", ["/homework/", "homework/", "-solution.md", "problem-analysis"]),
    (
        "review",
        [
            "/reviews/",
            "reviews/",
            "chapter-review",
            "weekly-review-digest",
            "review-sheet",
            "exam-census",
            "exam-type-",
            "exam-prep-guide",
            "formula-cheat-sheet",
            "answer-template-quickref",
            "pre-exam-one-hour-checklist",
            "题型频率统计",
            "题型解析",
            "备考指南",
            "公式总卡",
            "答题模板速查",
            "考前1小时清单",
        ],
    ),
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
LARGE_FILE_BYTES = 10 * 1024 * 1024


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
        return status, unquote_status_path(source.strip()), unquote_status_path(target.strip())
    path = unquote_status_path(payload)
    return status, path, path


def unquote_status_path(path: str) -> str:
    if len(path) >= 2 and path[0] == '"' and path[-1] == '"':
        try:
            value = ast.literal_eval(path)
        except (SyntaxError, ValueError):
            return path
        if isinstance(value, str):
            return value
    return path


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


def safe_file_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def staged_blob_size(repo: Path, path: str) -> int | None:
    if not (repo / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-s", f":{path}"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return None
    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def git_diff_quiet(repo: Path, path: str, *, cached: bool = False, ignore_cr_at_eol: bool = False) -> bool:
    command = ["git", "-C", str(repo), "diff", "--quiet"]
    if cached:
        command.append("--cached")
    if ignore_cr_at_eol:
        command.append("--ignore-cr-at-eol")
    command.extend(["--", f":(literal){path}"])
    result = subprocess.run(command, check=False, capture_output=True)
    return result.returncode == 0


def is_tracked_markdown_eol_only(repo: Path, status: str, source_path: str, target_path: str) -> bool:
    if status == "??" or is_pure_delete_status(status):
        return False
    if source_path != target_path:
        return False
    if not target_path.lower().endswith(".md"):
        return False
    has_regular_diff = not git_diff_quiet(repo, target_path) or not git_diff_quiet(repo, target_path, cached=True)
    if not has_regular_diff:
        return True
    has_content_diff = (
        not git_diff_quiet(repo, target_path, ignore_cr_at_eol=True)
        or not git_diff_quiet(repo, target_path, cached=True, ignore_cr_at_eol=True)
    )
    return not has_content_diff


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
    candidate = repo / Path(normalized)
    size = safe_file_size(candidate)
    if size is not None and size > LARGE_FILE_BYTES:
        return "large file"
    staged_size = staged_blob_size(repo, normalized)
    if staged_size is not None and staged_size > LARGE_FILE_BYTES:
        return "large file"
    return ""


def read_git_status(repo: Path, *, include_ignored: bool = True) -> tuple[list[str], bool, str]:
    if not (repo / ".git").exists():
        return [], False, "not a git repository"
    command = [
        "git",
        "-c",
        "core.quotepath=false",
        "-c",
        "i18n.logOutputEncoding=utf-8",
        "-C",
        str(repo),
        "status",
        "--short",
        "--untracked-files=all",
    ]
    if include_ignored:
        command.append("--ignored=matching")
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or "git status failed"
        return [], False, stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return lines, True, ""


def configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
        sys.stderr.reconfigure(encoding="utf-8", newline="\n")
    except AttributeError:
        pass


def main() -> int:
    configure_stdout()
    parser = argparse.ArgumentParser(description="Group git changes for student-os repositories.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument(
        "--compact-json",
        "--preflight",
        dest="compact_json",
        action="store_true",
        help="Print a compact preflight summary without large hold-back path lists.",
    )
    parser.add_argument("--full-json", action="store_true", help="Force full output shape; non-compact mode is already full.")
    parser.add_argument(
        "--include-ignored",
        action="store_true",
        help="Include ignored files in compact output. Non-compact output includes ignored files by default.",
    )
    parser.add_argument("--limit", type=int, default=20, help="Maximum paths per list in --compact-json output")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    compact_mode = args.compact_json and not args.full_json
    lines, is_git_repo, git_status_error = read_git_status(repo, include_ignored=not compact_mode or args.include_ignored)
    groups: dict[str, list[str]] = {}
    eol_only_files: list[str] = []
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
        if is_tracked_markdown_eol_only(repo, status, source_path, target_path):
            eol_only_files.append(change_path)
            continue
        group = detect_group(target_path)
        groups.setdefault(group, []).append(target_path)

    payload = {
        "is_git_repo": is_git_repo,
        "git_status_error": git_status_error,
        "artifact_grouping": groups,
        "eol_only_files": eol_only_files,
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
    if compact_mode:
        limit = max(1, args.limit)
        compact_payload = {
            "is_git_repo": is_git_repo,
            "git_status_error": git_status_error,
            "compact": True,
            "ignored_included": bool(args.include_ignored),
            "counts": {
                "changed_groups": {group: len(paths) for group, paths in groups.items()},
                "eol_only_files": len(eol_only_files),
                "hold_back_files": len(hold_back_files),
            },
            "recommended_commit_split": [
                {
                    "group": item["group"],
                    "suggested_commit_prefix": item["suggested_commit_prefix"],
                    "path_count": len(item["paths"]),
                    "sample_paths": item["paths"][:limit],
                }
                for item in payload["recommended_commit_split"]
            ],
            "eol_only_sample": eol_only_files[:limit],
            "hold_back_reason_counts": {
                reason: list(hold_back_reasons.values()).count(reason)
                for reason in sorted(set(hold_back_reasons.values()))
            },
            "hold_back_sample": hold_back_files[:limit],
            "agent_rules": [
                "Use this output for preflight decisions.",
                "Do not read spill files just to inspect hold-back binary assets.",
                "Inspect target paths directly before modifying them.",
            ],
        }
        payload = compact_payload
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
