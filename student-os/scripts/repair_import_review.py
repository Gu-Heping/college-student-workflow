#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

from import_governance import diagnose_import_risks, frontmatter_value, mark_auto_repaired, read_frontmatter
from repair_import_case import SCHEMA_VERSION as CASE_SCHEMA_VERSION
from repair_import_case import (
    PROPOSAL_SCHEMA_VERSION,
    case_sha256,
    extract_replacement,
    json_path,
    load_json,
    object_sha256,
    proposal_replacement_kind,
    section_replacements,
)
from repair_import_queue import SCHEMA_VERSION as QUEUE_SCHEMA_VERSION
from repair_import_queue import decode_yaml_path, file_sha256, has_question_stem, split_sections


SCHEMA_VERSION = "import-repair-review/v1"
TARGET_RE = re.compile(r"<!--\s*student-os-target:\s*(?P<path>.*?)\s*-->")
META_RE = re.compile(r"<!--\s*student-os-(?P<key>[a-z0-9-]+):\s*(?P<value>.*?)\s*-->")
QUESTION_RE = re.compile(r"(?m)^\s*(?:#{1,3}\s*)?(?P<num>[一二三四五六七八九十]+|[0-9]+)[\.、．)]")
BLOCKING_RISK_CODES = {
    "math-dollar-odd-line",
    "latex-left-right-unbalanced",
    "latex-array-column-mismatch",
    "obsidian-inline-array-render-risk",
    "display-math-delimiter-not-standalone",
    "inline-math-delimiter-space",
}


def configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
        sys.stderr.reconfigure(encoding="utf-8", newline="\n")
    except AttributeError:
        pass


def proposal_target(proposal_path: Path, explicit_target: str | None) -> Path | None:
    if explicit_target:
        return Path(explicit_target).expanduser().resolve()
    text = proposal_path.read_text(encoding="utf-8", errors="replace")
    match = TARGET_RE.search(text)
    if match:
        candidate = Path(match.group("path").strip()).expanduser()
        return candidate.resolve()
    return None


def state_root_for(proposal_path: Path, target: Path | None) -> Path:
    for parent in [proposal_path.parent, *proposal_path.parents]:
        if parent.name == ".student-os":
            return parent.parent
    if target is not None:
        for parent in [target.parent, *target.parents]:
            if (parent / ".student-os").exists():
                return parent
    return proposal_path.parent


def state_root_from_case_json(case_json_path: Path) -> Path | None:
    for parent in [case_json_path.parent, *case_json_path.parents]:
        if parent.name == ".student-os":
            return parent.parent.resolve()
    return None


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def question_numbers(text: str) -> list[str]:
    return [match.group("num") for match in QUESTION_RE.finditer(text)]


def proposal_metadata(proposal_path: Path) -> dict[str, str]:
    text = proposal_path.read_text(encoding="utf-8", errors="replace")
    return {match.group("key"): match.group("value").strip() for match in META_RE.finditer(text)}


def markdown_body(text: str) -> str:
    parsed = read_frontmatter(text)
    if parsed is None:
        return text
    _data, _start, end = parsed
    return text[end:]


def compact_visible_text(text: str) -> str:
    body = re.sub(r"(?s)<!--.*?-->", "", markdown_body(text))
    body = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", body)
    body = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", body)
    body = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)
    body = re.sub(r"(?s)<[^>]+>", "", body)
    return re.sub(r"\s+", "", body)


