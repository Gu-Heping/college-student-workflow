#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from collections import OrderedDict

from feedback_utils import (
    STATUS_TO_DIR,
    VALID_KINDS,
    VALID_REPRO,
    VALID_SEVERITIES,
    build_feedback_id,
    parse_csv,
    quoted_yaml_string,
    slugify,
    write_feedback,
    yaml_list,
)


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
    parser.add_argument("--developer-summary", default="- ", help="Short developer-facing summary")
    parser.add_argument("--evidence", default="- ", help="Evidence or related examples")
    parser.add_argument("--triage-status", default="open", help="Human-readable triage status")
    parser.add_argument("--follow-up", default="Review and classify.", help="Suggested next step")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    today = date.today().isoformat()
    feedback_root = repo / "feedback"
    folder = feedback_root / STATUS_TO_DIR[args.status]
    folder.mkdir(parents=True, exist_ok=True)
    slug = slugify(args.title)
    counter = 1
    while True:
        suffix = "" if counter == 1 else f"-{counter}"
        filename = f"{today}-{slug}{suffix}.md"
        if not any((feedback_root / subdir / filename).exists() for subdir in STATUS_TO_DIR.values()):
            target = folder / filename
            break
        counter += 1

    artifacts = parse_csv(args.related_artifacts)
    roles = parse_csv(args.related_roles)
    feedback_id = build_feedback_id(today, args.title)
    if counter > 1:
        feedback_id = f"{feedback_id}-{counter}"
    frontmatter = OrderedDict(
        [
            ("type", "feedback"),
            ("status", args.status),
            ("created", today),
            ("updated", today),
            ("feedback_id", quoted_yaml_string(feedback_id)),
            ("tags", f"[feedback, {args.feedback_kind}]"),
            ("feedback_kind", args.feedback_kind),
            ("severity", args.severity),
            ("reproducibility", args.reproducibility),
            ("source_context", quoted_yaml_string(args.source_context)),
            ("related_course", quoted_yaml_string(args.related_course)),
            ("related_artifacts", f"[{yaml_list(artifacts)}]"),
            ("related_roles", f"[{yaml_list(roles)}]"),
            ("github_issue_url", '""'),
            ("github_issue_number", '""'),
            ("github_issue_status", '""'),
            ("reported_to_github_at", '""'),
            ("fix_version", '""'),
        ]
    )
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
        "## Developer Summary",
        "",
        args.developer_summary,
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
    write_feedback(target, frontmatter, "\n".join(body))
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
