#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from course_layout import discover_course_dirs


@dataclass
class TaskEntry:
    path: Path
    rel: str
    title: str
    status: str
    due_date: date | None
    area: str
    priority: str
    tags: list[str]
    course: str


def parse_frontmatter(text: str) -> dict[str, str]:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return {}
    parts = normalized.split("---\n", 2)
    if len(parts) < 3:
        return {}
    data: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def parse_yaml_list(value: str) -> list[str]:
    text = value.strip()
    if not text.startswith("[") or not text.endswith("]"):
        return []
    inner = text[1:-1].strip()
    if not inner:
        return []
    return [item.strip().strip('"').strip("'") for item in inner.split(",") if item.strip()]


def parse_due(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("- due:"):
            return stripped.split(":", 1)[1].strip()
    return None


def parse_detail(text: str, label: str) -> str:
    prefix = f"- {label.lower()}:"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(prefix):
            return stripped.split(":", 1)[1].strip()
    return ""


def parse_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def parse_iso_date(raw: str) -> date | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        return None


def is_actionable(status: str) -> bool:
    return status not in {"done", "archived"}


def is_due_in_window(entry: TaskEntry, today: date, horizon_end: date) -> bool:
    return entry.due_date is not None and (entry.due_date < today or today <= entry.due_date <= horizon_end)


def normalize_course_key(raw: str) -> str:
    return " ".join(raw.replace("-", " ").replace("_", " ").lower().split())


def read_task(path: Path, repo: Path) -> TaskEntry:
    text = path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)
    tags = parse_yaml_list(frontmatter.get("tags", "[]"))
    return TaskEntry(
        path=path,
        rel=path.relative_to(repo).as_posix(),
        title=parse_title(text, path.stem.replace("-", " ").title()),
        status=frontmatter.get("status", "active").strip('"').strip("'"),
        due_date=parse_iso_date(parse_due(text)),
        area=parse_detail(text, "Area"),
        priority=parse_detail(text, "Priority"),
        tags=tags,
        course=frontmatter.get("course", "").strip('"').strip("'"),
    )


def read_exam_signals(paths: list[Path], repo: Path, today: date, horizon_end: date) -> list[tuple[date, str]]:
    results: list[tuple[date, str]] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            lowered = stripped.lower()
            if not lowered.startswith("- exam:") and not lowered.startswith("- next exam:"):
                continue
            raw = stripped.split(":", 1)[1].strip()
            exam_date = parse_iso_date(raw)
            if exam_date is None or exam_date < today or exam_date > horizon_end:
                continue
            results.append((exam_date, path.relative_to(repo).as_posix()))
    return results


def imported_targets(repo: Path) -> list[str]:
    targets: list[str] = []
    roots = [
        repo / "references" / "imports" / "repaired",
        repo / "references" / "slides",
    ]
    for root in roots:
        if not root.exists():
            continue
        candidates = [path for path in sorted(root.glob("*.md")) if not path.name.endswith("-repair-summary.md")]
        for path in candidates[:10]:
            targets.append(path.relative_to(repo).as_posix())
    for course_dir in discover_course_dirs(repo / "courses"):
        reference_dir = course_dir / "references"
        if not reference_dir.exists():
            continue
        for path in sorted(reference_dir.glob("*.md"))[:10]:
            targets.append(path.relative_to(repo).as_posix())
    return targets


