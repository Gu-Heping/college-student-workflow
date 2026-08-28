#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

from import_governance import diagnose_import_risks
from repair_import_case import (
    PROPOSAL_SCHEMA_VERSION,
    SECTION_REPLACEMENT_END,
    apply_proposal,
    build_case_payload,
    detect_line_ending,
    file_sha256,
    json_path,
    line_ending_name,
    normalize_line_endings,
    prepare_evidence,
    render_case,
    safe_state_id,
    write_case,
    write_case_json,
)
from repair_import_queue import (
    BLOCKING_RISKS,
    build_queue,
    compact_queue_payload,
    write_compact_queue,
    write_queue,
)
from repair_import_review import review_proposal


SCHEMA_VERSION = "import-repair-run/v1"
DIRECT_REPAIR_CODES = {
    "obsidian-inline-array-render-risk",
    "display-math-delimiter-not-standalone",
}


def configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
        sys.stderr.reconfigure(encoding="utf-8", newline="\n")
    except AttributeError:
        pass


def result(payload: dict[str, object], *, json_output: bool) -> int:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload.get("error") or payload.get("message") or json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("ok") else 1


def normalized_lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def transform_inline_array_line(line: str) -> list[str] | None:
    matches = list(
        re.finditer(
            r"(?<!\\)\$(?P<body>[^$\n]*(?:\\begin\{(?:array|matrix|[pbvBV]?matrix)\})[^$\n]*)(?<!\\)\$",
            line,
        )
    )
    if not matches:
        return None
    first = matches[0]
    last = matches[-1]
    before = line[: first.start()].rstrip()
    body = line[first.start() + 1 : last.end() - 1].strip()
    after = line[last.end() :].lstrip()
    if not body:
        return None
    output: list[str] = []
    if before:
        output.append(before)
        output.append("")
    output.extend(["$$", body, "$$"])
    if after:
        output.extend(["", after])
    return output


def transform_display_delimiter_line(line: str) -> list[str] | None:
    if "$$" not in line:
        return None
    parts = line.split("$$")
    if len(parts) < 2:
        return None
    output: list[str] = []
    changed = False
    for index, part in enumerate(parts):
        text = part.strip()
        if text:
            output.append(text)
        if index < len(parts) - 1:
            if text or (index + 1 < len(parts) and parts[index + 1].strip()):
                changed = True
            output.append("$$")
    cleaned: list[str] = []
    for line_item in output:
        if cleaned and line_item and cleaned[-1] not in {"", "$$"} and line_item != "$$":
            cleaned.append("")
        cleaned.append(line_item)
    return cleaned if changed else None


def repair_section_text(section_text: str) -> tuple[str, list[dict[str, object]]]:
    output: list[str] = []
    changes: list[dict[str, object]] = []
    for offset, line in enumerate(normalized_lines(section_text), start=1):
        replacement = transform_inline_array_line(line)
        code = "obsidian-inline-array-render-risk"
        if replacement is None:
            replacement = transform_display_delimiter_line(line)
            code = "display-math-delimiter-not-standalone"
        if replacement is None:
            output.append(line)
            continue
        output.extend(replacement)
        changes.append({"line_offset": offset, "code": code, "action": "localized-display-math-repair"})
    return "\n".join(output).rstrip("\n") + "\n", changes


def section_text_for_item(target_text: str, item: dict[str, object]) -> tuple[str, str] | None:
    section = item.get("target_section") if isinstance(item.get("target_section"), dict) else {}
    selector = str(section.get("id") or "")
    start = section.get("start_line")
    end = section.get("end_line")
    if selector and isinstance(start, int) and isinstance(end, int):
        lines = normalized_lines(target_text)
        return selector, "\n".join(lines[start - 1 : end]) + "\n"
    lines = item.get("blocking_risk_lines")
    if isinstance(lines, list) and lines and isinstance(lines[0], int):
        line = int(lines[0])
        text_lines = normalized_lines(target_text)
        if 1 <= line <= len(text_lines):
            return f"lines-{line}", text_lines[line - 1] + "\n"
    return None


