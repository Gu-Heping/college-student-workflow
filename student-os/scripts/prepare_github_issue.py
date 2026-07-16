#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from feedback_utils import extract_title, normalize_scalar, parse_frontmatter, resolve_feedback_path


DEFAULT_LABEL = "feedback"
WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\[^\r\n`]+")
UNIX_PATH_RE = re.compile(r"(?:(?<=\s)|^)/(?:Users|home|var|tmp|opt|srv|mnt)/[^\r\n`]+")
TOKEN_RE = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9][A-Za-z0-9\-]{19,}|AIza[0-9A-Za-z\-_]{20,})"
)
VAULT_PATH_RE = re.compile(r"(?i)(?:[A-Za-z]:\\|/)[^\s`]*(?:vault)[^\s`]*")
ENV_FILE_RE = re.compile(r"(?im)(?<![A-Za-z0-9_.-])\.env(?:\.[A-Za-z0-9_.-]+)*(?::[^\r\n]*)?")
SECRET_KV_RE = re.compile(
    r"(?im)\b(?:token|password|secret|api[_-]?key|access[_-]?key|database_url)\b\s*[:=]\s*(?:\"[^\r\n\"]*\"|'[^\r\n']*'|[^\r\n`]+)"
)
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
PHONE_RE = re.compile(
    r"(?:(?<!\w)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})(?!\w)|(?<!\d)1[3-9]\d{9}(?!\d))"
)
EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}\b")
PRIVATE_IP_RE = re.compile(r"\b(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b")
INTERNAL_HOST_RE = re.compile(r"\b(?:[A-Za-z0-9-]+\.)+(?:local|lan|internal|corp)\b", re.IGNORECASE)
COURSE_SEMESTER_RE = re.compile(r"\b(?:20\d{2}\s*(?:spring|summer|fall|winter)|freshman|sophomore|junior|senior|semester)\b", re.IGNORECASE)
FILE_COUNT_RE = re.compile(r"\b\d{2,5}\s+(?:files?|pdfs?|docx|pptx|images?)\b", re.IGNORECASE)
LOCAL_FILE_HINT_RE = re.compile(r"(?im)(?:^|\s)(?:[A-Za-z]:\\|/)(?:Users|home|var|tmp|opt|srv|mnt)/[^\r\n`]+")


def extract_section(body: str, heading: str) -> str:
    lines = body.replace("\r\n", "\n").splitlines()
    marker = f"## {heading}"
    start = None
    for index, line in enumerate(lines):
        if line.strip() == marker:
            start = index + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def detect_privacy_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    if WINDOWS_PATH_RE.search(text):
        warnings.append("Contains Windows absolute paths; redact user-specific local paths before public posting.")
    if UNIX_PATH_RE.search(text):
        warnings.append("Contains Unix-style absolute paths; redact user-specific local paths before public posting.")
    if ".env" in text.lower():
        warnings.append("Mentions .env or environment files; verify no secrets or private configuration are included.")
    if TOKEN_RE.search(text):
        warnings.append("Contains token-like strings; remove secrets before posting publicly.")
    if SECRET_KV_RE.search(text):
        warnings.append("Contains secret-like key/value pairs; remove credentials before posting publicly.")
    lowered = text.lower()
    if "\\vault" in lowered or "/vault" in lowered or "d:\\vault" in lowered:
        warnings.append("References a private vault path; redact private repository or note locations before posting.")
    if EMAIL_RE.search(text):
        warnings.append("Contains email addresses; replace personal addresses before public posting.")
    if PRIVATE_IP_RE.search(text):
        warnings.append("Contains private network IP addresses; replace internal infrastructure details before public posting.")
    if INTERNAL_HOST_RE.search(text):
        warnings.append("Contains internal hostnames or domains; replace internal network references before public posting.")
    if FILE_COUNT_RE.search(text):
        warnings.append("Contains file-count or dataset-size details; consider generalizing counts or ranges for public reports.")
    if COURSE_SEMESTER_RE.search(text):
        warnings.append("Contains semester or academic-stage details; consider generalizing study metadata for public reports.")
    if LOCAL_FILE_HINT_RE.search(text):
        warnings.append("References local files developers cannot access; inline the relevant snippet or remove the path.")
    return warnings


def detect_privacy_blockers(text: str) -> list[str]:
    blockers: list[str] = []
    if JWT_RE.search(text):
        blockers.append("Contains JWT-like tokens; remove credentials before publishing.")
    if SECRET_KV_RE.search(text):
        blockers.append("Contains secret-like key/value assignments; remove credentials before publishing.")
    if PHONE_RE.search(text):
        blockers.append("Contains phone-number-like personal data; remove personal contact details before publishing.")
    return blockers


