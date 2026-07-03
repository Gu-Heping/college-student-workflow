#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import re

from course_layout import slugify

GENERATED_START = "<!-- student-os:course-links:start -->"
GENERATED_END = "<!-- student-os:course-links:end -->"


def fill_template(template_path: Path, replacements: dict[str, str]) -> str:
    text = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


def generated_block(lines: list[str]) -> str:
    content = "\n".join(lines).rstrip()
    return f"{GENERATED_START}\n{content}\n{GENERATED_END}"


def parse_courses_entries(courses_path: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    if not courses_path.exists():
        return entries
    for line in courses_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("- ") or ": " not in line:
            continue
        title, relpath = line[2:].split(": ", 1)
        entries.append((title.strip(), relpath.strip()))
    return entries


def sync_semester_overview(repo: Path, semester_root: Path, courses_path: Path) -> None:
    overview_path = semester_root / "overview.md"
    if not overview_path.exists():
        return

    course_lines = [
        f"- [{title}](../../{relpath}/index.md)"
        for title, relpath in parse_courses_entries(courses_path)
    ] or ["- [ ] Add first course"]
    overview_text = overview_path.read_text(encoding="utf-8")
    block = generated_block(course_lines)

    if GENERATED_START in overview_text and GENERATED_END in overview_text:
        pattern = rf"{re.escape(GENERATED_START)}.*?{re.escape(GENERATED_END)}"
        updated = re.sub(pattern, block, overview_text, count=1, flags=re.DOTALL)
    else:
        marker = "## Courses"
        start = overview_text.find(marker)
        if start == -1:
            updated = overview_text.rstrip() + "\n\n## Courses\n\n" + block + "\n"
        else:
            insert_at = overview_text.find("\n", start)
            if insert_at == -1:
                insert_at = len(overview_text)
                spacer = "\n\n"
            else:
                insert_at += 1
                spacer = "\n"
            updated = overview_text[:insert_at] + spacer + block + "\n" + overview_text[insert_at:]
    overview_path.write_text(updated, encoding="utf-8")


def enable_semester_mode(repo: Path) -> None:
    profile_path = repo / ".student-os" / "repo-profile.md"
    if not profile_path.exists():
        return
    profile_text = profile_path.read_text(encoding="utf-8")
    section_marker = "## Semester Conventions"
    if section_marker not in profile_text:
        return
    before, section = profile_text.split(section_marker, 1)
    if "enabled: false" not in section:
        return
    updated = before + section_marker + section.replace("enabled: false", "enabled: true", 1)
    profile_path.write_text(updated, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a course workspace for a student repository.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("course_name", help="Human-readable course name")
    parser.add_argument("--semester", default="", help="Optional semester label")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    semester_slug = slugify(args.semester, fallback="semester") if args.semester else ""
    course_slug = slugify(args.course_name, fallback="course")
    root = repo / "courses" / semester_slug / course_slug if semester_slug else repo / "courses" / course_slug
    today = date.today().isoformat()
    repl = {
        "course_name": args.course_name,
        "course_slug": course_slug,
        "semester_label": args.semester,
        "semester_slug": semester_slug,
        "date": today,
        "week_label": today,
        "project_slug": course_slug,
        "project_name": args.course_name,
        "task_title": f"{args.course_name} inbox item",
        "homework_title": "Homework",
        "review_title": "Review Sheet",
        "lab_title": "Lab Report",
        "topic_title": args.course_name,
    }

    for rel in ["notes", "homework", "reviews", "labs", "references"]:
        (root / rel).mkdir(parents=True, exist_ok=True)

    templates = {
        "index.md": "course-home.md",
        "dashboard.md": "course-dashboard.md",
    }
    template_root = Path(__file__).resolve().parents[1] / "templates"
    for output_name, template_name in templates.items():
        target = root / output_name
        if not target.exists():
            target.write_text(fill_template(template_root / template_name, repl), encoding="utf-8")

    if args.semester:
        enable_semester_mode(repo)
        semester_root = repo / "semesters" / semester_slug
        semester_root.mkdir(parents=True, exist_ok=True)
        overview_path = semester_root / "overview.md"
        if not overview_path.exists():
            overview_path.write_text(fill_template(template_root / "semester-overview.md", repl), encoding="utf-8")

        courses_path = semester_root / "courses.md"
        entry = f"- {args.course_name}: {root.relative_to(repo).as_posix()}"
        if courses_path.exists():
            lines = courses_path.read_text(encoding="utf-8").splitlines()
            if entry not in lines:
                lines.extend(["", entry])
                courses_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        else:
            courses_path.write_text(
                f"# Courses - {args.semester}\n\n## Entries\n\n{entry}\n",
                encoding="utf-8",
            )
        sync_semester_overview(repo, semester_root, courses_path)

    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
