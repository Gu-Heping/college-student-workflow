#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


GROUP_RULES = [
    ("homework", ["/homework/", "homework/", "-solution.md", "problem-analysis", "homework-and-reviews.md"]),
    ("review", ["/reviews/", "reviews/", "chapter-review", "weekly-review-digest", "review-sheet"]),
    ("tasks", ["/tasks/", "tasks/", "weekly-plan"]),
    ("course", ["/courses/", "courses/", "dashboard.md", "/index.md"]),
    ("notes", ["/notes/", "notes/", "class-note"]),
    ("ops", [".student-os/", "/scripts/", "scripts/", "/templates/", "templates/", "repo-profile.md"]),
]

PREFIX = {
    "notes": "notes:",
    "homework": "homework:",
    "review": "review:",
    "tasks": "tasks:",
    "course": "course:",
    "ops": "ops:",
}


def detect_group(path: str) -> str:
    normalized = path.replace("\\", "/")
    for group, needles in GROUP_RULES:
        if any(needle in normalized for needle in needles):
            return group
    return "ops"


def main() -> int:
    parser = argparse.ArgumentParser(description="Group git changes for student-os repositories.")
    parser.add_argument("repo", help="Target repository root")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    result = subprocess.run(
        ["git", "-C", str(repo), "status", "--short"],
        check=False,
        capture_output=True,
        text=True,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    groups: dict[str, list[str]] = {}
    for line in lines:
        path = line[3:].strip()
        group = detect_group(path)
        groups.setdefault(group, []).append(path)

    payload = {
        "artifact_grouping": groups,
        "recommended_commit_split": [
            {
                "group": group,
                "suggested_commit_prefix": PREFIX.get(group, "ops:"),
                "paths": paths,
            }
            for group, paths in groups.items()
        ],
        "hold_back_files": [],
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
