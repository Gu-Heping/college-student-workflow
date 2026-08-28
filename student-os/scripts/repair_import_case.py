#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import hashlib
import os
import sys
import tempfile
from pathlib import Path

from import_governance import ensure_field, is_verified, mark_auto_repaired
from repair_import_queue import SCHEMA_VERSION as QUEUE_SCHEMA_VERSION
from repair_import_queue import STATE_DIR, build_queue_item, file_sha256, json_path, relative_path, split_sections


SCHEMA_VERSION = "import-repair-case/v1"
PROPOSAL_SCHEMA_VERSION = "import-repair-proposal/v1"
REPLACEMENT_START = "<!-- student-os-replacement-start -->"
REPLACEMENT_END = "<!-- student-os-replacement-end -->"
SECTION_REPLACEMENT_END = "<!-- student-os-section-replacement-end -->"
LINE_REPLACEMENT_END = "<!-- student-os-line-replacement-end -->"
EVIDENCE_MODES = {"auto", "text-only", "pdf-text-layer", "ocr-assisted", "vision-assisted"}
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SECTION_REPLACEMENT_RE = re.compile(
    r"<!--\s*student-os-section-replacement-start:\s*(?P<section>.*?)\s*-->\s*\n(?P<body>.*?)\n\s*"
    + re.escape(SECTION_REPLACEMENT_END),
    flags=re.S,
)
LINE_REPLACEMENT_RE = re.compile(
    r"<!--\s*student-os-line-replacement-start:\s*(?P<start>\d+)(?:\s*-\s*(?P<end>\d+))?(?:\s+sha256=(?P<sha>[0-9a-f]{64}))?\s*-->\s*\n(?P<body>.*?)\n\s*"
    + re.escape(LINE_REPLACEMENT_END),
    flags=re.S,
)


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
        sys.stderr.reconfigure(encoding="utf-8", newline="\n")
    except AttributeError:
        pass


def object_sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def case_integrity_payload(case_payload: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in case_payload.items() if key != "case_sha256"}


def case_sha256(case_payload: dict[str, object]) -> str:
    return object_sha256(case_integrity_payload(case_payload))


def build_case_payload(item: dict[str, object], evidence_payload: dict[str, object]) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "item_id": item.get("id", ""),
        "target": item.get("path", ""),
        "target_sha256": item.get("content_sha256", ""),
        "primary_risk": item.get("primary_risk", {}),
        "blocking_risk_lines": item.get("blocking_risk_lines", []),
        "target_section": item.get("target_section", {}),
        "repair_scope_required": item.get("repair_scope_required", ""),
        "single_section_candidate": item.get("single_section_candidate", False),
        "queue_item": item,
        "evidence": evidence_payload,
        "evidence_sha256": object_sha256(evidence_payload),
    }
    payload["case_sha256"] = case_sha256(payload)
    return payload


def find_queue(start: Path) -> Path | None:
    start = start.resolve()
    candidates = [start, *start.parents] if start.is_dir() else [start.parent, *start.parent.parents]
    for parent in candidates:
        queue = parent / STATE_DIR / "queue.json"
        if queue.exists():
            return queue
    return None


