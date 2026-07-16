#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from feedback_utils import normalize_scalar, parse_frontmatter, quoted_yaml_string, resolve_feedback_path, write_feedback
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


def quote_for_shell(parts: list[str]) -> str:
    return shlex.join(parts)


def safe_feedback_slug(value: object) -> str:
    raw = str(value or "").strip()
    if not raw or "/" in raw or "\\" in raw or ".." in raw:
        return "issue"
    text = raw.lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    text = text.strip("-.")
    return text or "issue"


def draft_body_filename(payload: dict[str, object]) -> str:
    feedback_id = safe_feedback_slug(payload.get("feedback_id"))
    source_stem = safe_feedback_slug(Path(str(payload.get("source_feedback_path") or "issue")).stem)
    if feedback_id == "issue":
        return f"{source_stem}-github-issue-body.md"
    return f"{feedback_id}-{source_stem}-github-issue-body.md"


def replace_body_file_argument(command: list[str], body_file: str) -> list[str]:
    updated = list(command)
    for index, part in enumerate(updated[:-1]):
        if part == "--body-file":
            updated[index + 1] = body_file
            return updated
    raise ValueError("Missing --body-file argument")


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


def existing_issue_link(frontmatter: dict[str, str]) -> tuple[str, str]:
    issue_url = normalize_scalar(str(frontmatter.get("github_issue_url", "")))
    issue_number = normalize_scalar(str(frontmatter.get("github_issue_number", "")))
    return issue_url, issue_number


def emit_result(payload: dict[str, object], *, as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if payload.get("blocked_reason") == "privacy-warnings":
            print("Publishing blocked due to privacy warnings.")
            print(payload.get("next_step", "Review the draft body before retrying."))
            if payload.get("body_path"):
                print(f"Draft body: {payload['body_path']}")
        elif "gh_command" in payload:
            print(payload["gh_command"])
        elif "issue_url" in payload:
            print(payload["issue_url"])
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def available_repo_labels(github_repo: str) -> set[str]:
    if not gh_available() or not gh_authenticated():
        return set()
    result = subprocess.run(
        ["gh", "label", "list", "--repo", github_repo, "--limit", "200", "--json", "name"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return set()
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return set()
    return {str(item.get("name", "")).strip() for item in payload if str(item.get("name", "")).strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a student-os feedback item to GitHub Issues when gh is available.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("feedback", help="Feedback path, relative to repo or absolute")
    parser.add_argument("--github-repo", default="Gu-Heping/college-student-workflow", help="GitHub repo slug for issue creation")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    parser.add_argument(
        "--allow-privacy-warnings",
        action="store_true",
        help="Allow direct publishing even when prepare_github_issue.py reports privacy warnings.",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    feedback_path = resolve_feedback_path(repo, args.feedback)
    frontmatter, _ = parse_frontmatter(feedback_path)
    if not frontmatter:
        raise SystemExit(f"Feedback entry is missing frontmatter: {feedback_path}")
    existing_url, existing_number = existing_issue_link(frontmatter)
    if existing_url or existing_number:
        return emit_result(
            {
                "published": False,
                "blocked_reason": "already-linked",
                "existing_issue_url": existing_url,
                "existing_issue_number": existing_number,
                "source_feedback_path": str(feedback_path.relative_to(repo)).replace("\\", "/"),
                "next_step": "Reuse the linked issue or clear the GitHub issue metadata before retrying.",
            },
            as_json=args.json,
        )
    payload = prepare_payload(repo, args.feedback)
    requested_labels = [str(label) for label in payload["labels"]]
    known_labels = available_repo_labels(args.github_repo)
    labels = [label for label in requested_labels if label in known_labels] if known_labels else []
    omitted_labels = [label for label in requested_labels if label not in labels]
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

    def emit_draft(*, blocked_reason: str, next_step: str) -> int:
        temp_body = repo / "feedback" / "summaries" / draft_body_filename(payload)
        temp_body.parent.mkdir(parents=True, exist_ok=True)
        temp_body.write_text(str(payload["body"]), encoding="utf-8", newline="\n")
        ready_command = quote_for_shell(replace_body_file_argument(command, str(temp_body)))
        return emit_result(
            {
                "published": False,
                "blocked_reason": blocked_reason,
                "feedback_id": payload["feedback_id"],
                "source_feedback_path": payload["source_feedback_path"],
                "gh_command": ready_command,
                "body_path": str(temp_body.relative_to(repo)).replace("\\", "/"),
                "privacy_warnings": payload["privacy_warnings"],
                "omitted_labels": omitted_labels,
                "next_step": next_step,
            },
            as_json=args.json,
        )

    if payload["privacy_warnings"] and not args.allow_privacy_warnings:
        return emit_draft(
            blocked_reason="privacy-warnings",
            next_step="Review the redactions and rerun with --allow-privacy-warnings only after explicit user confirmation.",
        )

    if not gh_available() or not gh_authenticated():
        return emit_draft(
            blocked_reason="gh-unavailable",
            next_step="Authenticate gh or run the shell-safe fallback command after reviewing the draft body.",
        )

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(str(payload["body"]))
        temp_path = Path(handle.name)
    try:
        actual_command = replace_body_file_argument(command, str(temp_path))
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
        "omitted_labels": omitted_labels,
    }
    return emit_result(output, as_json=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
