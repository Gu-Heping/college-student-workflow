#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import hashlib
from pathlib import Path

from import_governance import ensure_field, mark_auto_repaired
from repair_import_queue import SCHEMA_VERSION as QUEUE_SCHEMA_VERSION
from repair_import_queue import STATE_DIR, build_queue_item, file_sha256, json_path, relative_path


SCHEMA_VERSION = "import-repair-case/v1"
PROPOSAL_SCHEMA_VERSION = "import-repair-proposal/v1"
REPLACEMENT_START = "<!-- student-os-replacement-start -->"
REPLACEMENT_END = "<!-- student-os-replacement-end -->"
EVIDENCE_MODES = {"auto", "text-only", "ocr-assisted", "vision-assisted"}


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def object_sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def case_integrity_payload(case_payload: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in case_payload.items() if key != "case_sha256"}


def case_sha256(case_payload: dict[str, object]) -> str:
    return object_sha256(case_integrity_payload(case_payload))


def find_queue(start: Path) -> Path | None:
    start = start.resolve()
    candidates = [start, *start.parents] if start.is_dir() else [start.parent, *start.parent.parents]
    for parent in candidates:
        queue = parent / STATE_DIR / "queue.json"
        if queue.exists():
            return queue
    return None


def resolve_queue_item(queue_item: str, *, queue_path: Path | None, cwd: Path) -> tuple[Path, dict[str, object], Path]:
    candidate = Path(queue_item).expanduser()
    if candidate.exists():
        target = candidate.resolve()
        root = cwd.resolve()
        item = build_queue_item(root, target)
        if item is None:
            item = {
                "id": target.stem,
                "path": json_path(target),
                "relative_path": relative_path(root, target),
                "source_file": "",
                "raw_import": "",
                "repair_summary": "",
                "risk_codes": [],
                "risks": [],
                "snippets": [],
            }
        return root, item, target

    queue = queue_path.resolve() if queue_path else find_queue(cwd)
    if queue is None:
        raise SystemExit("Queue file not found. Run repair_import_queue.py <vault> --write-queue first or pass --queue.")
    payload = load_json(queue)
    if payload.get("schema_version") != QUEUE_SCHEMA_VERSION:
        raise SystemExit(f"Unsupported queue schema_version: {payload.get('schema_version')}")
    root = Path(str(payload.get("target_root") or queue.parents[2])).resolve()
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        if item.get("id") == queue_item or item.get("path") == queue_item or item.get("relative_path") == queue_item:
            target = Path(str(item["path"])).resolve()
            return root, item, target
    raise SystemExit(f"Queue item not found: {queue_item}")


def excerpt(path: Path | None, *, max_chars: int = 5000) -> str:
    if path is None or not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n...[truncated for repair case]...\n"


def source_evidence(item: dict[str, object], target: Path) -> dict[str, object]:
    evidence = item.get("evidence")
    if isinstance(evidence, dict):
        source_pdf = evidence.get("source_pdf")
        if isinstance(source_pdf, dict):
            if source_pdf.get("exists"):
                return {
                    "status": "available-path-only",
                    "path": source_pdf.get("path", ""),
                    "page_hint": evidence.get("candidate_pages", []),
                    "note": "Open the source material manually before marking verify_status: verified.",
                }
            if source_pdf.get("path") or source_pdf.get("declared"):
                return {
                    "status": "unavailable",
                    "path": source_pdf.get("path") or source_pdf.get("declared"),
                    "reason": "source file not found on disk",
                }
    source = str(item.get("source_file") or "").strip()
    if not source:
        return {"status": "unavailable", "reason": "missing source_file frontmatter"}
    source_path = Path(source).expanduser()
    if not source_path.is_absolute():
        source_path = target.parent / source_path
    if source_path.exists():
        return {
            "status": "available-path-only",
            "path": json_path(source_path),
            "page_hint": "",
            "note": "Open the source material manually before marking verify_status: verified.",
        }
    return {"status": "unavailable", "path": str(source_path), "reason": "source file not found on disk"}


def render_pdf_pages(source_pdf: Path, output_dir: Path, pages: list[int]) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not pages:
        return {
            "ok": False,
            "reason": "page-hint-unavailable",
            "pages": [],
            "note": "No candidate page was located; do not render arbitrary pages as evidence.",
        }
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError:
        return {
            "ok": False,
            "reason": "missing-pymupdf",
            "pages": [],
            "note": "Install optional requirements before generating vision evidence.",
        }

    written: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    try:
        document = fitz.open(str(source_pdf))
    except Exception as exc:
        return {"ok": False, "reason": "pdf-open-failed", "pages": [], "error": str(exc)}
    try:
        for page_number in pages[:6]:
            if page_number < 1 or page_number > document.page_count:
                failures.append({"page": page_number, "reason": "page-out-of-range"})
                continue
            try:
                page = document.load_page(page_number - 1)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image_path = output_dir / f"page-{page_number}.png"
                pixmap.save(str(image_path))
                written.append({"page": page_number, "path": json_path(image_path)})
            except Exception as exc:
                failures.append({"page": page_number, "reason": "render-failed", "error": str(exc)})
    finally:
        document.close()
    if not written:
        return {"ok": False, "reason": "page-render-failed", "pages": [], "failures": failures}
    return {"ok": True, "pages": written, "failures": failures}


