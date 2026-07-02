#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path


def parse_due(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("- due:"):
            return stripped.split(":", 1)[1].strip()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a weekly planning page from tasks and courses.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("--days", type=int, default=7, help="Deadline window in days")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    today = date.today()
    week_label = f"{today.isoformat()}-plus-{args.days}d"
    weekly_dir = repo / "tasks" / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)
    weekly_plan = weekly_dir / f"{week_label}.md"

    deadlines = []
    for path in sorted((repo / "tasks").rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        due = parse_due(text)
        if not due:
            continue
        try:
            due_date = datetime.fromisoformat(due).date()
        except ValueError:
            continue
        if due_date <= today + timedelta(days=args.days):
            deadlines.append((due_date, path))

    courses = sorted([p.name for p in (repo / "courses").iterdir() if p.is_dir()]) if (repo / "courses").exists() else []
    reviews = []
    if (repo / "courses").exists():
        for course_dir in sorted([p for p in (repo / "courses").iterdir() if p.is_dir()]):
            for review_file in sorted((course_dir / "reviews").glob("*.md")):
                reviews.append(review_file.relative_to(repo).as_posix())
    lines = [
        "---",
        "type: weekly-plan",
        "course:",
        "status: active",
        f"created: {today.isoformat()}",
        f"updated: {today.isoformat()}",
        "tags: [planning, weekly]",
        "---",
        "",
        f"# Weekly Plan - {week_label}",
        "",
        "## Deadlines This Week",
        "",
    ]
    if deadlines:
        for due_date, path in deadlines:
            rel = path.relative_to(repo).as_posix()
            lines.append(f"- {due_date.isoformat()} :: {rel}")
    else:
        lines.append("- None")

    lines.extend(["", "## Course Actions", ""])
    if courses:
        for course in courses:
            lines.append(f"- Review current tasks and notes for `{course}`")
    else:
        lines.append("- No courses found")

    lines.extend(["", "## Review Targets", ""])
    if reviews:
        for review in reviews[:10]:
            lines.append(f"- {review}")
    else:
        lines.append("- No review artifacts found")

    lines.extend(["", "## Project Actions", "", "- Review active project milestones", "", "## Inbox To Triage", "", "- Review tasks/inbox/"])
    weekly_plan.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(weekly_plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