def review_failure_guidance(
    issues: list[dict[str, object]],
    risk_items: list[dict[str, object]],
) -> tuple[str, str]:
    if not any(item.get("severity") == "error" for item in issues):
        return "", ""
    if any(item.get("code") in {"proposal-target-stale", "proposal-case-target-stale"} for item in issues):
        return (
            "stale-proposal",
            "Regenerate the repair queue and case for the current file content, then rebuild the proposal from that case.",
        )
    if any(item.get("code") == "proposal-scope-widened-without-authorization" for item in issues):
        return (
            "proposal-scope-widened",
            "Keep the proposal to one case section, or add student-os-repair-scope: widened only when the user explicitly authorizes a broader repair.",
        )
    if any(item.get("code") == "markdown-paragraph-boundary-regression" for item in issues):
        return (
            "markdown-paragraph-boundary-regression",
            "Preserve the blank separator before the next question; update the proposal and re-run review/apply instead of editing the target sidecar directly.",
        )
    remaining_blocking = sorted(
        {
            str(risk.get("code"))
            for risk in risk_items
            if str(risk.get("code", "")) in BLOCKING_RISK_CODES
        }
    )
    if remaining_blocking:
        return (
            "replacement-still-has-blocking-risks",
            "The replacement still has blocking diagnostics: "
            + ", ".join(remaining_blocking)
            + ". Choose a smaller queue item/section, or explicitly widen the proposal and fix every blocking risk in scope.",
        )
    if any(item.get("code") == "proposal-derived-from-scratch-fix" for item in issues):
        return (
            "scratch-fix-proposal-rejected",
            "Generate the proposal directly from the Student OS case artifact; do not wrap .fixed files or vault-local scratch outputs.",
        )
    if any(str(item.get("code", "")).startswith("text-") for item in issues):
        return (
            "insufficient-evidence-mode",
            "A text-only proposal cannot resolve vision-blocked work; create a blocked proposal or regenerate the case with stronger evidence.",
        )
    return (
        "proposal-review-failed",
        "Read the structured issue codes/messages in this JSON and update the proposal metadata or replacement; do not inspect Student OS source code unless the tool crashed.",
    )


def validate_queue_item(queue_item: dict[str, object]) -> list[dict[str, object]]:
    required_nonempty = ["schema_version", "path", "content_sha256", "recommended_evidence_mode"]
    issues: list[dict[str, object]] = []
    for key in required_nonempty:
        if not str(queue_item.get(key) or "").strip():
            issues.append(issue("proposal-case-queue-item-incomplete", f"Bound case queue_item is missing {key}.", detail={"field": key}))
    if "blocked" not in queue_item:
        issues.append(issue("proposal-case-queue-item-incomplete", "Bound case queue_item is missing blocked.", detail={"field": "blocked"}))
    return issues


def issue(code: str, message: str, *, severity: str = "error", detail: object | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"code": code, "severity": severity, "message": message}
    if detail is not None:
        payload["detail"] = detail
    return payload


def changed_line_ranges(before: str, after: str) -> list[dict[str, int]]:
    ranges: list[dict[str, int]] = []
    matcher = difflib.SequenceMatcher(a=before.splitlines(), b=after.splitlines(), autojunk=False)
    for tag, i1, i2, _j1, _j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        start = i1 + 1
        end = max(i2, i1 + 1)
        ranges.append({"start_line": start, "end_line": end})
    return ranges


def sections_for_ranges(text: str, ranges: list[dict[str, int]]) -> list[dict[str, object]]:
    sections = split_sections(text)
    selected: list[dict[str, object]] = []
    seen: set[str] = set()
    for changed in ranges:
        start = changed["start_line"]
        end = changed["end_line"]
        matched = False
        for section in sections:
            section_start = section.get("start_line")
            section_end = section.get("end_line")
            if isinstance(section_start, int) and isinstance(section_end, int) and start <= section_end and end >= section_start:
                section_id = str(section.get("id", ""))
                if section_id and section_id not in seen:
                    selected.append(
                        {
                            "id": section_id,
                            "title": section.get("title", ""),
                            "start_line": section_start,
                            "end_line": section_end,
                        }
                    )
                    seen.add(section_id)
                matched = True
        if not matched:
            key = f"lines-{start}-{end}"
            if key not in seen:
                selected.append({"id": key, "title": "", "start_line": start, "end_line": end})
                seen.add(key)
    return selected


