#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from import_governance import (
    diagnose_import_risks,
    frontmatter_value,
    is_verified,
    mark_auto_repaired,
)
from repair_import_queue import BLOCKING_RISKS, build_queue_item, is_relative_to, is_repair_target_markdown, iter_import_markdown, json_path, state_root_for_scan


SCHEMA_VERSION = "import-repair-check/v1"
EOL_POLICY = "student-os-markdown-lf"


def configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
        sys.stderr.reconfigure(encoding="utf-8", newline="\n")
    except AttributeError:
        pass


def read_markdown(path: Path) -> tuple[str, bool]:
    try:
        return path.read_text(encoding="utf-8"), False
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace"), True


def detect_eol(path: Path) -> str:
    data = path.read_bytes() if path.exists() else b""
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    cr = data.count(b"\r") - crlf
    kinds = sum(1 for count in (crlf, lf, cr) if count > 0)
    if kinds > 1:
        return "mixed"
    if crlf:
        return "crlf"
    if cr:
        return "cr"
    return "lf"


def risk_lines(risk: dict[str, object]) -> list[int]:
    lines: list[int] = []
    line = risk.get("line")
    if isinstance(line, int):
        lines.append(line)
    nested = risk.get("lines")
    if isinstance(nested, list):
        for value in nested:
            if isinstance(value, int):
                lines.append(value)
            elif isinstance(value, dict) and isinstance(value.get("line"), int):
                lines.append(int(value["line"]))
    return sorted(set(lines))


def risk_count(risk: dict[str, object], lines: list[int]) -> int:
    count = risk.get("count")
    if isinstance(count, int) and count > 0:
        return count
    return max(1, len(lines))


def first_excerpt(text: str, lines: list[int]) -> str:
    if not lines:
        return ""
    text_lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    line = lines[0]
    if 1 <= line <= len(text_lines):
        return text_lines[line - 1].strip()[:240]
    return ""


def focus_line_set(values: list[str]) -> set[int]:
    selected: set[int] = set()
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            match = part.replace("..", "-")
            if "-" in match:
                start_text, end_text = match.split("-", 1)
                start = int(start_text)
                end = int(end_text)
                if end < start:
                    start, end = end, start
                selected.update(range(start, end + 1))
            else:
                selected.add(int(match))
    return selected