def course_action_lines(course_dirs: list[Path], task_entries: list[TaskEntry], repo: Path, today: date, horizon_end: date) -> list[str]:
    lines: list[str] = []
    deadlines_by_course: dict[str, list[TaskEntry]] = {}
    for entry in task_entries:
        if entry.course:
            deadlines_by_course.setdefault(normalize_course_key(entry.course), []).append(entry)
    for course_dir in course_dirs:
        rel = course_dir.relative_to(repo / "courses").as_posix()
        course_slug_name = rel.split("/")[-1].replace("-", " ")
        candidates = {normalize_course_key(course_slug_name)}
        course_home = course_dir / "index.md"
        if course_home.exists():
            course_title = parse_title(course_home.read_text(encoding="utf-8"), "")
            if course_title.lower().startswith("course - "):
                course_title = course_title[9:].strip()
            if course_title:
                candidates.add(normalize_course_key(course_title))
        matching = []
        for candidate in candidates:
            matching.extend(deadlines_by_course.get(candidate, []))
        matching = [entry for entry in matching if is_actionable(entry.status)]
        if matching:
            nearest = sorted(
                (entry for entry in matching if is_due_in_window(entry, today, horizon_end)),
                key=lambda item: item.due_date or date.max,
            )
            if nearest:
                lines.append(f"- `{rel}` -> prioritize {nearest[0].title} ({nearest[0].due_date.isoformat()})")
                continue
        lines.append(f"- `{rel}` -> review notes, homework, and imports for the next concrete study step")
    return lines or ["- No courses found"]


def render_task_line(entry: TaskEntry) -> str:
    due = entry.due_date.isoformat() if entry.due_date else "no-date"
    suffix = f" [{entry.priority}]" if entry.priority else ""
    return f"- {due} :: {entry.title} -> {entry.rel}{suffix}"


def render_exam_line(exam_date: date, label: str) -> str:
    return f"- {exam_date.isoformat()} :: {label}"