def sections_for_selectors(text: str, selectors: list[str]) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    seen: set[str] = set()
    sections = split_sections(text)
    by_id = {str(section.get("id", "")): section for section in sections}
    for selector in selectors:
        selector = selector.strip()
        section = by_id.get(selector)
        if section is not None:
            section_id = str(section.get("id", ""))
            if section_id and section_id not in seen:
                selected.append(
                    {
                        "id": section_id,
                        "title": section.get("title", ""),
                        "start_line": section.get("start_line", 0),
                        "end_line": section.get("end_line", 0),
                    }
                )
                seen.add(section_id)
            continue
        line_match = re.fullmatch(r"(?:line|lines)[-: ](?P<start>\d+)(?:\s*(?:-|\.\.)\s*(?P<end>\d+))?", selector)
        if line_match:
            start = int(line_match.group("start"))
            end = int(line_match.group("end") or start)
            key = f"lines-{start}-{end}"
            if key not in seen:
                selected.append({"id": key, "title": "", "start_line": start, "end_line": end})
                seen.add(key)
    return selected


def declared_widened_scope(metadata: dict[str, str]) -> bool:
    scope = metadata.get("repair-scope", "").strip().lower()
    return scope in {"widened", "multi-section", "full-file"}


def risk_codes(items: list[dict[str, object]]) -> set[str]:
    return {str(item.get("code", "")) for item in items if str(item.get("code", ""))}


def question_boundary_key(line: str) -> str | None:
    stripped = line.strip()
    match = QUESTION_RE.match(stripped)
    if not match:
        return None
    return f"{match.group('num')}:{stripped[:80]}"


def markdown_paragraph_boundary_regressions(before: str, after: str) -> list[dict[str, object]]:
    before_lines = before.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    after_lines = after.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    before_separated: set[str] = set()
    for index, line in enumerate(before_lines):
        key = question_boundary_key(line)
        if key is None or index == 0:
            continue
        if before_lines[index - 1].strip() == "":
            before_separated.add(key)
    regressions: list[dict[str, object]] = []
    for index, line in enumerate(after_lines):
        key = question_boundary_key(line)
        if key is None or key not in before_separated or index == 0:
            continue
        if after_lines[index - 1].strip() != "":
            regressions.append(
                {
                    "line": index + 1,
                    "question": line.strip()[:120],
                    "previous_line": after_lines[index - 1].strip()[:120],
                }
            )
    return regressions