def redact_sensitive_text(text: str) -> str:
    redacted = WINDOWS_PATH_RE.sub("[REDACTED_WINDOWS_PATH]", text)
    redacted = UNIX_PATH_RE.sub("[REDACTED_UNIX_PATH]", redacted)
    redacted = TOKEN_RE.sub("[REDACTED_TOKEN]", redacted)
    redacted = JWT_RE.sub("[REDACTED_JWT]", redacted)
    redacted = PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    redacted = VAULT_PATH_RE.sub("[REDACTED_VAULT_PATH]", redacted)
    redacted = ENV_FILE_RE.sub("[REDACTED_ENV_FILE]", redacted)
    redacted = SECRET_KV_RE.sub("[REDACTED_SECRET_KV]", redacted)
    redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", redacted)
    redacted = PRIVATE_IP_RE.sub("[REDACTED_PRIVATE_IP]", redacted)
    redacted = INTERNAL_HOST_RE.sub("[REDACTED_INTERNAL_HOST]", redacted)
    return redacted


def public_feedback_id(frontmatter: dict[str, str], feedback_path: Path) -> str:
    created = normalize_scalar(frontmatter.get("created", "")) or "unknown"
    compact = re.sub(r"[^0-9]", "", created)[:8] or "unknown"
    source = normalize_scalar(frontmatter.get("feedback_id", "")) or feedback_path.as_posix()
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:8]
    return f"fb-public-{compact}-{digest}"


def likely_area(frontmatter: dict[str, str]) -> str:
    kind = normalize_scalar(frontmatter.get("feedback_kind", "other")) or "other"
    return {
        "workflow": "workflow and orchestration",
        "template": "templates and generated artifact structure",
        "routing": "routing and companion selection",
        "import": "document import pipeline",
        "git": "git workflow and change grouping",
        "quality": "output quality and result shaping",
        "docs": "documentation and usage guidance",
        "course-pack": "course packs and specialization rules",
        "install": "installation and self-update workflow",
        "other": "general student-os behavior",
    }.get(kind, "general student-os behavior")


def issue_labels(frontmatter: dict[str, str]) -> list[str]:
    kind = normalize_scalar(frontmatter.get("feedback_kind", "other")) or "other"
    severity = normalize_scalar(frontmatter.get("severity", "medium")) or "medium"
    return [DEFAULT_LABEL, f"feedback:{kind}", f"severity:{severity}"]


def build_issue_title(frontmatter: dict[str, str], feedback_path: Path, body: str) -> str:
    title = public_feedback_id(frontmatter, feedback_path)
    body_title = redact_sensitive_text(extract_title(body) or feedback_path.stem.replace("-", " "))
    return f"{title}: {body_title}"


def infer_installed_version(frontmatter: dict[str, str], body: str) -> str:
    fix_version = normalize_scalar(frontmatter.get("fix_version", ""))
    if fix_version:
        return redact_sensitive_text(fix_version)
    source_context = normalize_scalar(frontmatter.get("source_context", ""))
    match = re.search(r"(installed(?: version)?|version)[: ]+([^\s,;]+)", source_context + "\n" + body, flags=re.IGNORECASE)
    return redact_sensitive_text(match.group(2)) if match else "unknown"


def infer_agent_runtime(frontmatter: dict[str, str], body: str) -> str:
    related_roles = normalize_scalar(frontmatter.get("related_roles", ""))
    source_context = normalize_scalar(frontmatter.get("source_context", ""))
    text = "\n".join([related_roles, source_context, body]).lower()
    for runtime in ["codex", "claude code", "claude", "opencode"]:
        if runtime in text:
            return runtime
    return "unknown"


def infer_os(frontmatter: dict[str, str], body: str) -> str:
    source_context = normalize_scalar(frontmatter.get("source_context", ""))
    text = "\n".join([source_context, body]).lower()
    if "windows" in text:
        return "Windows"
    if "macos" in text or "darwin" in text or "os x" in text:
        return "macOS"
    if "linux" in text or "/home/" in text:
        return "Linux"
    return "unknown"


