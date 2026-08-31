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
    normalize_scalar,
    quoted_yaml_string,
    replace_section,
    resolve_feedback_path,
    unique_feedback_path,
    write_feedback,
    yaml_list,
)


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
    parser.add_argument("--related-outputs", default=None, help="Comma-separated output artifacts related to the failure")
    parser.add_argument("--workflow-area", default=None, help="Workflow area where the problem surfaced")
    parser.add_argument("--agent-failure-mode", default=None, help="How the agent behavior failed or got stuck")
    parser.add_argument("--tool-failure-mode", default=None, help="How a Student OS script/tool contract contributed")
    parser.add_argument("--user-visible-impact", default=None, help="What the user actually experienced")
    parser.add_argument("--skill-improvement-candidate", default=None, help="Candidate skill/tool improvement")
    parser.add_argument("--issue-candidate", choices=["true", "false"], default=None, help="Whether this should become a GitHub issue candidate")
    parser.add_argument("--evidence-log", choices=["unavailable", "attached", "summarized"], default=None, help="Legacy alias for --evidence-source-status")
    parser.add_argument("--evidence-source-status", choices=["unavailable", "attached", "summarized"], default=None)
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
    if args.related_outputs is not None:
        frontmatter["related_outputs"] = f"[{yaml_list(parse_csv(args.related_outputs))}]"
    for attr, field in (
        ("workflow_area", "workflow_area"),
        ("agent_failure_mode", "agent_failure_mode"),
        ("tool_failure_mode", "tool_failure_mode"),
        ("user_visible_impact", "user_visible_impact"),
        ("skill_improvement_candidate", "skill_improvement_candidate"),
    ):
        value = getattr(args, attr)
        if value is not None:
            frontmatter[field] = quoted_yaml_string(value)
    evidence_source_status = args.evidence_source_status or args.evidence_log
    if evidence_source_status is not None:
        frontmatter["evidence_source_status"] = quoted_yaml_string(evidence_source_status)
        frontmatter["evidence_log"] = quoted_yaml_string(evidence_source_status)
    if args.issue_candidate is not None:
        frontmatter["issue_candidate"] = args.issue_candidate

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
    workflow_lines = [
        f"- Workflow area: {args.workflow_area or normalize_scalar(frontmatter.get('workflow_area', 'unknown')) or 'unknown'}",
        f"- Agent failure mode: {args.agent_failure_mode or normalize_scalar(frontmatter.get('agent_failure_mode', 'unknown')) or 'unknown'}",
        f"- Tool failure mode: {args.tool_failure_mode or normalize_scalar(frontmatter.get('tool_failure_mode', 'unknown')) or 'unknown'}",
        f"- User-visible impact: {args.user_visible_impact or normalize_scalar(frontmatter.get('user_visible_impact', 'unknown')) or 'unknown'}",
        f"- Skill improvement candidate: {args.skill_improvement_candidate or normalize_scalar(frontmatter.get('skill_improvement_candidate', 'unknown')) or 'unknown'}",
        f"- Issue candidate: {args.issue_candidate or normalize_scalar(frontmatter.get('issue_candidate', 'false')) or 'false'}",
        f"- Evidence source status: {evidence_source_status or normalize_scalar(frontmatter.get('evidence_source_status', '')) or normalize_scalar(frontmatter.get('evidence_log', 'summarized')) or 'summarized'}",
    ]
    body = replace_section(body, "Workflow Failure Analysis", workflow_lines)

    target_dir = repo / "feedback" / STATUS_TO_DIR["triaged"]
    target_path = unique_feedback_path(target_dir, source_path.name, source_path=source_path)
    if target_path.resolve() != source_path:
        source_path.unlink()
    write_feedback(target_path, frontmatter, body)
    print(target_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