def review_proposal(proposal_path: Path, *, target: Path | None = None) -> dict[str, object]:
    proposal_path = proposal_path.resolve()
    resolved_target = target or proposal_target(proposal_path, None)
    issues: list[dict[str, object]] = []
    try:
        replacement = extract_replacement(proposal_path, resolved_target)
    except SystemExit as exc:
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "proposal": json_path(proposal_path),
            "target": json_path(resolved_target) if resolved_target else "",
            "review_pass": False,
            "issues": [issue("proposal-marker-invalid", str(exc))],
        }
    metadata = proposal_metadata(proposal_path)
    replacement_kind = proposal_replacement_kind(proposal_path)
    if resolved_target is None:
        issues.append(issue("proposal-target-missing", "Proposal must include a student-os-target marker or pass --target."))
    if metadata.get("proposal-schema") != PROPOSAL_SCHEMA_VERSION:
        issues.append(
            issue(
                "proposal-schema-missing",
                f"Proposal must include student-os-proposal-schema: {PROPOSAL_SCHEMA_VERSION}.",
            )
        )
    evidence_mode = metadata.get("evidence-mode", "")
    if evidence_mode not in {"text-only", "pdf-text-layer", "ocr-assisted", "vision-assisted"}:
        issues.append(issue("proposal-evidence-mode-invalid", "Proposal must declare text-only, pdf-text-layer, ocr-assisted, or vision-assisted evidence mode."))
    model_capability = metadata.get("model-capability", "")
    if model_capability not in {"text-only", "vision"}:
        issues.append(issue("proposal-model-capability-invalid", "Proposal must declare model capability as text-only or vision."))
    if not metadata.get("changed-sections"):
        issues.append(issue("proposal-changed-sections-missing", "Proposal must declare changed sections or line ranges."))
    if not metadata.get("remaining-risks"):
        issues.append(issue("proposal-remaining-risks-missing", "Proposal must declare remaining human-review risks."))
    proposal_text = proposal_path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"(?i)(?:^|[\\/])[^\\/ \n\r]+\.fixed\b|\.dsh[\\/]tmp[\\/].*fix_|debug_|trace_", proposal_text):
        issues.append(
            issue(
                "proposal-derived-from-scratch-fix",
                "Proposal appears to be derived from a .fixed file or vault-local scratch script; generate a proposal from the case instead.",
            )
        )
    case_payload: dict[str, object] | None = None
    case_state_root: Path | None = None
    case_json_value = metadata.get("case-json", "")
    case_sha_value = metadata.get("case-sha256", "")
    evidence_sha_value = metadata.get("evidence-sha256", "")
    if not case_json_value:
        issues.append(issue("proposal-case-json-missing", "Proposal must bind to the generated case JSON artifact."))
    else:
        case_json_path = Path(case_json_value).expanduser()
        if not case_json_path.exists():
            issues.append(issue("proposal-case-json-unavailable", "Proposal case JSON artifact is not available.", detail={"case_json": case_json_value}))
        else:
            case_json_path = case_json_path.resolve()
            case_state_root = state_root_from_case_json(case_json_path)
            if case_state_root is None:
                issues.append(
                    issue(
                        "proposal-case-json-outside-vault",
                        "Case JSON must be stored under a vault .student-os directory.",
                        detail={"case_json": json_path(case_json_path)},
                    )
                )
            try:
                loaded_case = load_json(case_json_path)
                if not isinstance(loaded_case, dict):
                    issues.append(
                        issue(
                            "proposal-case-json-top-level-invalid",
                            "Proposal case JSON must be an object.",
                            detail={"type": type(loaded_case).__name__},
                        )
                    )
                else:
                    case_payload = loaded_case
                if case_payload is not None and case_payload.get("schema_version") != CASE_SCHEMA_VERSION:
                    issues.append(
                        issue(
                            "proposal-case-schema-invalid",
                            "Proposal case JSON has an unsupported schema version.",
                            detail={"schema_version": case_payload.get("schema_version")},
                        )
                    )
                if case_payload is not None and case_payload.get("ok") is not True:
                    issues.append(issue("proposal-case-not-ok", "Proposal case JSON is not marked ok."))
            except (OSError, json.JSONDecodeError) as exc:
                issues.append(issue("proposal-case-json-invalid", f"Proposal case JSON cannot be read: {exc}"))
    if not case_sha_value:
        issues.append(issue("proposal-case-sha256-missing", "Proposal must bind to the full generated case hash."))
    elif case_payload is not None:
        stored_case_sha = str(case_payload.get("case_sha256") or "")
        actual_case_sha = case_sha256(case_payload)
        if stored_case_sha != case_sha_value:
            issues.append(
                issue(
                    "proposal-case-hash-mismatch",
                    "Proposal case hash does not match the bound case JSON hash.",
                    detail={"proposal": case_sha_value, "case": stored_case_sha},
                )
            )
        if actual_case_sha != case_sha_value:
            issues.append(
                issue(
                    "proposal-case-stale",
                    "Proposal case hash does not match the current case JSON payload.",
                    detail={"expected": case_sha_value, "actual": actual_case_sha},
                )
            )
    queue_item = case_payload.get("queue_item") if isinstance(case_payload, dict) else None
    if not isinstance(queue_item, dict):
        queue_item = None
        if case_payload is not None:
            issues.append(issue("proposal-case-queue-item-missing", "Bound case JSON must include a complete queue_item."))
    else:
        issues.extend(validate_queue_item(queue_item))
    if not evidence_sha_value:
        issues.append(issue("proposal-evidence-sha256-missing", "Proposal must bind to the generated evidence hash."))
    elif case_payload is not None:
        evidence_payload = case_payload.get("evidence")
        if not isinstance(evidence_payload, dict):
            issues.append(issue("proposal-evidence-payload-invalid", "Proposal case evidence payload must be an object."))
            evidence_payload = {}
        evidence_schema = str(evidence_payload.get("schema_version") or "")
        evidence_payload_mode = str(evidence_payload.get("mode") or "")
        if evidence_schema != CASE_SCHEMA_VERSION:
            issues.append(
                issue(
                    "proposal-evidence-schema-invalid",
                    "Proposal case evidence payload has an unsupported schema version.",
                    detail={"schema_version": evidence_schema},
                )
            )
        if evidence_payload_mode != evidence_mode:
            issues.append(
                issue(
                    "proposal-evidence-mode-mismatch",
                    "Proposal evidence-mode must match the bound case evidence mode.",
                    detail={"proposal": evidence_mode, "case": evidence_payload_mode},
                )
            )
        case_evidence_sha = str(case_payload.get("evidence_sha256") or "")
        actual_evidence_sha = object_sha256(evidence_payload)
        if case_evidence_sha and case_evidence_sha != evidence_sha_value:
            issues.append(
                issue(
                    "proposal-evidence-hash-mismatch",
                    "Proposal evidence hash does not match the bound case evidence hash.",
                    detail={"proposal": evidence_sha_value, "case": case_evidence_sha},
                )
            )
        if actual_evidence_sha != evidence_sha_value:
            issues.append(
                issue(
                    "proposal-evidence-stale",
                    "Proposal evidence hash does not match the current case JSON evidence payload.",
                    detail={"expected": evidence_sha_value, "actual": actual_evidence_sha},
                )
            )
    if evidence_mode == "vision-assisted" and case_payload is not None:
        evidence_payload = case_payload.get("evidence")
        vision_payload = evidence_payload.get("vision") if isinstance(evidence_payload, dict) else None
        state_dir = Path(str(evidence_payload.get("state_dir"))).expanduser().resolve() if isinstance(evidence_payload, dict) and evidence_payload.get("state_dir") else None
        pages_dir = state_dir / "pages" if state_dir is not None else None
        if model_capability != "vision":
            issues.append(issue("vision-model-capability-required", "Vision-assisted proposals require model-capability: vision."))
        pages = vision_payload.get("pages") if isinstance(vision_payload, dict) else []
        if not (isinstance(vision_payload, dict) and vision_payload.get("ok") is True and isinstance(pages, list) and pages):
            issues.append(
                issue(
                    "vision-evidence-unavailable",
                    "Vision-assisted proposals require a bound case with successful rendered candidate pages.",
                    detail=vision_payload,
                )
            )
        elif any(
            not isinstance(page, dict)
            or not isinstance(page.get("path"), str)
            or not str(page.get("path")).strip()
            or not Path(str(page.get("path"))).is_file()
            or Path(str(page.get("path"))).suffix.lower() != ".png"
            or pages_dir is None
            or not is_relative_to(Path(str(page.get("path"))), pages_dir)
            or not str(page.get("sha256") or "").strip()
            or file_sha256(Path(str(page.get("path")))) != str(page.get("sha256") or "")
            for page in pages
        ):
            issues.append(
                issue(
                    "vision-evidence-page-missing",
                    "Vision-assisted proposals require rendered evidence page files that still exist on disk.",
                    detail=pages,
                )
            )
    if evidence_mode == "ocr-assisted" and case_payload is not None:
        evidence_payload = case_payload.get("evidence")
        ocr_payload = evidence_payload.get("ocr") if isinstance(evidence_payload, dict) else None
        ocr_path = Path(str(ocr_payload.get("path"))).expanduser().resolve() if isinstance(ocr_payload, dict) and ocr_payload.get("path") else None
        if (
            not isinstance(ocr_payload, dict)
            or ocr_payload.get("ok") is not True
            or ocr_path is None
            or not ocr_path.is_file()
            or ocr_path.suffix.lower() not in {".md", ".txt"}
            or case_state_root is None
            or not is_relative_to(ocr_path, case_state_root)
            or not str(ocr_payload.get("sha256") or "").strip()
            or file_sha256(ocr_path) != str(ocr_payload.get("sha256") or "")
        ):
            issues.append(
                issue(
                    "ocr-evidence-unavailable",
                    "OCR-assisted proposals require a bound case with successful OCR evidence.",
                    detail=ocr_payload,
                )
            )

    if re.search(r"(?m)^verify_status:\s*verified\b", replacement):
        issues.append(
            issue(
                "ai-claimed-verification",
                "Proposal claims verify_status: verified; apply will downgrade it to unverified.",
                severity="warning",
            )
        )
    if re.search(r"(?m)^repair_status:\s*(?:human-verified|verified)\b", replacement):
        issues.append(
            issue(
                "ai-claimed-human-repair",
                "Proposal claims a human repair status; apply will downgrade it to auto-repaired.",
                severity="warning",
            )
        )

    governed = mark_auto_repaired(replacement, needs_review=True)
    risk_items = diagnose_import_risks(governed)
    for risk in risk_items:
        code = str(risk.get("code", ""))
        severity = "error" if code in BLOCKING_RISK_CODES else "warning"
        issues.append(issue(f"remaining-{code}", "Replacement still has import risk diagnostics.", severity=severity, detail=risk))

    original_text = ""
    before_risk_items: list[dict[str, object]] = []
    changed_ranges: list[dict[str, int]] = []
    actual_changed_sections: list[dict[str, object]] = []
    scope_pass = True
    if resolved_target and case_state_root is not None:
        if resolved_target.suffix.lower() != ".md" or not is_relative_to(resolved_target, case_state_root):
            issues.append(
                issue(
                    "proposal-target-outside-vault",
                    "Proposal target must be a markdown sidecar inside the bound case vault.",
                    detail={"target": json_path(resolved_target), "vault": json_path(case_state_root)},
                )
            )
    if resolved_target and resolved_target.exists():
        original_text = resolved_target.read_text(encoding="utf-8", errors="replace")
        before_risk_items = diagnose_import_risks(original_text)
        changed_ranges = changed_line_ranges(original_text, replacement)
        if replacement_kind == "section":
            actual_changed_sections = sections_for_selectors(
                original_text,
                [selector for selector, _body in section_replacements(proposal_path)],
            )
        else:
            actual_changed_sections = sections_for_ranges(original_text, changed_ranges)
        single_section_case = bool(queue_item and queue_item.get("single_section_candidate") is True)
        if single_section_case and len(actual_changed_sections) > 1 and not declared_widened_scope(metadata):
            scope_pass = False
            issues.append(
                issue(
                    "proposal-scope-widened-without-authorization",
                    "Proposal was generated for a single-section queue item but changes multiple non-adjacent sections.",
                    detail={
                        "replacement_kind": replacement_kind,
                        "actual_changed_sections": actual_changed_sections,
                        "required_metadata": "student-os-repair-scope: widened",
                    },
                )
            )
        if single_section_case and replacement_kind == "full" and not declared_widened_scope(metadata):
            issues.append(
                issue(
                    "proposal-full-replacement-for-single-section",
                    "Single-section repairs must use student-os-section-replacement markers unless the user explicitly authorized widened scope.",
                    severity="warning",
                    detail={"required_metadata": "student-os-repair-scope: widened"},
                )
            )
        original_source = frontmatter_value(original_text, "source_file")
        replacement_source = frontmatter_value(replacement, "source_file")
        original_raw_import = frontmatter_value(original_text, "derived_from_import")
        replacement_raw_import = frontmatter_value(replacement, "derived_from_import")
        if original_source and not replacement_source:
            issues.append(
                issue(
                    "source-file-dropped",
                    "Replacement drops source_file frontmatter from the current sidecar.",
                    detail={"source_file": original_source},
                )
            )
        elif original_source and decode_yaml_path(original_source) != decode_yaml_path(replacement_source):
            issues.append(
                issue(
                    "source-file-changed",
                    "Replacement changes source_file frontmatter from the current sidecar.",
                    detail={"before": decode_yaml_path(original_source), "after": decode_yaml_path(replacement_source)},
                )
            )
        if original_raw_import and not replacement_raw_import:
            issues.append(
                issue(
                    "derived-from-import-dropped",
                    "Replacement drops derived_from_import frontmatter from the current sidecar.",
                    detail={"derived_from_import": original_raw_import},
                )
            )
        elif original_raw_import and decode_yaml_path(original_raw_import) != decode_yaml_path(replacement_raw_import):
            issues.append(
                issue(
                    "derived-from-import-changed",
                    "Replacement changes derived_from_import frontmatter from the current sidecar.",
                    detail={
                        "before": decode_yaml_path(original_raw_import),
                        "after": decode_yaml_path(replacement_raw_import),
                    },
                )
            )
        target_sha = metadata.get("target-sha256", "")
        current_sha = file_sha256(resolved_target)
        if not target_sha:
            issues.append(issue("proposal-target-sha256-missing", "Proposal must include the target sha256 from the repair case."))
        elif target_sha != current_sha:
            issues.append(
                issue(
                    "proposal-target-stale",
                    "Target sidecar changed after the case/proposal was prepared.",
                    detail={"expected": target_sha, "actual": current_sha},
                )
            )
        if queue_item is not None:
            if queue_item.get("schema_version") != QUEUE_SCHEMA_VERSION:
                issues.append(
                    issue(
                        "proposal-queue-item-schema-invalid",
                        "Bound case queue item has an unsupported schema version.",
                        detail={"schema_version": queue_item.get("schema_version")},
                    )
                )
            item_path = Path(str(queue_item.get("path") or "")).expanduser() if queue_item.get("path") else None
            if item_path and item_path.resolve() != resolved_target:
                issues.append(
                    issue(
                        "proposal-case-target-mismatch",
                        "Bound case queue item does not match the proposal target.",
                        detail={"case_target": json_path(item_path), "proposal_target": json_path(resolved_target)},
                    )
                )
            item_sha = str(queue_item.get("content_sha256") or "")
            if item_sha and item_sha != current_sha:
                issues.append(
                    issue(
                        "proposal-case-target-stale",
                        "Bound case queue item was generated for different target content.",
                        detail={"case_sha256": item_sha, "actual": current_sha},
                    )
                )
        boundary_regressions = markdown_paragraph_boundary_regressions(original_text, replacement)
        if boundary_regressions:
            issues.append(
                issue(
                    "markdown-paragraph-boundary-regression",
                    "Replacement glues a question heading to the previous paragraph; preserve the blank separator line.",
                    detail={"regressions": boundary_regressions},
                )
            )
    elif resolved_target:
        issues.append(
            issue(
                "proposal-target-missing-file",
                "Proposal target sidecar does not exist on disk.",
                detail={"target": json_path(resolved_target)},
            )
        )
    if queue_item is not None and evidence_mode == "text-only":
        blocked = str(queue_item.get("blocked") or "")
        recommended = str(queue_item.get("recommended_evidence_mode") or "")
        if blocked == "requires-vision-evidence" or recommended == "vision-assisted":
            issues.append(
                issue(
                    "text-only-cannot-resolve-vision-risk",
                    "Text-only proposal cannot claim to resolve an item that requires vision evidence.",
                    detail={"blocked": blocked, "recommended_evidence_mode": recommended},
                )
            )
    if queue_item is not None and model_capability == "text-only":
        blocked = str(queue_item.get("blocked") or "")
        if blocked == "requires-vision-evidence":
            issues.append(
                issue(
                    "text-model-blocked-by-vision-risk",
                    "Text-only model must leave requires-vision-evidence work blocked instead of rewriting content.",
                )
            )
    old_numbers = question_numbers(original_text)
    new_numbers = question_numbers(replacement)
    original_visible = compact_visible_text(original_text)
    replacement_visible = compact_visible_text(replacement)
    if original_visible and len(replacement_visible) < max(1, len(original_visible) // 5):
        issues.append(
            issue(
                "replacement-body-erased",
                "Replacement removes most imported content from the current sidecar.",
                detail={"before_chars": len(original_visible), "after_chars": len(replacement_visible)},
            )
        )
    if old_numbers and len(new_numbers) < len(old_numbers):
        issues.append(
            issue(
                "question-number-count-decreased",
                "Replacement removes question numbers compared with the current sidecar.",
                detail={"before": old_numbers, "after": new_numbers},
            )
        )
    missing_numbers = [number for number in old_numbers if number not in new_numbers]
    if missing_numbers:
        issues.append(
            issue(
                "question-number-missing",
                "Replacement is missing question numbers present in the current sidecar.",
                detail={"missing": missing_numbers},
            )
        )

    target_name = resolved_target.name if resolved_target else proposal_path.name
    if re.search(r"(答案|参考答案|解析)", target_name) and re.search(r"(?m)^\s*(?:解|证明|答)[:：]", replacement):
        if not has_question_stem(replacement):
            issues.append(issue("answer-missing-question-stem", "Answer proposal appears to start solving before preserving the question stem."))

    for environment in ("array", "matrix", "pmatrix", "bmatrix", "cases"):
        begin_count = len(re.findall(rf"\\begin\{{{environment}\}}", replacement))
        end_count = len(re.findall(rf"\\end\{{{environment}\}}", replacement))
        if begin_count != end_count:
            issues.append(
                issue(
                    "latex-environment-unbalanced",
                    f"Replacement has unbalanced {environment} environment markers.",
                    detail={"environment": environment, "begin": begin_count, "end": end_count},
                )
            )

    before_blocking = risk_codes(before_risk_items) & BLOCKING_RISK_CODES
    after_blocking = risk_codes(risk_items) & BLOCKING_RISK_CODES
    render_codes = {"obsidian-inline-array-render-risk", "display-math-delimiter-not-standalone", "inline-math-delimiter-space"}
    review_pass = not any(item["severity"] == "error" for item in issues)
    failure_reason, recommended_next_action = review_failure_guidance(issues, risk_items)
    paragraph_boundaries_preserved = not any(item.get("code") == "markdown-paragraph-boundary-regression" for item in issues)
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "proposal": json_path(proposal_path),
        "target": json_path(resolved_target) if resolved_target else "",
        "metadata": metadata,
        "review_pass": review_pass,
        "replacement_kind": replacement_kind,
        "actual_changed_sections": actual_changed_sections,
        "changed_line_ranges": changed_ranges,
        "scope_pass": scope_pass,
        "paragraph_boundaries_preserved": paragraph_boundaries_preserved,
        "post_apply_direct_edit_allowed": False,
        "next_action_on_post_apply_issue": "create-follow-up-proposal",
        "blocking_risk_count_before": len(before_blocking),
        "blocking_risk_count_after": len(after_blocking),
        "render_risks_cleared": sorted((before_blocking & render_codes) - (after_blocking & render_codes)),
        "remaining_warnings": [item for item in issues if item.get("severity") == "warning"],
        "failure_reason": failure_reason,
        "recommended_next_action": recommended_next_action,
        "issues": issues,
        "risk_items": risk_items,
        "question_numbers": {"before": old_numbers, "after": new_numbers},
    }


def write_review(payload: dict[str, object], *, root: Path, proposal_path: Path) -> Path:
    review_dir = root / ".student-os" / "import-repair" / "reviews"
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / f"{proposal_path.stem}.json"
    review_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return review_path


def main() -> int:
    configure_stdout()
    parser = argparse.ArgumentParser(description="Mechanically review an AI import repair proposal before apply.")
    parser.add_argument("--proposal", required=True, help="Proposal markdown path")
    parser.add_argument("--target", help="Target sidecar path; defaults to student-os-target marker in proposal")
    parser.add_argument("--write-review", action="store_true", help="Write .student-os/import-repair/reviews/<proposal>.json")
    parser.add_argument("--json", action="store_true", help="Print structured review JSON")
    args = parser.parse_args()

    proposal_path = Path(args.proposal).expanduser().resolve()
    target = Path(args.target).expanduser().resolve() if args.target else None
    payload = review_proposal(proposal_path, target=target)
    root = state_root_for(proposal_path, Path(str(payload["target"])) if payload.get("target") else None)
    if args.write_review:
        payload["review_path"] = json_path(write_review(payload, root=root, proposal_path=proposal_path))
    if args.json or not args.write_review:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["review_path"])
    return 0 if payload["review_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
