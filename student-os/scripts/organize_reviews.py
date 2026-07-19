#!/usr/bin/env python3
"""Archive loose files under courses/<course>/reviews/<exam-scope>/ into subdirectories."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from course_layout import configure_stdout_utf8, resolve_course_dir
from exam_census_utils import exam_scope_key, relative_posix


# Source document suffixes that belong under 试卷/.
_SOURCE_SUFFIXES = {
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".doc",
    ".ppt",
    ".xls",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".mp3",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
}

# Markdown sidecars that are extracted text.
_TEXT_SIDECAR_SUFFIXES = (".pdf.md", ".raw.md")

# Names of subdirs/files that are protected (already organized or exam-census artifacts).
_PROTECTED_DIR_NAMES = {
    "README.md",
    "题型解析",
    "analysis",
    "真题精析",
    "备考指南.md",
    "公式总卡.md",
    "答题模板速查.md",
    "考前1小时清单.md",
    "题型频率统计.md",
    "试卷",
    "文本",
    "归档",
    "images",
}


def is_repair_summary(path: Path) -> bool:
    return path.name.endswith("-repair-summary.md") or path.name.endswith(".pdf-repair-summary.md")


def classify_path(path: Path) -> str | None:
    """Return the target subdirectory name for a loose path, or None to skip."""
    if path.is_dir():
        return None
    name = path.name
    if is_repair_summary(path):
        return "归档"
    lower = name.lower()
    if any(lower.endswith(suffix) for suffix in _TEXT_SIDECAR_SUFFIXES):
        return "文本"
    if path.suffix.lower() in _SOURCE_SUFFIXES:
        return "试卷"
    return None


def _is_git_tracked(path: Path, repo: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--error-unmatch", str(path.relative_to(repo))],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def _git_mv(src: Path, dst: Path, repo: Path) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "mv", str(src.relative_to(repo)), str(dst.relative_to(repo))],
        check=True,
        capture_output=True,
    )


def _shutil_move(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))


def move_path(src: Path, dst: Path, repo: Path) -> None:
    """Move using git mv when tracked; otherwise fall back to shutil."""
    if dst.exists():
        raise FileExistsError(f"Collision: target already exists {dst}")
    if (repo / ".git").is_dir() and _is_git_tracked(src, repo):
        _git_mv(src, dst, repo)
        return
    _shutil_move(src, dst)


def _list_files(dir_path: Path) -> list[str]:
    if not dir_path.exists():
        return []
    return sorted(p.name for p in dir_path.iterdir() if p.is_file())


def _list_recursive_files(dir_path: Path) -> list[str]:
    if not dir_path.exists():
        return []
    return sorted(
        p.relative_to(dir_path).as_posix() for p in dir_path.rglob("*") if p.is_file()
    )


def update_readme(scope_dir: Path) -> None:
    """Rewrite reviews/<scope>/README.md with an index of the scope contents."""
    readme = scope_dir / "README.md"

    lines = [
        "# 复习资料索引",
        "",
        "本目录由 `organize_reviews.py` 自动生成/更新。",
        "",
    ]

    archive_sections = [
        ("试卷", "原始试卷与文档"),
        ("文本", "文本提取 sidecar"),
        ("归档", "修复记录与元数据"),
        ("images", "图片资源"),
    ]
    for subdir, description in archive_sections:
        path = scope_dir / subdir
        files = _list_files(path)
        lines.append(f"## {description}（{subdir}/）")
        lines.append("")
        if files:
            for name in files:
                lines.append(f"- [{name}]({subdir}/{name})")
        else:
            lines.append("- 暂无")
        lines.append("")

    census_files = [
        "备考指南.md",
        "公式总卡.md",
        "答题模板速查.md",
        "考前1小时清单.md",
        "题型频率统计.md",
    ]
    present_census_files = [name for name in census_files if (scope_dir / name).exists()]
    if present_census_files:
        lines.append("## 备考资料包")
        lines.append("")
        for name in present_census_files:
            lines.append(f"- [{name}]({name})")
        lines.append("")

    census_dirs = [
        ("题型解析", "题型解析"),
        ("analysis", "多维分析"),
        ("真题精析", "真题精析"),
    ]
    for subdir, description in census_dirs:
        path = scope_dir / subdir
        if not path.is_dir():
            continue
        files = _list_recursive_files(path)
        lines.append(f"## {description}（{subdir}/）")
        lines.append("")
        if files:
            for rel in files:
                lines.append(f"- [{rel}]({subdir}/{rel})")
        else:
            lines.append("- 暂无")
        lines.append("")

    readme.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive loose files under courses/<course>/reviews/<exam-scope>/ into subdirectories."
    )
    parser.add_argument("repo", help="Target vault repository root")
    parser.add_argument("--course", required=True, help="Course slug or path under courses/")
    parser.add_argument("--exam-scope", required=True, help="Exam scope label such as 期中 or midterm")
    parser.add_argument("--semester", default="", help="Optional semester slug when resolving the course")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without moving files")
    return parser.parse_args()


def main() -> int:
    configure_stdout_utf8()
    args = parse_args()

    repo = Path(args.repo).resolve()
    course_dir = resolve_course_dir(repo, args.course, semester=args.semester)
    scope_key = exam_scope_key(args.exam_scope)
    scope_dir = course_dir / "reviews" / scope_key
    if not scope_dir.is_dir():
        raise SystemExit(f"Reviews directory does not exist: {scope_dir}")

    moves: list[tuple[Path, Path]] = []
    created_dirs: set[str] = set()
    for child in sorted(scope_dir.iterdir()):
        if child.name in _PROTECTED_DIR_NAMES:
            continue
        target_subdir = classify_path(child)
        if target_subdir is None:
            continue
        dst = scope_dir / target_subdir / child.name
        moves.append((child, dst))
        created_dirs.add(target_subdir)

    if not moves:
        print(
            json.dumps(
                {
                    "course": relative_posix(course_dir, repo),
                    "exam_scope": args.exam_scope,
                    "scope_dir": str(scope_dir),
                    "moved": [],
                    "created_dirs": [],
                    "dry_run": args.dry_run,
                    "message": "already organized, nothing to do",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    for src, dst in moves:
        if dst.exists():
            raise SystemExit(
                f"Collision: cannot move {relative_posix(src, repo)} to existing "
                f"{relative_posix(dst, repo)}"
            )

    moved: list[dict[str, str]] = []
    if args.dry_run:
        for src, dst in moves:
            moved.append(
                {
                    "source": relative_posix(src, repo),
                    "target": relative_posix(dst, repo),
                }
            )
        print(
            json.dumps(
                {
                    "course": relative_posix(course_dir, repo),
                    "exam_scope": args.exam_scope,
                    "scope_dir": str(scope_dir),
                    "moved": moved,
                    "created_dirs": sorted(created_dirs),
                    "dry_run": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    for subdir in sorted(created_dirs):
        (scope_dir / subdir).mkdir(parents=True, exist_ok=True)

    for src, dst in moves:
        move_path(src, dst, repo)
        moved.append(
            {
                "source": relative_posix(src, repo),
                "target": relative_posix(dst, repo),
            }
        )

    update_readme(scope_dir)

    print(
        json.dumps(
            {
                "course": relative_posix(course_dir, repo),
                "exam_scope": args.exam_scope,
                "scope_dir": str(scope_dir),
                "moved": moved,
                "created_dirs": sorted(created_dirs),
                "dry_run": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