def write_dashboard(repo: Path, week_label: str, today: date, overdue: list[TaskEntry], upcoming: list[TaskEntry], inbox: list[TaskEntry], exam_count: int, imports: list[str], weekly_plan_rel: str) -> Path:
    dashboard_dir = repo / "dashboards" / "weekly"
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    dashboard_path = dashboard_dir / f"{week_label}.md"
    lines = [
        "---",
        "type: weekly-dashboard",
        "course:",
        "status: active",
        f"created: {today.isoformat()}",
        f"updated: {today.isoformat()}",
        "tags: [planning, weekly, dashboard]",
        "---",
        "",
        f"# Weekly Dashboard - {week_label}",
        "",
        "## Snapshot",
        "",
        f"- Weekly plan: {weekly_plan_rel}",
        f"- Overdue tasks: {len(overdue)}",
        f"- Upcoming deadlines: {len(upcoming)}",
        f"- Inbox items: {len(inbox)}",
        f"- Exams in range: {exam_count}",
        f"- Imported materials to review: {len(imports)}",
        "",
        "## Immediate Focus",
        "",
    ]
    if overdue:
        for entry in overdue[:5]:
            lines.append(f"- Overdue -> {entry.title} :: {entry.rel}")
    elif upcoming:
        for entry in upcoming[:5]:
            lines.append(f"- Upcoming -> {entry.title} :: {entry.rel}")
    else:
        lines.append("- No urgent deadlines.")

    lines.extend(["", "## Inbox Queue", ""])
    if inbox:
        for entry in inbox[:5]:
            lines.append(f"- {entry.title} :: {entry.rel}")
    else:
        lines.append("- Inbox is clear.")

    dashboard_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dashboard_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a weekly planning page and weekly dashboard from tasks, courses, and imports.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("--days", type=int, default=7, help="Deadline window in days")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    today = date.today()
    horizon_end = today + timedelta(days=args.days)
    exam_horizon_end = today + timedelta(days=max(args.days, 14))
    week_label = f"{today.isoformat()}-plus-{args.days}d"
    weekly_dir = repo / "tasks" / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)
    weekly_plan = weekly_dir / f"{week_label}.md"

    task_entries: list[TaskEntry] = []
    task_root = repo / "tasks"
    if task_root.exists():
        for path in sorted(task_root.rglob("*.md")):
            rel_from_tasks = path.relative_to(task_root).as_posix()
            if rel_from_tasks.startswith("weekly/"):
                continue
            task_entries.append(read_task(path, repo))

    overdue = sorted(
        [entry for entry in task_entries if entry.due_date and entry.due_date < today and is_actionable(entry.status)],
        key=lambda entry: entry.due_date or date.max,
    )
    upcoming = sorted(
        [entry for entry in task_entries if entry.due_date and today <= entry.due_date <= horizon_end and is_actionable(entry.status)],
        key=lambda entry: entry.due_date or date.max,
    )
    exam_entries = [
        entry for entry in task_entries
        if entry.due_date and today <= entry.due_date <= exam_horizon_end and is_actionable(entry.status)
        and ("exam" in entry.area.lower() or "exam" in entry.title.lower() or "exam" in [tag.lower() for tag in entry.tags])
    ]
    inbox_entries = [
        entry for entry in task_entries
        if entry.path.parent.name == "inbox" and is_actionable(entry.status)
    ]

    course_dirs = discover_course_dirs(repo / "courses")
    reviews = []
    for course_dir in course_dirs:
        for review_file in sorted((course_dir / "reviews").glob("*.md")):
            reviews.append(review_file.relative_to(repo).as_posix())
    imports = imported_targets(repo)
    exam_paths = []
    for course_dir in course_dirs:
        if (course_dir / "index.md").exists():
            exam_paths.append(course_dir / "index.md")
        if (course_dir / "dashboard.md").exists():
            exam_paths.append(course_dir / "dashboard.md")
    if (repo / "semesters").exists():
        exam_paths.extend(path for path in (repo / "semesters").rglob("*.md") if path.exists())
    exam_signals = sorted(read_exam_signals(exam_paths, repo, today, exam_horizon_end), key=lambda item: item[0])

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
        "## Overdue Carryover",
        "",
    ]
    if overdue:
        for entry in overdue:
            lines.append(render_task_line(entry))
    else:
        lines.append("- None")

    lines.extend(["", "## Deadlines This Week", ""])
    if upcoming:
        for entry in upcoming:
            lines.append(render_task_line(entry))
    else:
        lines.append("- None")

    lines.extend(["", "## Exams And Countdowns", ""])
    if exam_entries or exam_signals:
        exam_lines = [(entry.due_date or date.max, render_task_line(entry)) for entry in exam_entries]
        exam_lines.extend((exam_date, render_exam_line(exam_date, rel)) for exam_date, rel in exam_signals)
        for _, line in sorted(exam_lines, key=lambda item: item[0]):
            lines.append(line)
    else:
        lines.append("- No exam signals found")

    lines.extend(["", "## Course Actions", ""])
    lines.extend(course_action_lines(course_dirs, task_entries, repo, today, horizon_end))

    lines.extend(["", "## Review Targets", ""])
    if reviews:
        for review in reviews[:10]:
            lines.append(f"- {review}")
    else:
        lines.append("- No review artifacts found")

    lines.extend(["", "## Imported Materials To Curate", ""])
    if imports:
        for item in imports:
            lines.append(f"- {item}")
    else:
        lines.append("- No imported materials found")

    lines.extend(["", "## Project Actions", ""])
    project_paths = sorted((repo / "projects").rglob("*.md")) if (repo / "projects").exists() else []
    if project_paths:
        for path in project_paths[:5]:
            lines.append(f"- {path.relative_to(repo).as_posix()}")
    else:
        lines.append("- Review active project milestones")

    lines.extend(["", "## Inbox To Triage", ""])
    if inbox_entries:
        for entry in inbox_entries:
            lines.append(f"- {entry.title} :: {entry.rel}")
    else:
        lines.append("- Inbox is clear")

    dashboard_path = write_dashboard(
        repo=repo,
        week_label=week_label,
        today=today,
        overdue=overdue,
        upcoming=upcoming,
        inbox=inbox_entries,
        exam_count=len(exam_entries) + len(exam_signals),
        imports=imports,
        weekly_plan_rel=weekly_plan.relative_to(repo).as_posix(),
    )
    lines.extend(["", "## Dashboard Link", "", f"- {dashboard_path.relative_to(repo).as_posix()}"])

    weekly_plan.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(weekly_plan)
    print(dashboard_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
