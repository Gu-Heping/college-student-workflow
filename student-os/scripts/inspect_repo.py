#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


CANONICAL_DIRS = ["courses", "semesters", "projects", "tasks", "reviews", "references", "dashboards", ".student-os"]
LOCAL_ONLY_NAMES = {".ds_store", "thumbs.db"}
LOCAL_ONLY_PREFIXES = (".env.",)
BINARY_SUFFIXES = {
    ".7z",
    ".avi",
    ".bin",
    ".db",
    ".dmg",
    ".doc",
    ".docx",
    ".exe",
    ".gz",
    ".iso",
    ".jpeg",
    ".jpg",
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
    ".wav",
    ".webm",
    ".xls",
    ".xlsx",
    ".zip",
}
CACHE_DIR_NAMES = {"__pycache__", "node_modules"}
TEMP_DIR_NAMES = {"tmp", "temp"}
LARGE_FILE_BYTES = 10 * 1024 * 1024
DEFAULT_SKIP_DIR_NAMES = {
    ".git",
    ".dsh",
    ".pytest_cache",
    ".mypy_cache",
    "__pycache__",
    "node_modules",
    "tmp",
    "temp",
}
SKIP_DIR_PARTS = {
    (".student-os", "import-repair", "evidence"),
}


def configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
        sys.stderr.reconfigure(encoding="utf-8", newline="\n")
    except AttributeError:
        pass


def should_skip_dir(root: Path, directory: Path) -> bool:
    relative = directory.relative_to(root)
    parts = tuple(part.lower() for part in relative.parts)
    if directory.name.lower() in DEFAULT_SKIP_DIR_NAMES:
        return True
    return any(parts[-len(pattern) :] == pattern for pattern in SKIP_DIR_PARTS if len(parts) >= len(pattern))


def iter_repo_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root):
        current = Path(current_root)
        dirnames[:] = [name for name in dirnames if not should_skip_dir(root, current / name)]
        for filename in filenames:
            files.append(current / filename)
    return files


