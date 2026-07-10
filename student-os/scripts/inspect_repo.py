#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


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


def iter_repo_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        current = Path(current_root)
        for filename in filenames:
            files.append(current / filename)
    return files


def relpath(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


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
    if binary_zones:
        warnings.append("binary-heavy areas detected; treat raw source documents and media as hold-back candidates by default")
    return warnings


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
    return [line for line in output.stdout.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a student knowledge repository.")
    parser.add_argument("repo", help="Target repository root")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    files = iter_repo_files(root)
    markdown = [p for p in files if p.suffix.lower() == ".md"]
    conflicts = [p for p in files if ".sync-conflict-" in p.name]
    generated_caches = [p for p in files if has_dir_component(p.relative_to(root), CACHE_DIR_NAMES)]
    local_only_files = [p for p in files if is_local_only_file(p.relative_to(root))]
    temp_files = [p for p in files if has_dir_component(p.relative_to(root), TEMP_DIR_NAMES)]
    binary_files = [p for p in files if p.suffix.lower() in BINARY_SUFFIXES]
    binary_zone_counts: dict[str, dict[str, object]] = {}
    for binary_file in binary_files:
        zone = classify_binary_zone(root, binary_file)
        entry = binary_zone_counts.setdefault(zone, {"path": zone, "file_count": 0, "extensions": set()})
        entry["file_count"] = int(entry["file_count"]) + 1
        cast_extensions = entry["extensions"]
        assert isinstance(cast_extensions, set)
        cast_extensions.add(binary_file.suffix.lower())
    dirty = git_lines(root)
    binary_zones = [
        {
            "path": entry["path"],
            "file_count": entry["file_count"],
            "extensions": sorted(entry["extensions"]),
        }
        for entry in sorted(binary_zone_counts.values(), key=lambda item: str(item["path"]))
    ]

    result = {
        "root": str(root),
        "is_git_repo": (root / ".git").exists(),
        "canonical_dirs_present": [name for name in CANONICAL_DIRS if (root / name).exists()],
        "markdown_files": len(markdown),
        "conflict_files": [relpath(root, p) for p in conflicts[:50]],
        "generated_cache_files": [relpath(root, p) for p in generated_caches[:50]],
        "local_only_files": [relpath(root, p) for p in local_only_files[:50]],
        "temp_files": [relpath(root, p) for p in temp_files[:50]],
        "binary_files": [relpath(root, p) for p in binary_files[:50]],
        "binary_zones": binary_zones[:50],
        "hygiene_warnings": build_hygiene_warnings(
            conflict_files=[relpath(root, p) for p in conflicts[:50]],
            generated_cache_files=[relpath(root, p) for p in generated_caches[:50]],
            local_only_files=[relpath(root, p) for p in local_only_files[:50]],
            temp_files=[relpath(root, p) for p in temp_files[:50]],
            binary_zones=binary_zones[:50],
        ),
        "dirty_files": dirty,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