def infer_python_version(frontmatter: dict[str, str], body: str) -> str:
    source_context = normalize_scalar(frontmatter.get("source_context", ""))
    text = "\n".join([source_context, body])
    match = re.search(r"\bpython(?: version)?[: ]+([0-9]+(?:\.[0-9]+){1,2})\b", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"\bpy(?:thon)?\s*([0-9]+(?:\.[0-9]+){1,2})\b", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return "unknown"


def detect_completeness_warnings(frontmatter: dict[str, str], body: str) -> list[str]:
    warnings: list[str] = []
    what_happened = extract_section(body, "What Happened")
    expected_behavior = extract_section(body, "Expected Behavior")
    evidence = extract_section(body, "Evidence")
    likely_cause = extract_section(body, "Likely Cause")
    suggested_improvement = extract_section(body, "Suggested Improvement")
    source_context = normalize_scalar(frontmatter.get("source_context", ""))

    if not what_happened.strip() or what_happened.strip() == "-":
        warnings.append("Missing a concrete problem description; add one sentence describing what broke.")
    if not expected_behavior.strip() or expected_behavior.strip() == "-":
        warnings.append("Missing expected behavior; add a clear actual-vs-expected comparison.")
    if not evidence.strip() or evidence.strip() == "-":
        warnings.append("Missing evidence or repro data; add logs, snippets, or a minimal failing example.")
    if not source_context.strip() or source_context.strip().lower() == "unknown":
        warnings.append("Missing reproduction context; add a self-contained reproduction path developers can follow.")
    if not likely_cause.strip() or likely_cause.strip() == "-":
        warnings.append("Likely cause is missing; include a suspected area when available to speed triage.")
    if not suggested_improvement.strip() or suggested_improvement.strip() == "-":
        warnings.append("Suggested improvement is missing; add a fix direction or note that none is known.")
    if "..." in evidence or "..." in what_happened:
        warnings.append("Contains ellipsis-truncated content; inline complete commands or snippets when they are needed for reproduction.")
    return warnings


def build_issue_body(
    feedback_path: Path,
    frontmatter: dict[str, str],
    body: str,
    warnings: list[str],
    blockers: list[str],
    completeness_warnings: list[str],
) -> str:
    display_feedback_id = public_feedback_id(frontmatter, feedback_path)
    display_feedback_path = redact_sensitive_text(feedback_path.name)
    what_happened = redact_sensitive_text(extract_section(body, "What Happened") or "- ")
    expected_behavior = redact_sensitive_text(extract_section(body, "Expected Behavior") or "- ")
    evidence = redact_sensitive_text(extract_section(body, "Evidence") or "- ")
    likely_cause = redact_sensitive_text(extract_section(body, "Likely Cause") or "- ")
    suggested_improvement = redact_sensitive_text(extract_section(body, "Suggested Improvement") or "- ")
    developer_summary = redact_sensitive_text(extract_section(body, "Developer Summary") or "- ")
    source_context = redact_sensitive_text(normalize_scalar(frontmatter.get("source_context", "")) or "unknown")
    severity = normalize_scalar(frontmatter.get("severity", "medium")) or "medium"
    privacy_lines = blockers + warnings or ["No obvious privacy warnings detected."]
    completeness_lines = completeness_warnings or ["Minimum issue sections detected for public triage."]
    issue_lines = [
        "## Feedback ID",
        "",
        f"- `{display_feedback_id}`",
        f"- Source Feedback: `{display_feedback_path}`",
        "",
        "## Installed Version",
        "",
        f"- {infer_installed_version(frontmatter, body)}",
        "",
        "## Agent Runtime",
        "",
        f"- {infer_agent_runtime(frontmatter, body)}",
        "",
        "## Environment",
        "",
        f"- OS: {infer_os(frontmatter, body)}",
        f"- Python: {infer_python_version(frontmatter, body)}",
        "",
        "## What Happened",
        "",
        what_happened,
        "",
        "## Expected Behavior",
        "",
        expected_behavior,
        "",
        "## Evidence",
        "",
        evidence,
        "",
        "## Reproduction Steps",
        "",
        f"- Source context: {source_context}",
        "- Follow the workflow described in the linked feedback entry.",
        "- Observe the mismatch between actual and expected behavior.",
        "",
        "## Likely Area",
        "",
        f"- {likely_area(frontmatter)}",
        "",
        "## Severity",
        "",
        f"- {severity}",
        "",
        "## Privacy Check",
        "",
    ]
    for warning in privacy_lines:
        issue_lines.append(f"- {warning}")
    issue_lines.extend(
        [
            "",
            "## Completeness Check",
            "",
        ]
    )
    for warning in completeness_lines:
        issue_lines.append(f"- {warning}")
    issue_lines.extend(
        [
            "",
            "## Suggested Improvement",
            "",
            suggested_improvement,
            "",
            "## Developer Summary",
            "",
            developer_summary,
            "",
            "## Likely Cause",
            "",
            likely_cause,
            "",
        ]
    )
    return "\n".join(issue_lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a GitHub issue draft from a student-os feedback entry.")
    parser.add_argument("repo", help="Target repository root")
    parser.add_argument("feedback", help="Feedback path, relative to repo or absolute")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    feedback_path = resolve_feedback_path(repo, args.feedback)
    if not feedback_path.exists():
        raise SystemExit(f"Feedback entry not found: {feedback_path}")

    frontmatter, body = parse_frontmatter(feedback_path)
    if not frontmatter:
        raise SystemExit(f"Feedback entry is missing frontmatter: {feedback_path}")

    privacy_scan_text = "\n".join(
        [
            body,
            normalize_scalar(frontmatter.get("source_context", "")),
            normalize_scalar(frontmatter.get("related_artifacts", "")),
        ]
    )
    warnings = detect_privacy_warnings(privacy_scan_text)
    blockers = detect_privacy_blockers(privacy_scan_text)
    completeness_warnings = detect_completeness_warnings(frontmatter, body)
    payload = {
        "title": build_issue_title(frontmatter, feedback_path, body),
        "body": build_issue_body(
            feedback_path.relative_to(repo),
            frontmatter,
            body,
            warnings,
            blockers,
            completeness_warnings,
        ),
        "labels": issue_labels(frontmatter),
        "feedback_id": normalize_scalar(frontmatter.get("feedback_id", "")),
        "source_feedback_path": feedback_path.relative_to(repo).as_posix(),
        "privacy_warnings": warnings,
        "privacy_blockers": blockers,
        "completeness_warnings": completeness_warnings,
        "sanitized": True,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
