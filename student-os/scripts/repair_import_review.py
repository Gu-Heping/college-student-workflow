#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from import_governance import diagnose_import_risks, frontmatter_value, mark_auto_repaired
from repair_import_case import PROPOSAL_SCHEMA_VERSION, extract_replacement, json_path
from repair_import_queue import build_queue_item, file_sha256


SCHEMA_VERSION = "import-repair-review/v1"
TARGET_RE = re.compile(r"<!--\s*student-os-target:\s*(?P<path>.*?)\s*-->")
META_RE = re.compile(r"<!--\s*student-os-(?P<key>[a-z0-9-]+):\s*(?P<value>.*?)\s*-->")
QUESTION_RE = re.compile(r"(?m)^\s*(?:#{1,3}\s*)?(?P<num>[一二三四五六七八九十]+|[0-9]+)[\.、．)]")


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


def question_numbers(text: str) -> list[str]:
    return [match.group("num") for match in QUESTION_RE.finditer(text)]


def proposal_metadata(proposal_path: Path) -> dict[str, str]:
    text = proposal_path.read_text(encoding="utf-8", errors="replace")
    return {match.group("key"): match.group("value").strip() for match in META_RE.finditer(text)}


def issue(code: str, message: str, *, severity: str = "error", detail: object | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"code": code, "severity": severity, "message": message}
    if detail is not None:
        payload["detail"] = detail
    return payload


def review_proposal(proposal_path: Path, *, target: Path | None = None) -> dict[str, object]:
    proposal_path = proposal_path.resolve()
    resolved_target = target or proposal_target(proposal_path, None)
    issues: list[dict[str, object]] = []
    try:
        replacement = extract_replacement(proposal_path)
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
    if evidence_mode not in {"text-only", "ocr-assisted", "vision-assisted"}:
        issues.append(issue("proposal-evidence-mode-invalid", "Proposal must declare text-only, ocr-assisted, or vision-assisted evidence mode."))
    model_capability = metadata.get("model-capability", "")
    if model_capability not in {"text-only", "vision"}:
        issues.append(issue("proposal-model-capability-invalid", "Proposal must declare model capability as text-only or vision."))
    if not metadata.get("changed-sections"):
        issues.append(issue("proposal-changed-sections-missing", "Proposal must declare changed sections or line ranges."))
    if not metadata.get("remaining-risks"):
        issues.append(issue("proposal-remaining-risks-missing", "Proposal must declare remaining human-review risks."))

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
        severity = "error" if code in {"math-dollar-unbalanced", "latex-left-right-unbalanced"} else "warning"
        issues.append(issue(f"remaining-{code}", "Replacement still has import risk diagnostics.", severity=severity, detail=risk))

    original_text = ""
    if resolved_target and resolved_target.exists():
        original_text = resolved_target.read_text(encoding="utf-8", errors="replace")
        original_source = frontmatter_value(original_text, "source_file")
        replacement_source = frontmatter_value(replacement, "source_file")
        if original_source and not replacement_source:
            issues.append(
                issue(
                    "source-file-dropped",
                    "Replacement drops source_file frontmatter from the current sidecar.",
                    detail={"source_file": original_source},
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
        queue_item = build_queue_item(resolved_target.parent, resolved_target)
        if queue_item and evidence_mode == "text-only":
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
        if queue_item and model_capability == "text-only":
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
        head = replacement[:3000]
        if not re.search(r"(题干|已知|求证|设|证明|计算|求)", head):
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

    review_pass = not any(item["severity"] == "error" for item in issues)
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "proposal": json_path(proposal_path),
        "target": json_path(resolved_target) if resolved_target else "",
        "metadata": metadata,
        "review_pass": review_pass,
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
