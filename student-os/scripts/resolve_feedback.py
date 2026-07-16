#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date

from pathlib import Path

from feedback_utils import (
    STATUS_TO_DIR,
    parse_frontmatter,
    quoted_yaml_string,
    replace_section,
    resolve_feedback_path,
    unique_feedback_path,
    write_feedback,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Mark a student-os feedback entry as resolved or archived.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("feedback", help="Feedback path, relative to repo or absolute")
    parser.add_argument("--status", default="resolved", choices=["resolved", "archived"])
    parser.add_argument("--resolution-summary", required=True, help="What changed to address this item")
    parser.add_argument("--fix-version", default="", help="Release version or milestone that addressed the issue")
    parser.add_argument("--changelog-note", default="- ", help="User-facing changelog hint")
    parser.add_argument("--follow-up", default="Verify in the next real workflow run.", help="Remaining verification or monitoring step")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    source_path = resolve_feedback_path(repo, args.feedback)
    if not source_path.exists():
        raise SystemExit(f"Feedback entry not found: {source_path}")

    frontmatter, body = parse_frontmatter(source_path)
    if not frontmatter:
        raise SystemExit(f"Feedback entry is missing frontmatter: {source_path}")

    today = date.today().isoformat()
    frontmatter["status"] = args.status
    frontmatter["updated"] = today
    frontmatter["fix_version"] = quoted_yaml_string(args.fix_version)

    triage_status = "resolved" if args.status == "resolved" else "archived"
    body = replace_section(
        body,
        "Follow-up",
        [
            f"- Triage status: {triage_status}",
            f"- Next step: {args.follow_up}",
        ],
    )
    body = replace_section(body, "Resolution Summary", [args.resolution_summary])
    body = replace_section(body, "Changelog Hint", [args.changelog_note])

    target_dir = repo / "feedback" / STATUS_TO_DIR[args.status]
    target_path = unique_feedback_path(target_dir, source_path.name, source_path=source_path)
    if target_path.resolve() != source_path:
        source_path.unlink()
    write_feedback(target_path, frontmatter, body)
    print(target_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