def prepare_evidence(root: Path, item: dict[str, object], *, evidence_mode: str) -> dict[str, object]:
    evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
    recommended = str(evidence.get("recommended_mode") or "text-only") if isinstance(evidence, dict) else "text-only"
    selected_mode = recommended if evidence_mode == "auto" else evidence_mode
    if selected_mode not in EVIDENCE_MODES:
        raise SystemExit(f"Unknown evidence mode: {selected_mode}")
    item_id = str(item.get("id") or "repair-case")
    state_dir = root / STATE_DIR / "evidence" / item_id / selected_mode
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "mode": selected_mode,
        "recommended_mode": recommended,
        "blocked": evidence.get("blocked", "") if isinstance(evidence, dict) else "",
        "pages": [],
        "state_dir": json_path(state_dir),
    }
    if selected_mode == "vision-assisted":
        source_pdf = evidence.get("source_pdf") if isinstance(evidence, dict) else None
        source_path = Path(str(source_pdf.get("path"))) if isinstance(source_pdf, dict) and source_pdf.get("path") else None
        if source_path is None or not source_path.exists():
            payload.update({"blocked": "requires-vision-evidence", "vision": {"ok": False, "reason": "source-pdf-unavailable"}})
        else:
            pages = evidence.get("candidate_pages", []) if isinstance(evidence, dict) else []
            page_numbers = [int(page) for page in pages if isinstance(page, int)]
            payload["vision"] = render_pdf_pages(source_path, state_dir / "pages", page_numbers)
    elif selected_mode == "ocr-assisted":
        payload["ocr"] = {
            "ok": False,
            "reason": "not-run-by-case-tool",
            "note": "Run materials_convert.py with an OCR-capable strategy to create text evidence, then regenerate the case.",
        }
    return payload


def write_case_json(root: Path, item: dict[str, object], evidence_payload: dict[str, object]) -> Path:
    state_dir = Path(str(evidence_payload["state_dir"]))
    state_dir.mkdir(parents=True, exist_ok=True)
    case_json = state_dir / "case.json"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "queue_item": item,
        "evidence": evidence_payload,
        "evidence_sha256": object_sha256(evidence_payload),
    }
    payload["case_sha256"] = case_sha256(payload)
    case_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return case_json


def render_case(root: Path, item: dict[str, object], target: Path, evidence_payload: dict[str, object]) -> str:
    raw_path = Path(str(item.get("raw_import") or "")).resolve() if item.get("raw_import") else None
    summary_path = Path(str(item.get("repair_summary") or "")).resolve() if item.get("repair_summary") else None
    evidence = source_evidence(item, target)
    case_json = Path(str(evidence_payload["state_dir"])) / "case.json"
    evidence_digest = object_sha256(evidence_payload)
    case_digest = case_sha256(
        {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "queue_item": item,
            "evidence": evidence_payload,
            "evidence_sha256": evidence_digest,
        }
    )
    risk_lines = "\n".join(f"- `{risk}`" for risk in item.get("risk_codes", [])) or "- none"
    sections = item.get("suspect_sections") or item.get("sections") or []
    section_lines: list[str] = []
    if isinstance(sections, list):
        for section in sections[:8]:
            if not isinstance(section, dict):
                continue
            section_lines.extend(
                [
                    f"### {section.get('id')} `{section.get('title', '')}`",
                    "",
                    f"- Lines: {section.get('start_line')}..{section.get('end_line')}",
                    "",
                    "```markdown",
                    str(section.get("excerpt", "")),
                    "```",
                    "",
                ]
            )
    if not section_lines:
        section_lines = ["No section boundaries were detected.", ""]
    snippets = item.get("snippets", [])
    snippet_lines: list[str] = []
    if isinstance(snippets, list):
        for snippet in snippets:
            if not isinstance(snippet, dict):
                continue
            snippet_lines.extend(
                [
                    f"### {snippet.get('code')} at line {snippet.get('line')}",
                    "",
                    "```markdown",
                    str(snippet.get("excerpt", "")),
                    "```",
                    "",
                ]
            )
    if not snippet_lines:
        snippet_lines = ["No localized snippets were available.", ""]

    return "\n".join(
        [
            "# Student OS Import Repair Case",
            "",
            "## Target",
            "",
            f"- Queue item: `{item.get('id', '')}`",
            f"- Sidecar: `{relative_path(root, target)}`",
            f"- Repair status: `{item.get('repair_status', '')}`",
            f"- Verify status: `{item.get('verify_status', '')}`",
            f"- Target sha256: `{item.get('content_sha256') or file_sha256(target)}`",
            f"- Recommended evidence mode: `{item.get('recommended_evidence_mode', '')}`",
            f"- Blocked: `{item.get('blocked', '')}`",
            "",
            "## Boundary",
            "",
            "- AI may rewrite the markdown when the source evidence supports the change.",
            "- AI must keep `repair_status: auto-repaired` and `verify_status: unverified`.",
            "- Only a human who checked the original source may mark `verify_status: verified`.",
            "",
            "## Risks",
            "",
            risk_lines,
            "",
            "## Source Evidence",
            "",
            "```json",
            json.dumps({"source": evidence, "prepared": evidence_payload}, ensure_ascii=False, indent=2),
            "```",
            "",
            "## Suspicious Snippets",
            "",
            *snippet_lines,
            "## Suspect Sections",
            "",
            *section_lines,
            "## Repair Summary Excerpt",
            "",
            "```markdown",
            excerpt(summary_path, max_chars=2500) or "unavailable",
            "```",
            "",
            "## Raw Import Excerpt",
            "",
            "```markdown",
            excerpt(raw_path, max_chars=4000) or "unavailable",
            "```",
            "",
            "## Current Sidecar Excerpt",
            "",
            "```markdown",
            excerpt(target, max_chars=5000),
            "```",
            "",
            "## Proposal Template",
            "",
            "Explain evidence and remaining risks above the replacement block. Keep these metadata markers accurate:",
            "",
            f"<!-- student-os-proposal-schema: {PROPOSAL_SCHEMA_VERSION} -->",
            f"<!-- student-os-target: {json_path(target)} -->",
            f"<!-- student-os-target-sha256: {item.get('content_sha256') or file_sha256(target)} -->",
            f"<!-- student-os-case-json: {json_path(case_json)} -->",
            f"<!-- student-os-case-sha256: {case_digest} -->",
            f"<!-- student-os-evidence-sha256: {evidence_digest} -->",
            f"<!-- student-os-evidence-mode: {evidence_payload.get('mode', 'text-only')} -->",
            "<!-- student-os-model-capability: text-only|vision -->",
            "<!-- student-os-changed-sections: section-id-or-line-range -->",
            "<!-- student-os-remaining-risks: human-review-required -->",
            "",
            REPLACEMENT_START,
            "",
            "<full replacement markdown>",
            "",
            REPLACEMENT_END,
            "",
        ]
    )


