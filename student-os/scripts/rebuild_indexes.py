#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from course_layout import discover_course_dirs


def list_children(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted([p for p in path.iterdir() if p.is_dir()])


def list_markdown_files(path: Path) -> list[str]:
    if not path.exists():
        return []
    return sorted([p.name for p in path.glob("*.md") if p.is_file()])


def write_index(path: Path, title: str, items: list[str]) -> None:
    body = [f"# {title}", "", "## Entries", ""]
    if items:
        body.extend(f"- {item}" for item in items)
    else:
        body.append("- None")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild generated markdown indexes for student repositories.")
    parser.add_argument("repo", help="Target repository root")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    index_dir = root / ".student-os" / "index"
    course_dirs = discover_course_dirs(root / "courses")
    write_index(
        index_dir / "courses.md",
        "Course Index",
        [str(path.relative_to(root)).replace("\\", "/") for path in course_dirs],
    )
    write_index(index_dir / "semesters.md", "Semester Index", [p.name for p in list_children(root / "semesters")])
    write_index(index_dir / "projects.md", "Project Index", [p.name for p in list_children(root / "projects")])
    write_index(index_dir / "tasks.md", "Task Index", [p.name for p in list_children(root / "tasks")])
    write_index(index_dir / "dashboards.md", "Dashboard Index", list_markdown_files(root / "dashboards"))

    semester_index_root = index_dir / "semesters"
    for semester_dir in list_children(root / "semesters"):
        write_index(
            semester_index_root / f"{semester_dir.name}.md",
            f"Semester - {semester_dir.name}",
            list_markdown_files(semester_dir),
        )

    recent = sorted(
        [p for p in root.rglob("*.md") if ".student-os\\index" not in str(p)],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:20]
    write_index(
        index_dir / "recent-activity.md",
        "Recent Activity",
        [str(p.relative_to(root)).replace("\\", "/") for p in recent],
    )
    print(index_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
