#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "course"


def fill_template(template_path: Path, replacements: dict[str, str]) -> str:
    text = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a course workspace for a student repository.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("course_name", help="Human-readable course name")
    parser.add_argument("--semester", default="", help="Optional semester label")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    semester_slug = slugify(args.semester) if args.semester else ""
    course_slug = slugify(args.course_name)
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

    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
