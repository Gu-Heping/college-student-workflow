#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path


VALID_KINDS = {
    "workflow",
    "template",
    "routing",
    "import",
    "git",
    "quality",
    "docs",
    "course-pack",
    "install",
    "other",
}
VALID_SEVERITIES = {"low", "medium", "high"}
VALID_REPRO = {"always", "sometimes", "one-off", "unclear"}
STATUS_TO_DIR = {
    "open": "raw",
    "triaged": "triaged",
    "resolved": "resolved",
    "archived": "resolved",
}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "feedback"


def quoted_yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def yaml_list(items: list[str]) -> str:
    if not items:
        return ""
    return ", ".join(quoted_yaml_string(item) for item in items)


def parse_csv(value: str) -> list[str]:
    if not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a structured feedback entry for student-os.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("--title", required=True, help="Short feedback title")
    parser.add_argument("--feedback-kind", default="other", choices=sorted(VALID_KINDS))
    parser.add_argument("--severity", default="medium", choices=sorted(VALID_SEVERITIES))
    parser.add_argument("--reproducibility", default="unclear", choices=sorted(VALID_REPRO))
    parser.add_argument("--status", default="open", choices=sorted(STATUS_TO_DIR))
    parser.add_argument("--source-context", default="", help="Original request or short source context")
    parser.add_argument("--related-course", default="", help="Related course name if any")
    parser.add_argument("--related-artifacts", default="", help="Comma-separated related artifact paths")
    parser.add_argument("--related-roles", default="", help="Comma-separated related roles")
    parser.add_argument("--what-happened", default="- ", help="What happened")
    parser.add_argument("--expected-behavior", default="- ", help="Expected behavior")
    parser.add_argument("--why-unsatisfying", default="- ", help="Why the result was unsatisfying")
    parser.add_argument("--likely-cause", default="- ", help="Likely cause")
    parser.add_argument("--suggested-improvement", default="- ", help="Suggested improvement")
    parser.add_argument("--evidence", default="- ", help="Evidence or related examples")
    parser.add_argument("--triage-status", default="open", help="Human-readable triage status")
    parser.add_argument("--follow-up", default="Review and classify.", help="Suggested next step")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    today = date.today().isoformat()
    folder = repo / "feedback" / STATUS_TO_DIR[args.status]
    folder.mkdir(parents=True, exist_ok=True)

    slug = slugify(args.title)
    filename = f"{today}-{slug}.md"
    target = folder / filename
    counter = 2
    while target.exists():
        target = folder / f"{today}-{slug}-{counter}.md"
        counter += 1

    artifacts = parse_csv(args.related_artifacts)
    roles = parse_csv(args.related_roles)
    frontmatter = [
        "---",
        "type: feedback",
        f"status: {args.status}",
        f"created: {today}",
        f"updated: {today}",
        f"tags: [feedback, {args.feedback_kind}]",
        f"feedback_kind: {args.feedback_kind}",
        f"severity: {args.severity}",
        f"reproducibility: {args.reproducibility}",
        f"source_context: {quoted_yaml_string(args.source_context)}",
        f"related_course: {quoted_yaml_string(args.related_course)}",
        f"related_artifacts: [{yaml_list(artifacts)}]",
        f"related_roles: [{yaml_list(roles)}]",
        "---",
        "",
    ]
    body = [
        f"# Feedback - {args.title}",
        "",
        "## What Happened",
        "",
        args.what_happened,
        "",
        "## Expected Behavior",
        "",
        args.expected_behavior,
        "",
        "## Why This Was Unsatisfying",
        "",
        args.why_unsatisfying,
        "",
        "## Likely Cause",
        "",
        args.likely_cause,
        "",
        "## Suggested Improvement",
        "",
        args.suggested_improvement,
        "",
        "## Evidence",
        "",
        args.evidence,
        "",
        "## Follow-up",
        "",
        f"- Triage status: {args.triage_status}",
        f"- Next step: {args.follow_up}",
        "",
    ]
    target.write_text("\n".join(frontmatter + body), encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
