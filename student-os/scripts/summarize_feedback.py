#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from pathlib import Path

from feedback_utils import extract_title, normalize_scalar, parse_frontmatter


STATUSES = {
    "raw": "open",
    "triaged": "triaged",
    "resolved": "resolved",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize student-os feedback entries.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("--title", default="Current Feedback", help="Summary title")
    parser.add_argument("--scope", default="repository", help="Summary scope label")
    parser.add_argument(
        "--audience",
        default="workspace",
        choices=["workspace", "developer"],
        help="Choose a workspace snapshot or a developer-handoff summary layout.",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    feedback_root = repo / "feedback"
    all_items: list[dict[str, str]] = []

    for subdir, status in STATUSES.items():
        folder = feedback_root / subdir
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.md")):
            frontmatter, body = parse_frontmatter(path)
            if not frontmatter:
                continue
            data = dict(frontmatter)
            data["path"] = str(path.relative_to(repo)).replace("\\", "/")
            data["status"] = normalize_scalar(data.get("status", status))
            data["severity"] = normalize_scalar(data.get("severity", "medium"))
            data["feedback_kind"] = normalize_scalar(data.get("feedback_kind", "other"))
            data["workflow_area"] = normalize_scalar(data.get("workflow_area", ""))
            data["issue_candidate"] = normalize_scalar(data.get("issue_candidate", "false"))
            data["fix_version"] = normalize_scalar(data.get("fix_version", ""))
            data["feedback_id"] = normalize_scalar(data.get("feedback_id", ""))
            data["title"] = extract_title(body) or path.stem
            all_items.append(data)

    by_kind = Counter(item.get("feedback_kind", "other") for item in all_items)
    by_workflow_area = Counter(item.get("workflow_area") for item in all_items if item.get("workflow_area"))
    by_status = Counter(item.get("status", "open") for item in all_items)
    open_high = [
        item for item in all_items
        if item.get("status") in {"open", "triaged"} and item.get("severity") == "high"
    ]
    pending_items = [
        item for item in all_items
        if item.get("status") in {"open", "triaged"}
    ]
    recent_resolved = [
        item for item in all_items
        if item.get("status") == "resolved"
    ][-5:]

    today = date.today().isoformat()
    summary_path = feedback_root / "summaries" / f"{today}-{args.title.strip().lower().replace(' ', '-')}.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "---",
        "type: feedback-summary",
        "status: active",
        f"created: {today}",
        f"updated: {today}",
        "tags: [feedback, summary]",
        f"summary_scope: {args.scope}",
        f'summary_audience: "{args.audience}"',
        "---",
        "",
        f"# Feedback Summary - {args.title}",
        "",
        "## Snapshot",
        "",
        f"- Scope: {args.scope}",
        f"- Audience: {args.audience}",
        f"- Total feedback items: {len(all_items)}",
        f"- Open items: {by_status.get('open', 0)}",
        f"- Triaged items: {by_status.get('triaged', 0)}",
        f"- Resolved items: {by_status.get('resolved', 0)}",
        f"- Archived items: {by_status.get('archived', 0)}",
        "",
        "## By Kind",
        "",
    ]

    if by_kind:
        for kind, count in sorted(by_kind.items()):
            lines.append(f"- {kind}: {count}")
    else:
        lines.append("- No feedback recorded yet.")

    lines.extend(["", "## High Priority Open Items", ""])
    if open_high:
        for item in open_high:
            lines.append(
                f"- {item.get('title')}: {item.get('feedback_kind', 'other')} / {item.get('status', 'open')} / {item.get('path')}"
            )
    else:
        lines.append("- No high-priority open items.")

    lines.extend(["", "## Pending Queue", ""])
    if pending_items:
        for item in pending_items[:10]:
            lines.append(
                f"- {item.get('title')}: {item.get('feedback_kind', 'other')} / {item.get('severity', 'medium')} / {item.get('status', 'open')}"
            )
    else:
        lines.append("- No pending feedback items.")

    lines.extend(["", "## Workflow Areas", ""])
    if by_workflow_area:
        for area, count in sorted(by_workflow_area.items()):
            lines.append(f"- {area}: {count}")
    else:
        lines.append("- No workflow-area feedback recorded yet.")

    lines.extend(["", "## Recent Resolutions", ""])
    if recent_resolved:
        for item in recent_resolved:
            version = item.get("fix_version", "")
            suffix = f" / {version}" if version else ""
            lines.append(f"- {item.get('title')}: {item.get('feedback_kind', 'other')}{suffix}")
    else:
        lines.append("- No resolved items yet.")

    if args.audience == "developer":
        lines.extend(["", "## Developer Handoff", ""])
        if pending_items:
            for item in pending_items[:10]:
                feedback_id = item.get("feedback_id", "")
                lines.append(
                    f"- {feedback_id or item.get('path')}: {item.get('title')} ({item.get('feedback_kind', 'other')}, {item.get('severity', 'medium')}, workflow_area={item.get('workflow_area') or 'unknown'}, issue_candidate={item.get('issue_candidate', 'false')})"
                )
        else:
            lines.append("- No open developer follow-up items.")

    lines.extend(
        [
            "",
            "## Suggested Follow-up",
            "",
            "- Triage repeated `quality`, `workflow`, and `import` items first.",
            "- Move implementation-ready items to `feedback/triaged/` before bundling them into the next dev cycle.",
            "- Fold shipped fixes into `CHANGELOG.md` instead of copying full feedback entries.",
            "",
        ]
    )

    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