def state_root_for_target(target: Path, cwd: Path) -> Path:
    for parent in [target.parent, *target.parents]:
        if (parent / ".student-os").exists():
            return parent.resolve()
    try:
        target.resolve().relative_to(cwd.resolve())
        return cwd.resolve()
    except ValueError:
        return target.parent.resolve()


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def safe_state_id(item: dict[str, object], target: Path) -> str:
    item_id = str(item.get("id") or "").strip()
    if SAFE_ID_RE.fullmatch(item_id):
        return item_id
    digest = hashlib.sha256(json_path(target).encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"import-repair-{digest}"


def resolve_queue_item(
    queue_item: str,
    *,
    queue_path: Path | None,
    cwd: Path,
    include_verified: bool = False,
) -> tuple[Path, dict[str, object], Path]:
    candidate = Path(queue_item).expanduser()
    if candidate.exists():
        target = candidate.resolve()
        if target.suffix.lower() != ".md":
            raise SystemExit("Direct queue item targets must be markdown sidecars.")
        if is_verified(target.read_text(encoding="utf-8", errors="replace")) and not include_verified:
            raise SystemExit("Direct queue item target is verified; pass --include-verified to generate a case anyway.")
        root = state_root_for_target(target, cwd)
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
    if not isinstance(payload, dict):
        raise SystemExit(f"Queue JSON must be an object: {type(payload).__name__}")
    if payload.get("schema_version") != QUEUE_SCHEMA_VERSION:
        raise SystemExit(f"Unsupported queue schema_version: {payload.get('schema_version')}")
    root = Path(str(payload.get("target_root") or queue.parents[2])).resolve()
    queue_root = queue.parents[2].resolve()
    if root != queue_root:
        raise SystemExit(f"Queue target_root does not match queue location: {root} != {queue_root}")
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        if item.get("id") == queue_item or item.get("path") == queue_item or item.get("relative_path") == queue_item:
            target = Path(str(item["path"])).resolve()
            item_id = str(item.get("id") or "")
            if not SAFE_ID_RE.fullmatch(item_id):
                raise SystemExit(f"Unsafe queue item id: {item_id!r}")
            if target.suffix.lower() != ".md" or not is_relative_to(target, root):
                raise SystemExit(f"Queue item target must be a markdown sidecar inside target_root: {target}")
            return root, item, target
    raise SystemExit(f"Queue item not found: {queue_item}")


def excerpt(path: Path | None, *, max_chars: int = 5000) -> str:
    if path is None or not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n...[truncated for repair case]...\n"


def safe_markdown_evidence_path(path_value: object, *, root: Path) -> Path | None:
    if not path_value:
        return None
    path = Path(str(path_value)).expanduser().resolve()
    if path.suffix.lower() != ".md" or not is_relative_to(path, root):
        return None
    return path


def fenced_block(language: str, content: str) -> str:
    longest = max((len(match.group(0)) for match in re.finditer(r"`+", content)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}{language}\n{content}\n{fence}"


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
                written.append({"page": page_number, "path": json_path(image_path), "sha256": file_sha256(image_path)})
            except Exception as exc:
                failures.append({"page": page_number, "reason": "render-failed", "error": str(exc)})
    finally:
        document.close()
    if not written:
        return {"ok": False, "reason": "page-render-failed", "pages": [], "failures": failures}
    if failures:
        return {"ok": False, "reason": "partial-page-render-failed", "pages": written, "failures": failures}
    return {"ok": True, "pages": written, "failures": failures}


def prepare_evidence(root: Path, item: dict[str, object], *, evidence_mode: str, ocr_evidence: Path | None = None) -> dict[str, object]:
    evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
    recommended = str(evidence.get("recommended_mode") or "text-only") if isinstance(evidence, dict) else "text-only"
    selected_mode = recommended if evidence_mode == "auto" else evidence_mode
    if selected_mode not in EVIDENCE_MODES:
        raise SystemExit(f"Unknown evidence mode: {selected_mode}")
    target = Path(str(item.get("path") or root)).resolve()
    item_id = safe_state_id(item, target)
    state_dir = root / STATE_DIR / "evidence" / item_id / selected_mode
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "mode": selected_mode,
        "recommended_mode": recommended,
        "blocked": evidence.get("blocked", "") if isinstance(evidence, dict) else "",
        "pages": [],
        "state_dir": json_path(state_dir),
    }
    if selected_mode == "pdf-text-layer":
        source_pdf = evidence.get("source_pdf") if isinstance(evidence, dict) else None
        source_path = Path(str(source_pdf.get("path"))) if isinstance(source_pdf, dict) and source_pdf.get("path") else None
        payload["pdf_text_layer"] = {
            "ok": bool(source_path and source_path.exists()),
            "path": json_path(source_path) if source_path and source_path.exists() else "",
            "candidate_pages": evidence.get("candidate_pages", []) if isinstance(evidence, dict) else [],
            "note": "PDF text-layer evidence is source text extracted from the original PDF; it is not human verification.",
        }
    elif selected_mode == "vision-assisted":
        source_pdf = evidence.get("source_pdf") if isinstance(evidence, dict) else None
        source_path = Path(str(source_pdf.get("path"))) if isinstance(source_pdf, dict) and source_pdf.get("path") else None
        if source_path is None or not source_path.exists():
            payload.update({"blocked": "requires-vision-evidence", "vision": {"ok": False, "reason": "source-pdf-unavailable"}})
        else:
            pages = evidence.get("candidate_pages", []) if isinstance(evidence, dict) else []
            page_numbers = [int(page) for page in pages if isinstance(page, int)]
            payload["vision"] = render_pdf_pages(source_path, state_dir / "pages", page_numbers)
    elif selected_mode == "ocr-assisted":
        if ocr_evidence is None:
            payload["ocr"] = {
                "ok": False,
                "reason": "not-run-by-case-tool",
                "note": "Run materials_convert.py with an OCR-capable strategy to create text evidence, then regenerate the case with --ocr-evidence.",
            }
        else:
            ocr_path = ocr_evidence.expanduser().resolve()
            if not ocr_path.exists():
                payload["ocr"] = {"ok": False, "reason": "ocr-evidence-missing", "path": json_path(ocr_path)}
            elif ocr_path.suffix.lower() not in {".md", ".txt"} or not is_relative_to(ocr_path, root):
                payload["ocr"] = {
                    "ok": False,
                    "reason": "ocr-evidence-outside-vault",
                    "path": json_path(ocr_path),
                }
            else:
                payload["ocr"] = {
                    "ok": True,
                    "path": json_path(ocr_path),
                    "sha256": file_sha256(ocr_path),
                    "excerpt": excerpt(ocr_path, max_chars=4000),
                }
    return payload


def write_case_json(root: Path, item: dict[str, object], evidence_payload: dict[str, object]) -> Path:
    state_dir = Path(str(evidence_payload["state_dir"]))
    state_dir.mkdir(parents=True, exist_ok=True)
    case_json = state_dir / "case.json"
    payload = build_case_payload(item, evidence_payload)
    case_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return case_json


def render_case(root: Path, item: dict[str, object], target: Path, evidence_payload: dict[str, object]) -> str:
    raw_path = safe_markdown_evidence_path(item.get("raw_import"), root=root)
    summary_path = safe_markdown_evidence_path(item.get("repair_summary"), root=root)
    evidence = source_evidence(item, target)
    case_json = Path(str(evidence_payload["state_dir"])) / "case.json"
    case_payload = build_case_payload(item, evidence_payload)
    evidence_digest = str(case_payload["evidence_sha256"])
    case_digest = str(case_payload["case_sha256"])
    risk_lines = "\n".join(f"- `{risk}`" for risk in item.get("risk_codes", [])) or "- none"
    primary_risk = item.get("primary_risk") if isinstance(item.get("primary_risk"), dict) else {}
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
                    fenced_block("markdown", str(section.get("excerpt", ""))),
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
                    fenced_block("markdown", str(snippet.get("excerpt", ""))),
                    "",
                ]
            )
    if not snippet_lines:
        snippet_lines = ["No localized snippets were available.", ""]

    return "\n".join(
        [
            "# Student OS Import Repair Case",
            "",
            "## Action Brief",
            "",
            "- Repair exactly one local section from this case before moving to another item.",
            "- If Obsidian/Markdown preview shows literal TeX such as `$ ... \\begin{array} ... $`, treat that as render failure; do not debate byte-level backslash escapes.",
            "- If Obsidian shows inline math literally because `$` touches an internal space (`$ x$` or `$x $`), remove only that delimiter-adjacent space.",
            "- Do not search for KaTeX/MathJax packages unless the user explicitly asks for renderer debugging.",
            "- For long matrix or array formulas, prefer a display math block and put opening and closing `$$` delimiters alone on their own lines.",
            "- Never write `即 $$`, `设矩阵 $$`, or `$$，则`; move only the delimiter to a standalone line without changing the formula content.",
            "- Align the array column spec with the actual row cells, such as `ccc|cc` for a 3-column block plus 2-column block.",
            "",
            fenced_block("json", json.dumps({"primary_risk": primary_risk}, ensure_ascii=False, indent=2)),
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
            fenced_block("json", json.dumps({"source": evidence, "prepared": evidence_payload}, ensure_ascii=False, indent=2)),
            "",
            "## Suspicious Snippets",
            "",
            *snippet_lines,
            "## Suspect Sections",
            "",
            *section_lines,
            "## Repair Summary Excerpt",
            "",
            fenced_block("markdown", excerpt(summary_path, max_chars=2500) or "unavailable"),
            "",
            "## Raw Import Excerpt",
            "",
            fenced_block("markdown", excerpt(raw_path, max_chars=4000) or "unavailable"),
            "",
            "## Current Sidecar Excerpt",
            "",
            fenced_block("markdown", excerpt(target, max_chars=5000)),
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
            "Preferred for one-section repairs:",
            "<!-- student-os-line-replacement-start: START-END sha256=<span-sha256> -->",
            "<replacement markdown for only those lines>",
            LINE_REPLACEMENT_END,
            "",
            "Fallback when line ranges are not enough:",
            "<!-- student-os-section-replacement-start: section-id-or-lines-START-END -->",
            "<replacement markdown for only that section>",
            SECTION_REPLACEMENT_END,
            "",
            "Compatibility fallback for explicitly widened repairs:",
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
    target = Path(str(item.get("path") or root)).resolve()
    case_path = case_dir / f"{safe_state_id(item, target)}.md"
    case_path.write_text(markdown, encoding="utf-8", newline="\n")
    return case_path


def proposal_replacement_kind(proposal_path: Path) -> str:
    text = proposal_path.read_text(encoding="utf-8")
    if LINE_REPLACEMENT_RE.search(text):
        return "line"
    if SECTION_REPLACEMENT_RE.search(text):
        return "section"
    return "full"


def section_replacements(proposal_path: Path) -> list[tuple[str, str]]:
    text = proposal_path.read_text(encoding="utf-8")
    replacements: list[tuple[str, str]] = []
    for match in SECTION_REPLACEMENT_RE.finditer(text):
        section = match.group("section").strip()
        body = match.group("body").strip("\n")
        if not section:
            raise SystemExit("Section replacement marker must name a section id or line range.")
        if not body.strip():
            raise SystemExit(f"Section replacement block is empty: {section}")
        replacements.append((section, body + "\n"))
    return replacements


def line_replacements(proposal_path: Path) -> list[tuple[int, int, str | None, str]]:
    text = proposal_path.read_text(encoding="utf-8")
    replacements: list[tuple[int, int, str | None, str]] = []
    for match in LINE_REPLACEMENT_RE.finditer(text):
        start = int(match.group("start"))
        end = int(match.group("end") or start)
        if start < 1 or end < start:
            raise SystemExit(f"Line replacement range is invalid: {start}-{end}")
        body = match.group("body").strip("\n")
        if not body.strip():
            raise SystemExit(f"Line replacement block is empty: {start}-{end}")
        replacements.append((start, end, match.group("sha"), body + "\n"))
    return replacements


def span_sha256(lines: list[str]) -> str:
    return hashlib.sha256(("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")).hexdigest()


def resolve_section_span(text: str, selector: str) -> tuple[int, int]:
    selector = selector.strip()
    line_match = re.fullmatch(r"(?:line|lines)[-: ](?P<start>\d+)(?:\s*(?:-|\.\.)\s*(?P<end>\d+))?", selector)
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    if line_match:
        start = int(line_match.group("start"))
        end = int(line_match.group("end") or start)
        if start < 1 or end < start or end > len(lines):
            raise SystemExit(f"Section replacement line range is outside the target: {selector}")
        return start - 1, end
    for section in split_sections(text):
        if str(section.get("id")) == selector:
            start = int(section["start_line"])
            end = int(section["end_line"])
            return start - 1, end
    raise SystemExit(f"Section replacement selector was not found in the target: {selector}")


def apply_section_replacements(original: str, replacements: list[tuple[str, str]]) -> str:
    normalized = original.replace("\r\n", "\n").replace("\r", "\n")
    had_final_newline = normalized.endswith("\n")
    lines = normalized.splitlines()
    spans: list[tuple[int, int, str, str]] = []
    for selector, body in replacements:
        start, end = resolve_section_span(normalized, selector)
        spans.append((start, end, selector, body))
    spans.sort(key=lambda item: item[0], reverse=True)
    previous_start = len(lines) + 1
    for start, end, selector, body in spans:
        if end > previous_start:
            raise SystemExit(f"Section replacement ranges overlap or are not independent: {selector}")
        original_span = lines[start:end]
        replacement_lines = body.rstrip("\n").split("\n")
        if original_span and original_span[-1].strip() == "" and (not replacement_lines or replacement_lines[-1].strip() != ""):
            replacement_lines.append("")
        lines[start:end] = replacement_lines
        previous_start = start
    result = "\n".join(lines)
    return result + "\n" if had_final_newline or result else result


def apply_line_replacements(original: str, replacements: list[tuple[int, int, str | None, str]]) -> str:
    normalized = original.replace("\r\n", "\n").replace("\r", "\n")
    had_final_newline = normalized.endswith("\n")
    lines = normalized.splitlines()
    spans: list[tuple[int, int, str | None, str]] = []
    for start_line, end_line, expected_sha, body in replacements:
        if end_line > len(lines):
            raise SystemExit(f"Line replacement range is outside the target: {start_line}-{end_line}")
        spans.append((start_line - 1, end_line, expected_sha, body))
    spans.sort(key=lambda item: item[0], reverse=True)
    previous_start = len(lines) + 1
    for start, end, expected_sha, body in spans:
        if end > previous_start:
            raise SystemExit(f"Line replacement ranges overlap: {start + 1}-{end}")
        original_span = lines[start:end]
        if expected_sha and span_sha256(original_span) != expected_sha:
            raise SystemExit(f"Line replacement span hash is stale: {start + 1}-{end}")
        replacement_lines = body.rstrip("\n").split("\n")
        if original_span and original_span[-1].strip() == "" and (not replacement_lines or replacement_lines[-1].strip() != ""):
            replacement_lines.append("")
        lines[start:end] = replacement_lines
        previous_start = start
    result = "\n".join(lines)
    return result + "\n" if had_final_newline or result else result


def extract_replacement(proposal_path: Path, target: Path | None = None) -> str:
    line_blocks = line_replacements(proposal_path)
    if line_blocks:
        if target is None:
            raise SystemExit("Line replacement proposals require a resolved target sidecar.")
        return apply_line_replacements(target.read_text(encoding="utf-8", errors="replace"), line_blocks)
    replacements = section_replacements(proposal_path)
    if replacements:
        if target is None:
            raise SystemExit("Section replacement proposals require a resolved target sidecar.")
        return apply_section_replacements(target.read_text(encoding="utf-8", errors="replace"), replacements)
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


def detect_line_ending(path: Path) -> str:
    if not path.exists():
        return "\n"
    data = path.read_bytes()
    crlf_count = data.count(b"\r\n")
    lf_count = data.count(b"\n") - crlf_count
    return "\r\n" if crlf_count > lf_count else "\n"


def line_ending_name(newline: str) -> str:
    return "crlf" if newline == "\r\n" else "lf"


def normalize_line_endings(text: str, newline: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.replace("\n", newline)


def apply_proposal(proposal_path: Path, target: Path, output: Path | None, *, evidence_mode: str) -> Path:
    replacement = extract_replacement(proposal_path, target)
    governed = mark_auto_repaired(replacement, needs_review=True)
    governed = ensure_field(governed, "repair_evidence_mode", evidence_mode)
    governed = ensure_field(governed, "repair_ai_confidence", "unverified")
    destination = (output or target).resolve()
    source_for_newline = destination if destination.exists() else target
    governed = normalize_line_endings(governed, detect_line_ending(source_for_newline))
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(governed)
        if destination.exists():
            os.chmod(temp_name, destination.stat().st_mode)
        Path(temp_name).replace(destination)
    except Exception:
        try:
            Path(temp_name).unlink()
        except OSError:
            pass
        raise
    return destination


def main() -> int:
    configure_stdout()
    parser = argparse.ArgumentParser(description="Build or apply a Student OS AI import repair case.")
    parser.add_argument("--queue-item", required=True, help="Queue item id, queue relative path, or sidecar path")
    parser.add_argument("--queue", help="Explicit queue.json path")
    parser.add_argument("--include-verified", action="store_true", help="Allow direct sidecar case generation for verified files")
    parser.add_argument("--write-case", action="store_true", help="Write .student-os/import-repair/cases/<id>.md")
    parser.add_argument(
        "--evidence-mode",
        choices=sorted(EVIDENCE_MODES),
        default="auto",
        help="Evidence mode for this case; auto follows the queue recommendation.",
    )
    parser.add_argument("--output", help="Output path for --apply-proposal")
    parser.add_argument("--apply-proposal", help="Apply a proposal replacement block to the sidecar or --output")
    parser.add_argument("--ocr-evidence", help="Existing OCR text/markdown artifact to bind for ocr-assisted evidence")
    parser.add_argument(
        "--include-markdown",
        action="store_true",
        help="Include full case markdown in JSON output. By default --write-case --json returns compact metadata only.",
    )
    parser.add_argument("--json", action="store_true", help="Print structured result")
    args = parser.parse_args()

    queue_path = Path(args.queue).expanduser() if args.queue else None
    root, item, target = resolve_queue_item(
        args.queue_item,
        queue_path=queue_path,
        cwd=Path.cwd(),
        include_verified=args.include_verified,
    )

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

    ocr_evidence = Path(args.ocr_evidence).expanduser() if args.ocr_evidence else None
    evidence_payload = prepare_evidence(root, item, evidence_mode=args.evidence_mode, ocr_evidence=ocr_evidence)
    case_json = write_case_json(root, item, evidence_payload)
    markdown = render_case(root, item, target, evidence_payload)
    case_path = write_case(root, item, markdown) if args.write_case else None
    payload = {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "item_id": item.get("id", ""),
        "target": item.get("path", ""),
        "target_sha256": item.get("content_sha256", ""),
        "primary_risk": item.get("primary_risk", {}),
        "blocking_risk_lines": item.get("blocking_risk_lines", []),
        "target_section": item.get("target_section", {}),
        "repair_scope_required": item.get("repair_scope_required", ""),
        "single_section_candidate": item.get("single_section_candidate", False),
        "case_written": bool(case_path),
        "case_path": json_path(case_path) if case_path else "",
        "case_json": json_path(case_json),
        "evidence": evidence_payload,
        "queue_item": {
            "id": item.get("id", ""),
            "path": item.get("path", ""),
            "relative_path": item.get("relative_path", ""),
            "content_sha256": item.get("content_sha256", ""),
            "risk_codes": item.get("risk_codes", []),
            "primary_risk": item.get("primary_risk", {}),
            "blocking_risk_lines": item.get("blocking_risk_lines", []),
            "target_section": item.get("target_section", {}),
            "repair_scope_required": item.get("repair_scope_required", ""),
            "single_section_candidate": item.get("single_section_candidate", False),
            "repair_class": item.get("repair_class", ""),
            "recommended_evidence_mode": item.get("recommended_evidence_mode", ""),
            "blocked": item.get("blocked", ""),
        },
        "proposal_metadata": {
            "schema_version": PROPOSAL_SCHEMA_VERSION,
            "target": json_path(target),
            "target_sha256": item.get("content_sha256") or file_sha256(target),
            "case_json": json_path(case_json),
            "case_sha256": case_sha256(build_case_payload(item, evidence_payload)),
            "evidence_sha256": object_sha256(evidence_payload),
            "evidence_mode": evidence_payload.get("mode", "text-only"),
        },
        "markdown_omitted": bool(case_path and not args.include_markdown),
    }
    if args.include_markdown or not case_path:
        payload["markdown"] = markdown
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif case_path:
        print(case_path)
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
