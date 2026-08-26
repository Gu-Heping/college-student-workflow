#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from repair_import_case import apply_proposal, json_path
from repair_import_review import proposal_target, review_proposal


SCHEMA_VERSION = "import-repair-apply/v1"


def load_review(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "import-repair-review/v1":
        raise SystemExit(f"Unsupported review schema_version: {payload.get('schema_version')}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a reviewed AI import repair proposal with Student OS governance.")
    parser.add_argument("--proposal", required=True, help="Proposal markdown path")
    parser.add_argument("--target", help="Target sidecar path; defaults to student-os-target marker in proposal")
    parser.add_argument("--output", help="Optional output path; defaults to target")
    parser.add_argument("--review", help="Existing review JSON path")
    parser.add_argument(
        "--require-review-pass",
        action="store_true",
        help="Deprecated compatibility flag; apply always refuses failed reviews.",
    )
    parser.add_argument("--evidence-mode", help="Optional assertion; must match the proposal evidence-mode metadata")
    parser.add_argument("--json", action="store_true", help="Print structured apply JSON")
    args = parser.parse_args()

    proposal_path = Path(args.proposal).expanduser().resolve()
    target = Path(args.target).expanduser().resolve() if args.target else proposal_target(proposal_path, None)
    if target is None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "stage": "resolve-target",
            "error": "Target sidecar is required; pass --target or include a student-os-target marker in the proposal.",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    recorded_review = load_review(Path(args.review).expanduser().resolve()) if args.review else None
    review_payload = review_proposal(proposal_path, target=target)
    if recorded_review and recorded_review.get("target") and Path(str(recorded_review["target"])).resolve() != target:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "stage": "review",
            "proposal": json_path(proposal_path),
            "target": json_path(target),
            "error": "Existing review target does not match apply target.",
            "review": recorded_review,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    if recorded_review:
        review_payload["recorded_review"] = recorded_review
    if not review_payload.get("review_pass"):
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "stage": "review",
            "proposal": json_path(proposal_path),
            "target": json_path(target),
            "error": "Proposal review did not pass.",
            "review": review_payload,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    metadata = review_payload.get("metadata") if isinstance(review_payload.get("metadata"), dict) else {}
    declared_evidence_mode = str(metadata.get("evidence-mode") or "")
    if not declared_evidence_mode:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "stage": "review",
            "proposal": json_path(proposal_path),
            "target": json_path(target),
            "error": "Proposal review did not provide an evidence-mode.",
            "review": review_payload,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    if args.evidence_mode and args.evidence_mode != declared_evidence_mode:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "stage": "evidence-mode",
            "proposal": json_path(proposal_path),
            "target": json_path(target),
            "error": "Explicit --evidence-mode does not match proposal metadata.",
            "declared_evidence_mode": declared_evidence_mode,
            "requested_evidence_mode": args.evidence_mode,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    output = Path(args.output).expanduser().resolve() if args.output else None
    written = apply_proposal(proposal_path, target, output, evidence_mode=declared_evidence_mode)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "applied": True,
        "proposal": json_path(proposal_path),
        "target": json_path(target),
        "output": json_path(written),
        "review_pass": bool(review_payload.get("review_pass")),
        "verify_status": "unverified",
        "repair_status": "auto-repaired",
        "repair_evidence_mode": declared_evidence_mode,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
