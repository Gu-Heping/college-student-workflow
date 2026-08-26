#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from repair_import_case import apply_proposal, json_path
from repair_import_review import proposal_target, review_proposal


def load_review(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a reviewed AI import repair proposal with Student OS governance.")
    parser.add_argument("--proposal", required=True, help="Proposal markdown path")
    parser.add_argument("--target", help="Target sidecar path; defaults to student-os-target marker in proposal")
    parser.add_argument("--output", help="Optional output path; defaults to target")
    parser.add_argument("--review", help="Existing review JSON path")
    parser.add_argument("--require-review-pass", action="store_true", help="Refuse to apply unless review_pass is true")
    parser.add_argument("--evidence-mode", default="text-only", help="Recorded repair_evidence_mode value")
    parser.add_argument("--json", action="store_true", help="Print structured apply JSON")
    args = parser.parse_args()

    proposal_path = Path(args.proposal).expanduser().resolve()
    target = Path(args.target).expanduser().resolve() if args.target else proposal_target(proposal_path, None)
    if target is None:
        payload = {
            "ok": False,
            "stage": "resolve-target",
            "error": "Target sidecar is required; pass --target or include a student-os-target marker in the proposal.",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    review_payload = load_review(Path(args.review).expanduser().resolve()) if args.review else review_proposal(proposal_path, target=target)
    if args.require_review_pass and not review_payload.get("review_pass"):
        payload = {
            "ok": False,
            "stage": "review",
            "proposal": json_path(proposal_path),
            "target": json_path(target),
            "error": "Proposal review did not pass.",
            "review": review_payload,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    output = Path(args.output).expanduser().resolve() if args.output else None
    written = apply_proposal(proposal_path, target, output, evidence_mode=args.evidence_mode)
    payload = {
        "ok": True,
        "applied": True,
        "proposal": json_path(proposal_path),
        "target": json_path(target),
        "output": json_path(written),
        "review_pass": bool(review_payload.get("review_pass")),
        "verify_status": "unverified",
        "repair_status": "auto-repaired",
        "repair_evidence_mode": args.evidence_mode,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
