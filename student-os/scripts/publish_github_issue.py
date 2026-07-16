#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from feedback_utils import parse_frontmatter, quoted_yaml_string, resolve_feedback_path, write_feedback
SCRIPT_DIR = Path(__file__).resolve().parent


def prepare_payload(repo: Path, feedback: str) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, "-B", str(SCRIPT_DIR / "prepare_github_issue.py"), str(repo), feedback],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def gh_available() -> bool:
    return shutil.which("gh") is not None


def gh_authenticated() -> bool:
    result = subprocess.run(
        ["gh", "auth", "status"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode == 0


def quote_for_shell(value: str) -> str:
    return '"' + value.replace('"', '\\"') + '"'


def store_issue_metadata(repo: Path, feedback_path: Path, *, issue_url: str, issue_number: str, issue_status: str) -> None:
    frontmatter, body = parse_frontmatter(feedback_path)
    if not frontmatter:
        raise SystemExit(f"Feedback entry is missing frontmatter: {feedback_path}")
    today = date.today().isoformat()
    frontmatter["github_issue_url"] = quoted_yaml_string(issue_url)
    frontmatter["github_issue_number"] = quoted_yaml_string(issue_number)
    frontmatter["github_issue_status"] = quoted_yaml_string(issue_status)
    frontmatter["reported_to_github_at"] = quoted_yaml_string(today)
    frontmatter["updated"] = today
    write_feedback(feedback_path, frontmatter, body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a student-os feedback item to GitHub Issues when gh is available.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("feedback", help="Feedback path, relative to repo or absolute")
    parser.add_argument("--github-repo", default="Gu-Heping/college-student-workflow", help="GitHub repo slug for issue creation")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    feedback_path = resolve_feedback_path(repo, args.feedback)
    payload = prepare_payload(repo, args.feedback)
    labels = payload["labels"]
    command = [
        "gh",
        "issue",
        "create",
        "--repo",
        args.github_repo,
        "--title",
        str(payload["title"]),
        "--body-file",
        "-",
    ]
    for label in labels:
        command.extend(["--label", str(label)])

    if not gh_available() or not gh_authenticated():
        temp_body = repo / "feedback" / "summaries" / f"{payload['feedback_id'] or 'issue'}-github-issue-body.md"
        temp_body.parent.mkdir(parents=True, exist_ok=True)
        temp_body.write_text(str(payload["body"]), encoding="utf-8", newline="\n")
        ready_command = " ".join(
            quote_for_shell(part) for part in [*command[:-1], str(temp_body)]
        )
        result = {
            "published": False,
            "feedback_id": payload["feedback_id"],
            "source_feedback_path": payload["source_feedback_path"],
            "gh_command": ready_command,
            "body_path": str(temp_body.relative_to(repo)).replace("\\", "/"),
            "privacy_warnings": payload["privacy_warnings"],
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(ready_command)
        return 0

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(str(payload["body"]))
        temp_path = Path(handle.name)
    try:
        actual_command = command[:-1] + [str(temp_path)]
        result = subprocess.run(
            actual_command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    finally:
        temp_path.unlink(missing_ok=True)

    issue_url = result.stdout.strip().splitlines()[-1]
    issue_number = issue_url.rstrip("/").split("/")[-1]
    store_issue_metadata(
        repo,
        feedback_path,
        issue_url=issue_url,
        issue_number=issue_number,
        issue_status="open",
    )
    output = {
        "published": True,
        "issue_url": issue_url,
        "issue_number": issue_number,
        "feedback_id": payload["feedback_id"],
        "source_feedback_path": payload["source_feedback_path"],
        "privacy_warnings": payload["privacy_warnings"],
    }
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(issue_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