def write_proposal(
    run_dir: Path,
    *,
    root: Path,
    target: Path,
    item: dict[str, object],
    case_json: Path,
    case_payload: dict[str, object],
    selector: str,
    replacement: str,
) -> Path:
    proposal_path = run_dir / "proposal.md"
    evidence_mode = str(case_payload.get("evidence", {}).get("mode", "text-only")) if isinstance(case_payload.get("evidence"), dict) else "text-only"
    text = "\n".join(
        [
            "# Student OS Direct Import Repair",
            "",
            "Deterministic localized repair generated by repair_import_run.py.",
            "",
            f"<!-- student-os-proposal-schema: {PROPOSAL_SCHEMA_VERSION} -->",
            f"<!-- student-os-target: {json_path(target)} -->",
            f"<!-- student-os-target-sha256: {item.get('content_sha256') or file_sha256(target)} -->",
            f"<!-- student-os-case-json: {json_path(case_json)} -->",
            f"<!-- student-os-case-sha256: {case_payload.get('case_sha256')} -->",
            f"<!-- student-os-evidence-sha256: {case_payload.get('evidence_sha256')} -->",
            f"<!-- student-os-evidence-mode: {evidence_mode} -->",
            "<!-- student-os-model-capability: text-only -->",
            f"<!-- student-os-changed-sections: {selector} -->",
            "<!-- student-os-remaining-risks: human-review-required -->",
            "",
            f"<!-- student-os-section-replacement-start: {selector} -->",
            replacement.rstrip("\n"),
            SECTION_REPLACEMENT_END,
            "",
        ]
    )
    proposal_path.write_text(text, encoding="utf-8", newline="\n")
    return proposal_path


def blocking_codes(text: str) -> set[str]:
    return {str(risk.get("code", "")) for risk in diagnose_import_risks(text)} & BLOCKING_RISKS


