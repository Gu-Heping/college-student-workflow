#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from course_layout import discover_course_dirs, slugify


def fill_template(template_path: Path, replacements: dict[str, str]) -> str:
    text = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


def replace_section(text: str, heading: str, lines: list[str]) -> str:
    marker = f"## {heading}"
    start = text.find(marker)
    if start == -1:
        return text

    body_start = text.find("\n", start)
    if body_start == -1:
        return text

    body_start += 1
    next_heading = text.find("\n## ", body_start)
    replacement = "\n".join(lines).rstrip()
    if next_heading == -1:
        return text[:body_start] + "\n" + replacement + "\n"
    return text[:body_start] + "\n" + replacement + "\n\n" + text[next_heading + 1 :]


def sync_semester_overview(repo: Path, semester_root: Path, semester_slug: str) -> None:
    overview_path = semester_root / "overview.md"
    if not overview_path.exists():
        return

    semester_courses_root = repo / "courses" / semester_slug
    course_dirs = [
        path
        for path in discover_course_dirs(repo / "courses")
        if path.parent == semester_courses_root
    ]
    course_lines = [
        f"- [{course_dir.name.replace('-', ' ').title()}](../../{course_dir.relative_to(repo).as_posix()}/index.md)"
        for course_dir in course_dirs
    ] or ["- [ ] Add first course"]
    overview_text = overview_path.read_text(encoding="utf-8")
    overview_path.write_text(replace_section(overview_text, "Courses", course_lines), encoding="utf-8")


def enable_semester_mode(repo: Path) -> None:
    profile_path = repo / ".student-os" / "repo-profile.md"
    if not profile_path.exists():
        return
    profile_text = profile_path.read_text(encoding="utf-8")
    if "enabled: false" not in profile_text:
        return
    profile_path.write_text(profile_text.replace("enabled: false", "enabled: true", 1), encoding="utf-8")


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
        sync_semester_overview(repo, semester_root, semester_slug)

    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
