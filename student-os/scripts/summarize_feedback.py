#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from pathlib import Path


STATUSES = {
    "raw": "open",
    "triaged": "triaged",
    "resolved": "resolved",
}


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return {}
    block = text.split("---\n", 2)[1]
    data: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize student-os feedback entries.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("--title", default="Current Feedback", help="Summary title")
    parser.add_argument("--scope", default="repository", help="Summary scope label")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    feedback_root = repo / "feedback"
    all_items: list[dict[str, str]] = []

    for subdir, status in STATUSES.items():
        folder = feedback_root / subdir
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.md")):
            data = parse_frontmatter(path)
            if not data:
                continue
            data["path"] = str(path.relative_to(repo)).replace("\\", "/")
            data.setdefault("status", status)
            all_items.append(data)

    by_kind = Counter(item.get("feedback_kind", "other") for item in all_items)
    open_high = [
        item for item in all_items
        if item.get("status") in {"open", "triaged"} and item.get("severity") == "high"
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
        "---",
        "",
        f"# Feedback Summary - {args.title}",
        "",
        "## Snapshot",
        "",
        f"- Scope: {args.scope}",
        f"- Total feedback items: {len(all_items)}",
        f"- Open items: {sum(1 for item in all_items if item.get('status') == 'open')}",
        f"- Triaged items: {sum(1 for item in all_items if item.get('status') == 'triaged')}",
        f"- Resolved items: {sum(1 for item in all_items if item.get('status') == 'resolved')}",
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
            lines.append(f"- {item.get('path')}: {item.get('feedback_kind', 'other')} / {item.get('status', 'open')}")
    else:
        lines.append("- No high-priority open items.")

    lines.extend(["", "## Recent Resolutions", ""])
    if recent_resolved:
        for item in recent_resolved:
            lines.append(f"- {item.get('path')}: {item.get('feedback_kind', 'other')}")
    else:
        lines.append("- No resolved items yet.")

    lines.extend(
        [
            "",
            "## Suggested Follow-up",
            "",
            "- Triage repeated `quality` and `workflow` items first.",
            "- Fold shipped fixes into `CHANGELOG.md` instead of copying full feedback entries.",
            "",
        ]
    )

    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