def run_one(target_root: Path, *, dry_run: bool, allow_widened: bool) -> dict[str, object]:
    queue = build_queue(target_root)
    write_queue(queue)
    compact = compact_queue_payload(queue, limit=1)
    write_compact_queue(compact)
    item = compact.get("recommended_item") if isinstance(compact.get("recommended_item"), dict) else {}
    if not item:
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "stage": "queue",
            "error": "No repair queue item was found.",
            "rolled_back": False,
            "recommended_next_action": "Narrow the target folder or run repair_import_queue.py --full-json to inspect nonblocking items.",
        }
    if item.get("single_section_candidate") is not True:
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "stage": "queue",
            "error": "Recommended item requires widened or blocked handling; direct run v1 only edits one local section.",
            "item_id": item.get("id", ""),
            "target": item.get("path", ""),
            "repair_scope_required": item.get("repair_scope_required", ""),
            "allow_widened_requested": allow_widened,
            "rolled_back": False,
            "queue": compact,
            "recommended_next_action": "Use the case/proposal flow, or narrow the target to one affected section.",
        }
    primary = item.get("primary_risk") if isinstance(item.get("primary_risk"), dict) else {}
    if str(primary.get("code", "")) not in DIRECT_REPAIR_CODES:
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "stage": "plan",
            "error": "Recommended item is not a deterministic direct-render repair.",
            "item_id": item.get("id", ""),
            "target": item.get("path", ""),
            "primary_risk": primary,
            "rolled_back": False,
            "recommended_next_action": "Generate a case/proposal for semantic or evidence-dependent repair.",
        }

    root = Path(str(queue.get("target_root"))).resolve()
    full_item = next((candidate for candidate in queue["items"] if isinstance(candidate, dict) and candidate.get("id") == item.get("id")), item)
    target = Path(str(full_item.get("path"))).resolve()
    original = target.read_text(encoding="utf-8", errors="replace")
    selected = section_text_for_item(original, full_item)
    if selected is None:
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "stage": "plan",
            "error": "Could not locate a local section for the recommended item.",
            "item_id": item.get("id", ""),
            "target": json_path(target),
            "rolled_back": False,
            "recommended_next_action": "Use repair_import_case.py to create a manual case.",
        }
    selector, section_text = selected
    replacement, changes = repair_section_text(section_text)
    if not changes:
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "stage": "plan",
            "error": "No deterministic local render repair was available for the selected section.",
            "item_id": item.get("id", ""),
            "target": json_path(target),
            "rolled_back": False,
            "recommended_next_action": "Use the case/proposal flow for this item.",
        }

    run_id = f"{safe_state_id(full_item, target)}-{time.time_ns()}"
    run_dir = root / ".student-os" / "import-repair" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    before_path = run_dir / "before.md"
    before_path.write_text(original, encoding="utf-8", newline="")
    evidence_payload = prepare_evidence(root, full_item, evidence_mode="text-only")
    case_json = write_case_json(root, full_item, evidence_payload)
    case_payload = build_case_payload(full_item, evidence_payload)
    case_path = write_case(root, full_item, render_case(root, full_item, target, evidence_payload))
    proposal_path = write_proposal(
        run_dir,
        root=root,
        target=target,
        item=full_item,
        case_json=case_json,
        case_payload=case_payload,
        selector=selector,
        replacement=replacement,
    )
    review = review_proposal(proposal_path, target=target)
    review_path = run_dir / "review.json"
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    before_line_ending = detect_line_ending(target)
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "ok": False,
        "stage": "dry-run" if dry_run else "review",
        "target": json_path(target),
        "item_id": full_item.get("id", ""),
        "action": "direct-localized-render-repair",
        "changed_ranges": [{"selector": selector, **change} for change in changes],
        "run_dir": json_path(run_dir),
        "before": json_path(before_path),
        "case_path": json_path(case_path),
        "case_json": json_path(case_json),
        "proposal": json_path(proposal_path),
        "review_path": json_path(review_path),
        "review": review,
        "review_pass": bool(review.get("review_pass")),
        "rolled_back": False,
        "verify_status": "unverified",
    }
    if dry_run:
        payload["ok"] = True
        payload["message"] = "Dry run prepared a deterministic repair proposal; target was not modified."
        (run_dir / "run.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        return payload
    if not review.get("review_pass"):
        payload["error"] = "Generated direct repair did not pass review."
        payload["recommended_next_action"] = review.get("recommended_next_action", "Use the case/proposal flow.")
        (run_dir / "run.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        return payload

    try:
        written = apply_proposal(proposal_path, target, None, evidence_mode="text-only")
        after_text = written.read_text(encoding="utf-8", errors="replace")
        remaining_blocking = blocking_codes(after_text)
        if remaining_blocking:
            shutil.copyfile(before_path, target)
            normalized = normalize_line_endings(target.read_text(encoding="utf-8", errors="replace"), before_line_ending)
            target.write_text(normalized, encoding="utf-8", newline="")
            payload.update(
                {
                    "ok": False,
                    "stage": "post-review",
                    "error": "Direct repair left blocking diagnostics after apply; restored the original file.",
                    "remaining_blocking": sorted(remaining_blocking),
                    "rolled_back": True,
                    "recommended_next_action": "Use the case/proposal flow or narrow the target section.",
                }
            )
        else:
            after_line_ending = detect_line_ending(written)
            payload.update(
                {
                    "ok": True,
                    "stage": "complete",
                    "applied": True,
                    "output": json_path(written),
                    "rolled_back": False,
                    "repair_status": "auto-repaired",
                    "line_ending_before": line_ending_name(before_line_ending),
                    "line_ending_after": line_ending_name(after_line_ending),
                    "line_ending_preserved": before_line_ending == after_line_ending,
                    "paragraph_boundaries_preserved": bool(review.get("paragraph_boundaries_preserved", True)),
                    "post_apply_direct_edit_allowed": False,
                    "recommended_next_action": "Inspect the rendered Markdown. If another defect appears, rerun repair_import_run.py or create a follow-up proposal.",
                }
            )
    except Exception as exc:
        shutil.copyfile(before_path, target)
        payload.update(
            {
                "ok": False,
                "stage": "apply",
                "error": str(exc),
                "rolled_back": True,
                "recommended_next_action": "Inspect run artifacts and retry with the case/proposal flow.",
            }
        )
    (run_dir / "run.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return payload


def main() -> int:
    configure_stdout()
    parser = argparse.ArgumentParser(description="Run one direct Student OS import repair with review and rollback.")
    parser.add_argument("target", help="Learning vault, folder, or markdown sidecar to scan")
    parser.add_argument("--limit", type=int, default=1, help="Maximum repairs to apply. v1 supports only 1.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare artifacts and review without modifying the target")
    parser.add_argument("--allow-widened", action="store_true", help="Reserved for future widened deterministic repairs; v1 still blocks them")
    parser.add_argument("--json", action="store_true", help="Print structured JSON")
    args = parser.parse_args()

    if args.limit != 1:
        return result(
            {
                "schema_version": SCHEMA_VERSION,
                "ok": False,
                "stage": "args",
                "error": "repair_import_run.py v1 supports only --limit 1.",
                "rolled_back": False,
                "recommended_next_action": "Run the command repeatedly for multiple repairs.",
            },
            json_output=args.json,
        )
    target = Path(args.target).expanduser().resolve()
    if not target.exists():
        return result(
            {
                "schema_version": SCHEMA_VERSION,
                "ok": False,
                "stage": "resolve-target",
                "error": "Target path does not exist.",
                "target": json_path(target),
                "rolled_back": False,
            },
            json_output=args.json,
        )
    payload = run_one(target, dry_run=args.dry_run, allow_widened=args.allow_widened)
    return result(payload, json_output=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