def issue_fingerprint(issue: dict[str, object]) -> str:
    payload = {
        "code": issue.get("code", ""),
        "lines": issue.get("lines", []),
        "excerpt": issue.get("first_excerpt", ""),
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def baseline_issues(payload: dict[str, object]) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    for file_result in payload.get("files", []):
        if not isinstance(file_result, dict):
            continue
        for issue in file_result.get("blocking_errors", []):
            if isinstance(issue, dict):
                issues.append(issue)
    return issues


def evidence_mode_for(path: Path, text: str) -> str:
    if frontmatter_value(text, "repair_evidence_mode"):
        return frontmatter_value(text, "repair_evidence_mode")
    if frontmatter_value(text, "derived_from_import"):
        return "text-grounded"
    if frontmatter_value(text, "source_file"):
        source = frontmatter_value(text, "source_file").lower()
        if source.endswith(".pdf"):
            return "pdf-declared"
    return "evidence-missing"


def relative_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix() if is_relative_to(path, root) else json_path(path)


def check_file(path: Path, *, root: Path, include_verified: bool, focus_lines: set[int] | None = None) -> dict[str, object]:
    text, decode_error = read_markdown(path)
    eol = detect_eol(path)
    verified = is_verified(text)
    if verified and not include_verified:
        return {
            "path": json_path(path),
            "relative_path": relative_path(root, path),
            "ok": False,
            "skipped": True,
            "stage": "verified-skip",
            "blocking_errors": [
                {
                    "code": "verified-file-protected",
                    "severity": "error",
                    "message": "verify_status: verified files are skipped by default; pass --include-verified only when the user explicitly asks to recheck verified material.",
                }
            ],
            "warnings": [],
            "evidence_mode": evidence_mode_for(path, text),
            "line_ending": eol,
            "eol_policy": EOL_POLICY,
            "recommended_next_action": "Do not edit this file unless the user explicitly authorizes verified material changes.",
        }
    item = build_queue_item(root, path, text=text, decode_error=decode_error)
    risks = item.get("risks", []) if isinstance(item, dict) else diagnose_import_risks(text)
    risk_objects = [risk for risk in risks if isinstance(risk, dict)]
    blocking = []
    for risk in risk_objects:
        if str(risk.get("code", "")) not in BLOCKING_RISKS:
            continue
        lines = risk_lines(risk)
        issue = {
            "code": risk.get("code", ""),
            "severity": "error",
            "count": risk_count(risk, lines),
            "lines": lines,
            "first_excerpt": first_excerpt(text, lines),
            "message": risk.get("description", "Mechanical import repair check failed."),
            "detail": risk,
            "suggestion": risk.get("suggestion", ""),
        }
        issue["fingerprint"] = issue_fingerprint(issue)
        blocking.append(issue)
    warnings = [
        {
            "code": risk.get("code", ""),
            "severity": risk.get("severity", "warning"),
            "count": risk_count(risk, risk_lines(risk)),
            "message": risk.get("description", "Nonblocking import repair risk remains."),
            "lines": risk_lines(risk),
            "first_excerpt": first_excerpt(text, risk_lines(risk)),
            "detail": risk,
        }
        for risk in risk_objects
        if str(risk.get("code", "")) not in BLOCKING_RISKS
    ]
    protected_status_errors = []
    if frontmatter_value(text, "repair_status").lower() in {"verified", "human-verified"}:
        protected_status_errors.append(
            {
                "code": "repair-status-claimed-human-verification",
                "severity": "error",
                "count": 1,
                "message": "AI/script repair must not claim human repair status.",
                "lines": [],
                "first_excerpt": "",
            }
        )
    blocking.extend(protected_status_errors)
    focused_blocking = blocking
    out_of_focus_blocking: list[dict[str, object]] = []
    if focus_lines:
        focused_blocking = []
        for issue in blocking:
            lines = [line for line in issue.get("lines", []) if isinstance(line, int)]
            if not lines or any(line in focus_lines for line in lines):
                focused_blocking.append(issue)
            else:
                out_of_focus_blocking.append(issue)
    return {
        "path": json_path(path),
        "relative_path": relative_path(root, path),
        "ok": not focused_blocking,
        "skipped": False,
        "blocking_errors": focused_blocking,
        "out_of_focus_blocking_errors": out_of_focus_blocking,
        "out_of_focus_blocking_count": len(out_of_focus_blocking),
        "warnings": warnings,
        "evidence_mode": evidence_mode_for(path, text),
        "line_ending": eol,
        "eol_policy": EOL_POLICY,
        "repair_status": frontmatter_value(text, "repair_status"),
        "verify_status": frontmatter_value(text, "verify_status"),
        "recommended_next_action": (
            "Fix the reported local Markdown/LaTeX lines, then rerun this check."
            if blocking
            else "Mechanical review passed. Report this as review passed, not verified."
        ),
    }


def candidate_files(target: Path) -> list[Path]:
    if target.is_file():
        header = target.read_text(encoding="utf-8", errors="replace")[:65536]
        return [target] if target.suffix.lower() == ".md" and is_repair_target_markdown(target, header) else []
    return [path for path, _header in iter_import_markdown(target)]


def compact_file_result(file_result: dict[str, object], *, limit: int) -> dict[str, object]:
    blocking = [issue for issue in file_result.get("blocking_errors", []) if isinstance(issue, dict)]
    warnings = [issue for issue in file_result.get("warnings", []) if isinstance(issue, dict)]
    return {
        "path": file_result.get("path", ""),
        "relative_path": file_result.get("relative_path", ""),
        "ok": file_result.get("ok", False),
        "skipped": file_result.get("skipped", False),
        "line_ending": file_result.get("line_ending", ""),
        "eol_policy": file_result.get("eol_policy", EOL_POLICY),
        "evidence_mode": file_result.get("evidence_mode", ""),
        "repair_status": file_result.get("repair_status", ""),
        "verify_status": file_result.get("verify_status", ""),
        "blocking_error_count": len(blocking),
        "warning_count": len(warnings),
        "blocking_errors": blocking[:limit],
        "warning_sample": warnings[:limit],
        "out_of_focus_blocking_count": file_result.get("out_of_focus_blocking_count", 0),
        "recommended_next_action": file_result.get("recommended_next_action", ""),
    }


def recommended_file(file_results: list[dict[str, object]]) -> dict[str, object]:
    candidates = [item for item in file_results if not item.get("skipped")]
    if not candidates:
        return {}
    return max(
        candidates,
        key=lambda item: (
            len(item.get("blocking_errors", [])) if isinstance(item.get("blocking_errors"), list) else 0,
            len(item.get("warnings", [])) if isinstance(item.get("warnings"), list) else 0,
        ),
    )


def write_report(root: Path, payload: dict[str, object], *, kind: str) -> Path:
    report_dir = root / ".student-os" / "import-repair" / "checks"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{kind}-{time.time_ns()}.json"
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report_path


def compare_baseline(before_payload: dict[str, object], after_payload: dict[str, object]) -> dict[str, object]:
    before = {str(issue.get("fingerprint", issue_fingerprint(issue))): issue for issue in baseline_issues(before_payload)}
    after = {str(issue.get("fingerprint", issue_fingerprint(issue))): issue for issue in baseline_issues(after_payload)}
    before_keys = set(before)
    after_keys = set(after)
    return {
        "new_errors": [after[key] for key in sorted(after_keys - before_keys)],
        "cleared_errors": [before[key] for key in sorted(before_keys - after_keys)],
        "unchanged_existing_errors": [after[key] for key in sorted(after_keys & before_keys)],
        "new_error_count": len(after_keys - before_keys),
        "cleared_error_count": len(before_keys - after_keys),
        "unchanged_existing_error_count": len(after_keys & before_keys),
    }


def main() -> int:
    configure_stdout()
    parser = argparse.ArgumentParser(description="Check directly edited imported markdown for Student OS mechanical repair safety.")
    parser.add_argument("target", help="Imported markdown sidecar, folder, or learning vault to check")
    parser.add_argument("--include-verified", action="store_true", help="Check files marked verify_status: verified")
    parser.add_argument("--mark-auto-repaired", action="store_true", help="Write auto-repaired/unverified governance frontmatter before checking")
    parser.add_argument("--full-json", action="store_true", help="Print full per-file diagnostics instead of compact agent-facing JSON")
    parser.add_argument("--write-report", action="store_true", help="Write the full report under .student-os/import-repair/checks/")
    parser.add_argument("--write-baseline", action="store_true", help="Write a baseline report for later --baseline comparison")
    parser.add_argument("--baseline", help="Compare this check against a previous baseline JSON report")
    parser.add_argument("--focus-lines", action="append", default=[], help="Comma-separated lines or ranges to gate as hard errors, e.g. 143,174-180")
    parser.add_argument("--focus-range", action="append", default=[], help="Alias for --focus-lines with a single range")
    parser.add_argument("--limit", type=int, default=5, help="Maximum files/errors returned in compact JSON")
    parser.add_argument("--json", action="store_true", help="Print structured JSON")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.exists():
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "stage": "resolve-target",
            "error": "Target path does not exist.",
            "target": json_path(target),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else payload["error"])
        return 2

    root = state_root_for_scan(target)
    files = candidate_files(target)
    if not files:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "stage": "no-import-sidecar",
            "error": "No imported markdown sidecar was found at the target path.",
            "target": json_path(target),
            "target_root": json_path(root),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else payload["error"])
        return 1
    if args.mark_auto_repaired:
        for path in files:
            text = path.read_text(encoding="utf-8", errors="replace")
            if is_verified(text) and not args.include_verified:
                continue
            path.write_text(mark_auto_repaired(text, needs_review=True), encoding="utf-8", newline="\n")

    focus_lines = focus_line_set([*args.focus_lines, *args.focus_range]) if args.focus_lines or args.focus_range else None
    file_results = [check_file(path, root=root, include_verified=args.include_verified, focus_lines=focus_lines) for path in files]
    blocking_count = sum(len(item.get("blocking_errors", [])) for item in file_results)
    warning_count = sum(len(item.get("warnings", [])) for item in file_results)
    full_payload = {
        "schema_version": SCHEMA_VERSION,
        "ok": blocking_count == 0,
        "target": json_path(target),
        "target_root": json_path(root),
        "compact": False,
        "eol_policy": EOL_POLICY,
        "focus_lines": sorted(focus_lines) if focus_lines else [],
        "files_checked": len([item for item in file_results if not item.get("skipped")]),
        "files_skipped": len([item for item in file_results if item.get("skipped")]),
        "blocking_error_count": blocking_count,
        "warning_count": warning_count,
        "files": file_results,
        "review_label": "review passed" if blocking_count == 0 else "review failed",
        "verified": False,
        "recommended_next_action": (
            "Fix the blocking_errors in the reported local lines and rerun repair_import_check.py."
            if blocking_count
            else "Mechanical review passed; do not mark verified unless the user confirms human source verification."
        ),
    }
    if args.baseline:
        baseline_payload = json.loads(Path(args.baseline).expanduser().read_text(encoding="utf-8"))
        full_payload["baseline"] = json_path(Path(args.baseline).expanduser().resolve())
        full_payload["baseline_comparison"] = compare_baseline(baseline_payload, full_payload)
        comparison = full_payload["baseline_comparison"]
        if isinstance(comparison, dict) and comparison.get("new_error_count"):
            full_payload["ok"] = False
            full_payload["review_label"] = "review failed"
    report_path = None
    if args.write_report or args.write_baseline:
        report_dir = root / ".student-os" / "import-repair" / "checks"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{'baseline' if args.write_baseline else 'report'}-{time.time_ns()}.json"
        full_payload["report_path" if not args.write_baseline else "baseline_path"] = json_path(report_path)
        report_path.write_text(json.dumps(full_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if args.full_json:
        payload = full_payload
    else:
        limit = max(1, args.limit)
        recommendation = recommended_file(file_results)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ok": full_payload["ok"],
            "target": full_payload["target"],
            "target_root": full_payload["target_root"],
            "compact": True,
            "eol_policy": EOL_POLICY,
            "focus_lines": full_payload["focus_lines"],
            "files_checked": full_payload["files_checked"],
            "files_skipped": full_payload["files_skipped"],
            "blocking_error_count": blocking_count,
            "warning_count": warning_count,
            "recommended_file": compact_file_result(recommendation, limit=limit) if recommendation else {},
            "files_sample": [compact_file_result(item, limit=limit) for item in file_results[:limit]],
            "review_label": full_payload["review_label"],
            "verified": False,
            "baseline": full_payload.get("baseline", ""),
            "baseline_comparison": full_payload.get("baseline_comparison", {}),
            "baseline_path": full_payload.get("baseline_path", ""),
            "report_path": full_payload.get("report_path", ""),
            "full_report_path": json_path(report_path) if report_path is not None else "",
            "recommended_next_action": full_payload["recommended_next_action"],
        }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["review_label"])
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
