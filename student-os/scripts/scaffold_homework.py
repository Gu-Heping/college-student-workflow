#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "item"


def fill_template(template_path: Path, replacements: dict[str, str]) -> str:
    text = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_if_missing(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def append_backlink(path: Path, marker: str, line: str) -> None:
    if not path.exists():
        return
    text = read_file(path)
    if line in text:
        return
    if marker in text:
        text = text.replace(marker, f"{marker}\n{line}")
    else:
        text += f"\n{line}\n"
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold homework, linked solution, and deadline task artifacts.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("course_slug", help="Course slug, e.g. analog-electronics")
    parser.add_argument("homework_title", help="Homework title")
    parser.add_argument("--course-name", default="", help="Human-readable course name")
    parser.add_argument("--due", default="", help="ISO due date")
    parser.add_argument("--problems", default="", help="Problem labels, e.g. 1,2a,3")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    course_slug = slugify(args.course_slug)
    course_name = args.course_name or course_slug.replace("-", " ").title()
    today = date.today().isoformat()
    homework_slug = slugify(args.homework_title)
    course_dir = repo / "courses" / course_slug
    template_root = Path(__file__).resolve().parents[1] / "templates"

    replacements = {
        "course_name": course_name,
        "course_slug": course_slug,
        "date": today,
        "week_label": today,
        "project_slug": course_slug,
        "project_name": course_name,
        "task_title": f"{course_name} - {args.homework_title}",
        "homework_title": args.homework_title,
        "review_title": args.homework_title,
        "lab_title": args.homework_title,
        "topic_title": args.homework_title,
        "solution_status": "derived",
    }

    homework_path = course_dir / "homework" / f"{homework_slug}.md"
    solution_path = course_dir / "homework" / f"{homework_slug}-solution.md"
    task_path = repo / "tasks" / "deadlines" / f"{course_slug}-{homework_slug}.md"

    homework_text = fill_template(template_root / "homework.md", replacements)
    if args.due:
        homework_text = homework_text.replace("- Due:", f"- Due: {args.due}")
    if args.problems:
        problem_lines = "\n".join([f"- [ ] {p.strip()}" for p in args.problems.split(",") if p.strip()])
        homework_text += f"\n## Problem List\n\n{problem_lines}\n"
    write_if_missing(homework_path, homework_text)

    solution_text = fill_template(template_root / "homework-solution.md", replacements)
    if args.problems:
        blocks = []
        for index, problem in enumerate([p.strip() for p in args.problems.split(",") if p.strip()], start=1):
            blocks.append(
                f"### Problem {problem}\n\n#### Setup\n\n- \n\n#### Derivation Or Reasoning\n\n1. \n\n#### Final Answer\n\n- \n\n#### Notes\n\n- Reference source:\n- Needs review:\n"
            )
        start = solution_text.find("### Problem 1")
        end = solution_text.find("## Self-check")
        if start != -1 and end != -1:
            solution_text = solution_text[:start] + "\n".join(blocks) + "\n\n" + solution_text[end:]
    write_if_missing(solution_path, solution_text)

    task_text = fill_template(template_root / "task.md", replacements)
    if args.due:
        task_text = task_text.replace("- Due:", f"- Due: {args.due}")
    task_text = task_text.replace("- Area:", "- Area: homework")
    write_if_missing(task_path, task_text)

    append_backlink(course_dir / "index.md", "## Active Items", f"- [ ] [{args.homework_title} homework](homework/{homework_slug}.md)")
    append_backlink(course_dir / "dashboard.md", "## Open Homework", f"- [{args.homework_title}](homework/{homework_slug}.md)")

    print(homework_path)
    print(solution_path)
    print(task_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