def relpath(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def parse_status_path(line: str) -> tuple[str, str, str]:
    status = line[:2]
    payload = line[3:].strip()
    if " -> " in payload:
        source, target = payload.split(" -> ", 1)
        return status, source.strip(), target.strip()
    return status, payload, payload


def should_skip_status_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip("/")
    parts = tuple(part.lower() for part in normalized.split("/") if part)
    if not parts:
        return False
    if parts[0] in DEFAULT_SKIP_DIR_NAMES:
        return True
    return any(parts[: len(pattern)] == pattern for pattern in SKIP_DIR_PARTS if len(parts) >= len(pattern))


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


def has_dir_component(path: Path, names: set[str]) -> bool:
    return any(part.lower() in names for part in path.parts[:-1])


def is_local_only_file(path: Path) -> bool:
    lower_name = path.name.lower()
    if lower_name in LOCAL_ONLY_NAMES:
        return True
    if lower_name == ".env":
        return True
    if lower_name.startswith(LOCAL_ONLY_PREFIXES):
        return True
    return bool(path.parts) and path.parts[0] == ".obsidian" and lower_name.startswith("workspace") and path.suffix.lower() == ".json"


def classify_binary_zone(root: Path, path: Path) -> str:
    rel = path.relative_to(root)
    if len(rel.parts) >= 2:
        return Path(*rel.parts[:2]).as_posix()
    return rel.parent.as_posix() or "."


def build_hygiene_warnings(
    *,
    conflict_files: list[str],
    generated_cache_files: list[str],
    local_only_files: list[str],
    temp_files: list[str],
    large_files: list[dict[str, object]],
    binary_zones: list[dict[str, object]],
) -> list[str]:
    warnings: list[str] = []
    if conflict_files:
        warnings.append("sync-conflict files detected; keep them out of normal commits and resolve manually")
    if generated_cache_files:
        warnings.append("generated caches detected; review .gitignore and hold them back from commits")
    if local_only_files:
        warnings.append("local-only workspace or environment files detected; keep them out of shared history by default")
    if temp_files:
        warnings.append("temporary files detected under tmp/temp paths; clean or ignore them before committing")
    if large_files:
        warnings.append("large files detected; keep bulky exports or OCR dumps out of normal commits unless explicitly intended")
    if binary_zones:
        warnings.append("binary-heavy areas detected; treat raw source documents and media as hold-back candidates by default")
    return warnings


def collect_large_files(root: Path, files: list[Path], dirty_lines: list[str]) -> list[dict[str, Any]]:
    large_entries: dict[str, dict[str, Any]] = {}
    for path in files:
        size = safe_file_size(path)
        if size is None or size <= LARGE_FILE_BYTES:
            continue
        relative = relpath(root, path)
        large_entries[relative] = {"path": relative, "bytes": size, "source": "worktree"}

    for line in dirty_lines:
        _, source_path, target_path = parse_status_path(line)
        for candidate_path in {source_path, target_path}:
            if not candidate_path:
                continue
            size = staged_blob_size(root, candidate_path)
            if size is None or size <= LARGE_FILE_BYTES:
                continue
            existing = large_entries.get(candidate_path)
            if existing is None or int(existing["bytes"]) < size:
                large_entries[candidate_path] = {"path": candidate_path, "bytes": size, "source": "index"}

    return [large_entries[key] for key in sorted(large_entries)]


def git_lines(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return []
    try:
        output = subprocess.run(
            [
                "git",
                "-c",
                "core.quotepath=false",
                "-c",
                "i18n.logOutputEncoding=utf-8",
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
    except FileNotFoundError:
        return []
    if output.returncode != 0:
        return []
    filtered: list[str] = []
    for line in output.stdout.splitlines():
        if not line.strip():
            continue
        _status, source_path, target_path = parse_status_path(line)
        if should_skip_status_path(source_path) or should_skip_status_path(target_path):
            continue
        filtered.append(line)
    return filtered


def build_full_payload(root: Path, *, scope: str) -> dict[str, object]:
    files = [] if scope == "git" else iter_repo_files(root)
    markdown = [p for p in files if p.suffix.lower() == ".md"]
    conflicts = [p for p in files if ".sync-conflict-" in p.name]
    generated_caches = [p for p in files if has_dir_component(p.relative_to(root), CACHE_DIR_NAMES)]
    local_only_files = [p for p in files if is_local_only_file(p.relative_to(root))]
    temp_files = [p for p in files if has_dir_component(p.relative_to(root), TEMP_DIR_NAMES)]
    dirty = git_lines(root)
    large_files = [] if scope == "repo" else collect_large_files(root, files, dirty)
    binary_files = [] if scope == "repo" else [p for p in files if p.suffix.lower() in BINARY_SUFFIXES]
    binary_zone_counts: dict[str, dict[str, object]] = {}
    for binary_file in binary_files:
        zone = classify_binary_zone(root, binary_file)
        entry = binary_zone_counts.setdefault(zone, {"path": zone, "file_count": 0, "extensions": set()})
        entry["file_count"] = int(entry["file_count"]) + 1
        cast_extensions = entry["extensions"]
        assert isinstance(cast_extensions, set)
        cast_extensions.add(binary_file.suffix.lower())
    binary_zones = [
        {
            "path": entry["path"],
            "file_count": entry["file_count"],
            "extensions": sorted(entry["extensions"]),
        }
        for entry in sorted(binary_zone_counts.values(), key=lambda item: str(item["path"]))
    ]
    warning_inputs = {
        "conflict_files": [relpath(root, p) for p in conflicts[:50]],
        "generated_cache_files": [relpath(root, p) for p in generated_caches[:50]],
        "local_only_files": [relpath(root, p) for p in local_only_files[:50]],
        "temp_files": [relpath(root, p) for p in temp_files[:50]],
        "large_files": large_files[:50],
        "binary_zones": binary_zones[:50],
    }
    return {
        "root": str(root),
        "is_git_repo": (root / ".git").exists(),
        "canonical_dirs_present": [name for name in CANONICAL_DIRS if (root / name).exists()],
        "markdown_files": len(markdown),
        "conflict_files": warning_inputs["conflict_files"],
        "generated_cache_files": warning_inputs["generated_cache_files"],
        "local_only_files": warning_inputs["local_only_files"],
        "temp_files": warning_inputs["temp_files"],
        "large_files": large_files[:50],
        "binary_files": [relpath(root, p) for p in binary_files[:50]],
        "binary_zones": binary_zones[:50],
        "hygiene_warnings": build_hygiene_warnings(**warning_inputs),
        "dirty_files": dirty,
        "counts": {
            "files_scanned": len(files),
            "dirty_files": len(dirty),
            "conflict_files": len(conflicts),
            "generated_cache_files": len(generated_caches),
            "local_only_files": len(local_only_files),
            "temp_files": len(temp_files),
            "large_files": len(large_files),
            "binary_files": len(binary_files),
            "binary_zones": len(binary_zones),
        },
    }


def compact_payload(payload: dict[str, object], *, limit: int, scope: str) -> dict[str, object]:
    counts = payload.get("counts") if isinstance(payload.get("counts"), dict) else {}
    dirty_files = payload.get("dirty_files") if isinstance(payload.get("dirty_files"), list) else []
    warnings = payload.get("hygiene_warnings") if isinstance(payload.get("hygiene_warnings"), list) else []
    return {
        "root": payload.get("root"),
        "is_git_repo": payload.get("is_git_repo"),
        "canonical_dirs_present": payload.get("canonical_dirs_present", []),
        "markdown_files": payload.get("markdown_files", 0),
        "compact": True,
        "scope": scope,
        "counts": counts,
        "dirty_count": len(dirty_files),
        "dirty_sample": dirty_files[:limit],
        "hygiene_warning_count": len(warnings),
        "hygiene_warnings": warnings[:limit],
        "warning_counts": {
            "conflict_files": counts.get("conflict_files", 0),
            "generated_cache_files": counts.get("generated_cache_files", 0),
            "local_only_files": counts.get("local_only_files", 0),
            "temp_files": counts.get("temp_files", 0),
            "large_files": counts.get("large_files", 0),
            "binary_zones": counts.get("binary_zones", 0),
        },
        "next_recommended_command": "Use group_git_changes.py --compact-json for commit planning; use task-specific repair queues for imported markdown cleanup.",
    }


def main() -> int:
    configure_stdout()
    parser = argparse.ArgumentParser(description="Inspect a student knowledge repository.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("--compact-json", action="store_true", help="Print a compact agent-facing summary.")
    parser.add_argument("--full-json", action="store_true", help="Print full inspect JSON; kept for explicitness and compatibility.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum sample items in compact output.")
    parser.add_argument(
        "--scope",
        choices=("repo", "git", "hygiene"),
        default="hygiene",
        help="Inspection scope. git avoids filesystem walking; repo skips binary-heavy hygiene checks.",
    )
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    result = build_full_payload(root, scope=args.scope)
    if args.compact_json and not args.full_json:
        result = compact_payload(result, limit=max(1, args.limit), scope=args.scope)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
