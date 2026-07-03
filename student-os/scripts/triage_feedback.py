#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from feedback_utils import (
    STATUS_TO_DIR,
    VALID_KINDS,
    VALID_REPRO,
    VALID_SEVERITIES,
    parse_csv,
    parse_frontmatter,
    quoted_yaml_string,
    replace_section,
    write_feedback,
    yaml_list,
)


def resolve_feedback_path(repo: Path, candidate: str) -> Path:
    path = Path(candidate)
    if not path.is_absolute():
        path = repo / candidate
    return path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage an existing student-os feedback entry.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("feedback", help="Feedback path, relative to repo or absolute")
    parser.add_argument("--feedback-kind", choices=sorted(VALID_KINDS))
    parser.add_argument("--severity", choices=sorted(VALID_SEVERITIES))
    parser.add_argument("--reproducibility", choices=sorted(VALID_REPRO))
    parser.add_argument("--related-course", default=None)
    parser.add_argument("--related-artifacts", default=None, help="Comma-separated related artifact paths")
    parser.add_argument("--related-roles", default=None, help="Comma-separated related roles")
    parser.add_argument("--triage-status", default="triaged", help="Human-readable triage status")
    parser.add_argument("--follow-up", default=None, help="Suggested next step")
    parser.add_argument("--triage-notes", default="- ", help="Short triage notes")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    source_path = resolve_feedback_path(repo, args.feedback)
    if not source_path.exists():
        raise SystemExit(f"Feedback entry not found: {source_path}")

    frontmatter, body = parse_frontmatter(source_path)
    if not frontmatter:
        raise SystemExit(f"Feedback entry is missing frontmatter: {source_path}")

    today = date.today().isoformat()
    frontmatter["status"] = "triaged"
    frontmatter["updated"] = today
    if args.feedback_kind:
        frontmatter["feedback_kind"] = args.feedback_kind
        frontmatter["tags"] = f"[feedback, {args.feedback_kind}]"
    if args.severity:
        frontmatter["severity"] = args.severity
    if args.reproducibility:
        frontmatter["reproducibility"] = args.reproducibility
    if args.related_course is not None:
        frontmatter["related_course"] = quoted_yaml_string(args.related_course)
    if args.related_artifacts is not None:
        frontmatter["related_artifacts"] = f"[{yaml_list(parse_csv(args.related_artifacts))}]"
    if args.related_roles is not None:
        frontmatter["related_roles"] = f"[{yaml_list(parse_csv(args.related_roles))}]"

    next_step = args.follow_up or "Route to the next implementation batch."
    body = replace_section(
        body,
        "Follow-up",
        [
            f"- Triage status: {args.triage_status}",
            f"- Next step: {next_step}",
        ],
    )
    body = replace_section(body, "Triage Notes", [args.triage_notes])

    target_dir = repo / "feedback" / STATUS_TO_DIR["triaged"]
    target_path = target_dir / source_path.name
    if target_path.resolve() != source_path:
        source_path.unlink()
    write_feedback(target_path, frontmatter, body)
    print(target_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