def write_case(root: Path, item: dict[str, object], markdown: str) -> Path:
    case_dir = root / STATE_DIR / "cases"
    case_dir.mkdir(parents=True, exist_ok=True)
    case_path = case_dir / f"{item.get('id', 'repair-case')}.md"
    case_path.write_text(markdown, encoding="utf-8", newline="\n")
    return case_path


def extract_replacement(proposal_path: Path) -> str:
    text = proposal_path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"{re.escape(REPLACEMENT_START)}\s*\n(?P<body>.*?)\n\s*{re.escape(REPLACEMENT_END)}",
        flags=re.S,
    )
    match = pattern.search(text)
    if not match:
        raise SystemExit(f"Proposal is missing {REPLACEMENT_START} / {REPLACEMENT_END} replacement markers.")
    body = match.group("body").strip("\n")
    if not body.strip():
        raise SystemExit("Proposal replacement block is empty.")
    return body + "\n"


def apply_proposal(proposal_path: Path, target: Path, output: Path | None, *, evidence_mode: str) -> Path:
    replacement = extract_replacement(proposal_path)
    governed = mark_auto_repaired(replacement, needs_review=True)
    governed = ensure_field(governed, "repair_evidence_mode", evidence_mode)
    governed = ensure_field(governed, "repair_ai_confidence", "unverified")
    destination = (output or target).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(governed, encoding="utf-8", newline="\n")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or apply a Student OS AI import repair case.")
    parser.add_argument("--queue-item", required=True, help="Queue item id, queue relative path, or sidecar path")
    parser.add_argument("--queue", help="Explicit queue.json path")
    parser.add_argument("--write-case", action="store_true", help="Write .student-os/import-repair/cases/<id>.md")
    parser.add_argument(
        "--evidence-mode",
        choices=sorted(EVIDENCE_MODES),
        default="auto",
        help="Evidence mode for this case; auto follows the queue recommendation.",
    )
    parser.add_argument("--output", help="Output path for --apply-proposal")
    parser.add_argument("--apply-proposal", help="Apply a proposal replacement block to the sidecar or --output")
    parser.add_argument("--json", action="store_true", help="Print structured result")
    args = parser.parse_args()

    queue_path = Path(args.queue).expanduser() if args.queue else None
    root, item, target = resolve_queue_item(args.queue_item, queue_path=queue_path, cwd=Path.cwd())

    if args.apply_proposal:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "stage": "apply",
            "error": "repair_import_case.py no longer applies proposals directly; use repair_import_apply.py so review gates are mandatory.",
            "target": json_path(target),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    evidence_payload = prepare_evidence(root, item, evidence_mode=args.evidence_mode)
    case_json = write_case_json(root, item, evidence_payload)
    markdown = render_case(root, item, target, evidence_payload)
    case_path = write_case(root, item, markdown) if args.write_case else None
    payload = {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "case_written": bool(case_path),
        "case_path": json_path(case_path) if case_path else "",
        "case_json": json_path(case_json),
        "evidence": evidence_payload,
        "queue_item": item,
        "markdown": markdown,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif case_path:
        print(case_path)
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
