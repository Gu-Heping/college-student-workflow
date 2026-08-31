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
    parser.add_argument("--workflow-area", default="", help="Workflow area where the problem surfaced")
    parser.add_argument("--agent-failure-mode", default="", help="How the agent behavior failed or got stuck")
    parser.add_argument("--tool-failure-mode", default="", help="How a Student OS script/tool contract contributed")
    parser.add_argument("--user-visible-impact", default="", help="What the user actually experienced")
    parser.add_argument("--skill-improvement-candidate", default="", help="Candidate skill/tool improvement")
    parser.add_argument("--issue-candidate", action="store_true", help="Mark this feedback as a candidate GitHub issue")
    parser.add_argument("--evidence-from-current-conversation", default="", help="Conversation-derived evidence summary from the active workflow")
    parser.add_argument("--related-outputs", default="", help="Comma-separated output artifacts related to the failure")
    parser.add_argument(
        "--evidence-log",
        default="summarized",
        choices=["unavailable", "attached", "summarized"],
        help="Legacy alias for --evidence-source-status.",
    )
    parser.add_argument(
        "--evidence-source-status",
        default=None,
        choices=["unavailable", "attached", "summarized"],
        help="Whether evidence comes from the current workflow summary, attached artifacts, or is unavailable.",
    )
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
    outputs = parse_csv(args.related_outputs)
    roles = parse_csv(args.related_roles)
    feedback_id = build_feedback_id(today, args.title)
    if counter > 1:
        feedback_id = f"{feedback_id}-{counter}"
    evidence_source_status = args.evidence_source_status or args.evidence_log
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
            ("related_outputs", f"[{yaml_list(outputs)}]"),
            ("related_roles", f"[{yaml_list(roles)}]"),
            ("workflow_area", quoted_yaml_string(args.workflow_area)),
            ("agent_failure_mode", quoted_yaml_string(args.agent_failure_mode)),
            ("tool_failure_mode", quoted_yaml_string(args.tool_failure_mode)),
            ("user_visible_impact", quoted_yaml_string(args.user_visible_impact)),
            ("skill_improvement_candidate", quoted_yaml_string(args.skill_improvement_candidate)),
            ("issue_candidate", "true" if args.issue_candidate else "false"),
            ("evidence_source_status", quoted_yaml_string(evidence_source_status)),
            ("evidence_log", quoted_yaml_string(evidence_source_status)),
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
        "## Workflow Failure Analysis",
        "",
        f"- Workflow area: {args.workflow_area or 'unknown'}",
        f"- Agent failure mode: {args.agent_failure_mode or 'unknown'}",
        f"- Tool failure mode: {args.tool_failure_mode or 'unknown'}",
        f"- User-visible impact: {args.user_visible_impact or 'unknown'}",
        f"- Skill improvement candidate: {args.skill_improvement_candidate or 'unknown'}",
        f"- Issue candidate: {'true' if args.issue_candidate else 'false'}",
        f"- Evidence source status: {evidence_source_status}",
        "",
        "## Evidence From Current Conversation",
        "",
        args.evidence_from_current_conversation or "- Not provided.",
        "",
        "## Related Outputs",
        "",
        "\n".join(f"- {item}" for item in outputs) if outputs else "- Not provided.",
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
