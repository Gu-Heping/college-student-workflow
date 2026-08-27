#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from import_governance import (
    LEGACY_REPAIRED,
    NEEDS_HUMAN_REVIEW,
    VERIFIED,
    diagnose_import_risks,
    frontmatter_value,
    is_verified,
    read_frontmatter,
)


STATE_DIR = Path(".student-os") / "import-repair"
QUEUE_NAME = "queue.json"
SCHEMA_VERSION = "import-repair-queue/v1"
SKIP_DIRS = {".git", ".student-os", "node_modules", "__pycache__"}
FORMAT_RISKS = {
    "unicode-escape",
    "question-heading-promoted",
    "control-character",
    "latex-nonumber",
    "latex-binom-fragment",
    "latex-left-right-unbalanced",
    "math-dollar-unbalanced",
}
SEMANTIC_RISKS = {
    "mojibake-replacement-char",
    "low-cjk-density",
    "lossy-ocr-placeholder",
    "non-utf8-import",
    "ocr-symbol-garbage",
}
SOLUTION_LEAD_RE = re.compile(r"(?m)^\s*(?:解|证明|答)[:：]")
QUESTION_STEM_RE = re.compile(r"(题干|已知|求证|设|证明|计算|求)")


def json_path(path: Path) -> str:
    return str(path.resolve())


def stable_id(root: Path, path: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = path.resolve().as_posix()
    digest = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:10]
    return f"import-repair-{digest}"


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def read_markdown(path: Path) -> tuple[str, bool]:
    try:
        return path.read_text(encoding="utf-8"), False
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace"), True


def read_markdown_header(path: Path, *, max_bytes: int = 65536) -> str:
    with path.open("rb") as handle:
        return handle.read(max_bytes).decode("utf-8", errors="replace")


def decode_yaml_path(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda match: chr(int(match.group(1), 16)), value)


def resolve_declared_path(value: str, *, base: Path) -> Path | None:
    decoded = decode_yaml_path(value)
    if not decoded:
        return None
    candidate = Path(os.path.expandvars(decoded)).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve()


def is_import_markdown(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".pdf.md") or name.endswith(".raw.md") or name.endswith(".pdf.raw.md")


def is_raw_import_markdown(path: Path) -> bool:
    return path.name.lower().endswith(".raw.md")


def is_repair_target_markdown(path: Path, header: str) -> bool:
    return (is_import_markdown(path) and not is_raw_import_markdown(path)) or bool(frontmatter_value(header, "derived_from_import"))


def iter_import_markdown(root: Path) -> list[tuple[Path, str | None]]:
    if root.is_file():
        if root.suffix.lower() != ".md":
            return []
        header = read_markdown_header(root)
        return [(root, header)] if is_repair_target_markdown(root, header) else []
    paths: list[tuple[Path, str | None]] = []
    for path in root.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        header = read_markdown_header(path)
        if is_repair_target_markdown(path, header):
            paths.append((path, header))
    return sorted(paths, key=lambda item: item[0].as_posix().lower())


def find_repair_summary(path: Path) -> Path | None:
    stem = path.stem
    candidates = [
        path.with_name(f"{stem}-repair-summary.md"),
        path.with_name(f"{path.name}-repair-summary.md"),
    ]
    if stem.endswith(".pdf"):
        candidates.append(path.with_name(f"{stem[:-4]}-repair-summary.md"))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def raw_sibling(path: Path, frontmatter: dict[str, str], *, boundary_root: Path | None = None) -> Path | None:
    candidate = resolve_declared_path(frontmatter.get("derived_from_import", ""), base=path.parent)
    if (
        candidate
        and candidate.exists()
        and candidate.suffix.lower() == ".md"
        and (boundary_root is None or is_relative_to(candidate, boundary_root))
    ):
        return candidate.resolve()
    candidates = [
        path.with_name(f"{path.stem}.raw.md"),
        path.with_name(path.name.removesuffix(".md") + ".raw.md"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def source_path_for(path: Path, frontmatter: dict[str, str]) -> Path | None:
    source_path = resolve_declared_path(frontmatter.get("source_file", ""), base=path.parent)
    if source_path and source_path.exists():
        return source_path
    for candidate in [
        path.with_suffix(""),
        path.with_name(path.name.removesuffix(".md")),
        path.parent / "试卷" / path.name.removesuffix(".md"),
    ]:
        if candidate.exists():
            return candidate.resolve()
    return source_path


def pair_sidecar(path: Path) -> Path | None:
    name = path.name
    tokens = ["参考答案", "答案", "解析", "复习版"]
    candidates: list[Path] = []
    if any(token in name for token in tokens):
        base = name
        for token in tokens:
            base = base.replace(token, "")
        candidates.extend(path.parent.glob(f"*{base}"))
        candidates.extend(path.parent.glob(f"*{base.replace('.pdf.md', '')}*.pdf.md"))
    else:
        stem = name.removesuffix(".pdf.md").removesuffix(".PDF.md")
        candidates.extend(path.parent.glob(f"{stem}*答案*.pdf.md"))
        candidates.extend(path.parent.glob(f"{stem}*参考答案*.pdf.md"))
    for candidate in sorted(set(candidates), key=lambda item: item.name):
        if candidate.resolve() != path.resolve() and candidate.exists():
            return candidate.resolve()
    return None


def candidate_pages_for(text: str, snippets: list[dict[str, object]]) -> list[int]:
    pages: set[int] = set()
    page_markers: list[tuple[int, int]] = []
    for index, line in enumerate(text.splitlines(), start=1):
        match = re.search(r"(?:^##\s+Page|<!--\s*PART\s+\d+:\s+pages)\s+(\d+)", line, flags=re.I)
        if match:
            page_markers.append((index, int(match.group(1))))
    for snippet in snippets:
        line = snippet.get("line")
        if not isinstance(line, int):
            continue
        previous = [page for marker_line, page in page_markers if marker_line <= line]
        if previous:
            pages.add(previous[-1])
    return sorted(page for page in pages if page > 0)[:6]


def has_question_stem(text: str) -> bool:
    head = SOLUTION_LEAD_RE.sub("", text[:3000], count=1)
    return bool(QUESTION_STEM_RE.search(head))


def section_id(title: str, line: int) -> str:
    digest = hashlib.sha1(f"{line}:{title}".encode("utf-8", errors="replace")).hexdigest()[:8]
    return f"section-{line}-{digest}"


def split_sections(text: str) -> list[dict[str, object]]:
    lines = text.splitlines()
    starts: list[tuple[int, str]] = []
    pattern = re.compile(r"^\s*(?:#{1,3}\s*)?(?:第?\s*)?(?:[一二三四五六七八九十]+|[0-9]+)[\.、．)]")
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if re.match(r"^#{1,3}\s+\S", stripped) or pattern.match(stripped):
            starts.append((index, stripped[:120]))
    if not starts:
        return []
    sections: list[dict[str, object]] = []
    for offset, (start_line, title) in enumerate(starts):
        end_line = starts[offset + 1][0] - 1 if offset + 1 < len(starts) else len(lines)
        body = "\n".join(lines[start_line - 1 : min(end_line, start_line + 11)])
        sections.append(
            {
                "id": section_id(title, start_line),
                "title": title,
                "start_line": start_line,
                "end_line": end_line,
                "excerpt": body,
            }
        )
    return sections[:24]


def sections_for_snippets(sections: list[dict[str, object]], snippets: list[dict[str, object]]) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    seen: set[str] = set()
    for snippet in snippets:
        line = snippet.get("line")
        if not isinstance(line, int):
            continue
        for section in sections:
            start = section.get("start_line")
            end = section.get("end_line")
            if isinstance(start, int) and isinstance(end, int) and start <= line <= end:
                section_key = str(section["id"])
                if section_key not in seen:
                    selected.append(section)
                    seen.add(section_key)
                break
    return selected


def pdf_text_candidate_pages(source_path: Path | None, snippets: list[dict[str, object]]) -> list[int]:
    if source_path is None or not source_path.exists() or source_path.suffix.lower() != ".pdf":
        return []
    probes: list[str] = []
    for snippet in snippets:
        excerpt_text = str(snippet.get("excerpt", ""))
        for line in excerpt_text.splitlines():
            normalized = re.sub(r"\s+", " ", line).strip()
            if len(normalized) >= 12 and not re.search(r"[�□\\]", normalized):
                probes.append(normalized[:80])
                break
    if not probes:
        return []
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError:
        return []
    pages: set[int] = set()
    try:
        document = fitz.open(str(source_path))
    except Exception:
        return []
    try:
        for page_index in range(document.page_count):
            page_text = re.sub(r"\s+", " ", document.load_page(page_index).get_text("text"))
            if any(probe in page_text for probe in probes):
                pages.add(page_index + 1)
    finally:
        document.close()
    return sorted(pages)[:6]


def classify_evidence(
    path: Path,
    text: str,
    risks: list[dict[str, object]],
    frontmatter: dict[str, str],
    snippets: list[dict[str, object]],
    *,
    boundary_root: Path,
) -> dict[str, object]:
    risk_codes = {str(risk.get("code", "")) for risk in risks}
    source_path = source_path_for(path, frontmatter)
    raw_path = raw_sibling(path, frontmatter, boundary_root=boundary_root)
    summary_path = find_repair_summary(path)
    paired = pair_sidecar(path)
    source_exists = bool(source_path and source_path.exists())
    raw_exists = bool(raw_path and raw_path.exists())
    paired_exists = bool(paired and paired.exists())
    candidate_pages = candidate_pages_for(text, snippets)

    if risk_codes <= {"unicode-escape", "legacy-repaired-unverified", "frontmatter-repair-risk"}:
        repair_class = "metadata-only"
        recommended_mode = "text-only"
        blocked = ""
    elif "answer-missing-question-stem" in risk_codes:
        repair_class = "answer-paper-crosscheck"
        recommended_mode = "text-only" if paired_exists or raw_exists else "vision-assisted"
        blocked = "" if paired_exists or raw_exists or source_exists else "unrecoverable-with-current-evidence"
    elif risk_codes & SEMANTIC_RISKS:
        repair_class = "semantic-text-repair"
        recommended_mode = "text-only" if raw_exists else "vision-assisted"
        blocked = "" if raw_exists or source_exists else "unrecoverable-with-current-evidence"
    elif risk_codes & FORMAT_RISKS:
        repair_class = "format-only"
        recommended_mode = "text-only"
        blocked = ""
    elif source_exists and not raw_exists:
        repair_class = "requires-ocr"
        recommended_mode = "ocr-assisted"
        blocked = ""
    else:
        repair_class = "unrecoverable-with-current-evidence"
        recommended_mode = "text-only"
        blocked = "unrecoverable-with-current-evidence"

    if recommended_mode == "vision-assisted" and not source_exists:
        blocked = "requires-vision-evidence"
    if recommended_mode == "vision-assisted":
        candidate_pages = sorted(set(candidate_pages) | set(pdf_text_candidate_pages(source_path, snippets)))[:6]

    return {
        "class": repair_class,
        "recommended_mode": recommended_mode,
        "blocked": blocked,
        "source_pdf": {
            "declared": decode_yaml_path(frontmatter.get("source_file", "")),
            "path": json_path(source_path) if source_path else "",
            "exists": source_exists,
            "status": "available" if source_exists else ("missing" if source_path else "undeclared"),
        },
        "raw_import": {
            "declared": decode_yaml_path(frontmatter.get("derived_from_import", "")),
            "path": json_path(raw_path) if raw_path else "",
            "exists": raw_exists,
            "status": "available" if raw_exists else ("missing" if frontmatter.get("derived_from_import", "") else "undeclared"),
        },
        "repair_summary": {
            "path": json_path(summary_path) if summary_path else "",
            "exists": summary_path is not None,
            "status": "available" if summary_path else "missing",
        },
        "paired_sidecar": {
            "path": json_path(paired) if paired else "",
            "exists": paired_exists,
            "status": "available" if paired_exists else "missing",
        },
        "candidate_pages": candidate_pages,
        "source_evidence": "available" if source_exists or raw_exists or paired_exists else "unavailable",
        "notes": [
            "Use OCR to create or refresh text evidence; do not overwrite repaired markdown directly.",
            "Use vision evidence only for local page/crop grounding, not as a substitute for human verification.",
        ],
    }


def risk_line_patterns(code: str) -> list[re.Pattern[str]]:
    patterns: dict[str, list[str]] = {
        "mojibake-replacement-char": [r"�"],
        "unicode-escape": [r"\\u[0-9a-fA-F]{4}"],
        "latex-nonumber": [r"\\nonumber\b"],
        "latex-binom-fragment": [r"\\binom\b"],
        "latex-left-right-unbalanced": [r"\\(?:left|right)\b"],
        "math-dollar-unbalanced": [r"\$"],
        "lossy-ocr-placeholder": [r"□"],
        "question-heading-promoted": [r"^##\s+[一二三四五六七八九十]+[\.、]"],
        "answer-missing-question-stem": [r"^\s*(?:解|证明|答)[:：]"],
        "control-character": [r"[\x00-\x08\x0b\x0c\x0e-\x1f]"],
        "ocr-symbol-garbage": [r"\\boxplus|\\neg\s*\\neg|\\\s+Y(?:\s+Y)+"],
        "legacy-repaired-unverified": [r"^repair_status:\s*repaired\b"],
        "frontmatter-repair-risk": [r"^repair_risk:\s*needs-human-review\b"],
        "non-utf8-import": [r"�"],
    }
    return [re.compile(pattern) for pattern in patterns.get(code, [re.escape(code)])]


def first_snippet_for_risk(text: str, code: str, *, radius: int = 2) -> dict[str, object] | None:
    lines = text.splitlines()
    if code == "low-cjk-density":
        parsed = read_frontmatter(text)
        body_start = text[: parsed[2]].count("\n") if parsed else 0
        for body_index, line in enumerate(lines[body_start:], start=body_start):
            stripped = line.strip()
            if not stripped or re.match(r"^---$|^##\s+Page\b|^<!--", stripped, flags=re.I):
                continue
            visible = re.sub(r"\s+", "", stripped)
            cjk_count = len(re.findall(r"[\u4e00-\u9fff]", visible))
            if len(visible) >= 80 and cjk_count == 0:
                start = max(0, body_index - radius)
                end = min(len(lines), body_index + radius + 1)
                return {
                    "code": code,
                    "line": body_index + 1,
                    "excerpt": "\n".join(lines[start:end]),
                }
        return None
    for index, line in enumerate(lines):
        if any(pattern.search(line) for pattern in risk_line_patterns(code)):
            start = max(0, index - radius)
            end = min(len(lines), index + radius + 1)
            return {
                "code": code,
                "line": index + 1,
                "excerpt": "\n".join(lines[start:end]),
            }
    return None


def extra_risks(path: Path, text: str, frontmatter: dict[str, str], *, decode_error: bool) -> list[dict[str, object]]:
    risks: list[dict[str, object]] = []
    if decode_error:
        risks.append({"code": "non-utf8-import", "count": 1})
    repair_status = frontmatter.get("repair_status", "").lower()
    verify_status = frontmatter.get("verify_status", "").lower()
    if repair_status == LEGACY_REPAIRED and verify_status != VERIFIED:
        risks.append({"code": "legacy-repaired-unverified", "count": 1})
    if frontmatter.get("repair_risk", "").lower() == NEEDS_HUMAN_REVIEW:
        risks.append({"code": "frontmatter-repair-risk", "count": 1})

    heading_count = len(re.findall(r"(?m)^##\s+[一二三四五六七八九十]+[\.、]", text))
    if heading_count:
        risks.append({"code": "question-heading-promoted", "count": heading_count})

    control_count = len(re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text))
    if control_count:
        risks.append({"code": "control-character", "count": control_count})

    symbol_garbage_count = len(re.findall(r"\\boxplus|\\neg\s*\\neg|\\\s+Y(?:\s+Y)+", text))
    if symbol_garbage_count:
        risks.append({"code": "ocr-symbol-garbage", "count": symbol_garbage_count})

    if re.search(r"(答案|参考答案|解析)", path.name) and re.search(r"(?m)^\s*(?:解|证明|答)[:：]", text):
        if not has_question_stem(text):
            risks.append({"code": "answer-missing-question-stem", "count": 1})
    return risks


def merge_risks(risks: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: dict[str, dict[str, object]] = {}
    order: list[str] = []
    for risk in risks:
        code = str(risk.get("code", "")).strip()
        if not code:
            continue
        if code not in merged:
            merged[code] = {"code": code}
            order.append(code)
        target = merged[code]
        for key, value in risk.items():
            if key == "code":
                continue
            if key == "count" and isinstance(value, int):
                target[key] = int(target.get(key, 0)) + value
            else:
                target.setdefault(key, value)
    return [merged[code] for code in order]


def build_queue_item(root: Path, path: Path, *, text: str | None = None, decode_error: bool | None = None) -> dict[str, object] | None:
    if text is None or decode_error is None:
        text, decode_error = read_markdown(path)
    parsed = read_frontmatter(text)
    frontmatter = parsed[0] if parsed else {}
    risks = merge_risks([*diagnose_import_risks(text), *extra_risks(path, text, frontmatter, decode_error=decode_error)])
    if not risks:
        return None

    summary_path = find_repair_summary(path)
    raw_path = raw_sibling(path, frontmatter, boundary_root=root)
    snippets = [
        snippet
        for risk in risks
        if (snippet := first_snippet_for_risk(text, str(risk["code"]))) is not None
    ]
    evidence = classify_evidence(path, text, risks, frontmatter, snippets, boundary_root=root)
    sections = split_sections(text)
    suspect_sections = sections_for_snippets(sections, snippets)
    item = {
        "schema_version": SCHEMA_VERSION,
        "id": stable_id(root, path),
        "path": json_path(path),
        "relative_path": relative_path(root, path),
        "content_sha256": file_sha256(path),
        "source_file": decode_yaml_path(frontmatter.get("source_file", "")),
        "raw_import": json_path(raw_path) if raw_path else "",
        "repair_summary": json_path(summary_path) if summary_path else "",
        "repair_status": frontmatter.get("repair_status", ""),
        "verify_status": frontmatter.get("verify_status", ""),
        "verified": is_verified(text),
        "frontmatter": frontmatter,
        "risk_codes": [str(risk["code"]) for risk in risks],
        "risks": risks,
        "snippets": snippets[:8],
        "sections": sections,
        "suspect_sections": suspect_sections,
        "evidence": evidence,
        "repair_class": evidence["class"],
        "recommended_evidence_mode": evidence["recommended_mode"],
        "blocked": evidence["blocked"],
        "suggested_next_step": "Generate an AI repair case, edit with source evidence, then keep verify_status: unverified until human source review.",
    }
    return item


def build_queue(root: Path, *, include_verified: bool = False) -> dict[str, object]:
    root = root.resolve()
    state_root = root.parent if root.is_file() else root
    scanned = 0
    skipped_verified = 0
    items: list[dict[str, object]] = []
    for path, header in iter_import_markdown(root):
        scanned += 1
        if header is not None and is_verified(header) and not include_verified:
            skipped_verified += 1
            continue
        text, decode_error = read_markdown(path)
        if is_verified(text) and not include_verified:
            skipped_verified += 1
            continue
        item = build_queue_item(state_root, path, text=text, decode_error=decode_error)
        if item:
            items.append(item)

    queue_path = state_root / STATE_DIR / QUEUE_NAME
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "target_root": json_path(state_root),
        "queue_path": json_path(queue_path),
        "counts": {
            "scanned": scanned,
            "items": len(items),
            "skipped_verified": skipped_verified,
        },
        "items": items,
    }


def write_queue(payload: dict[str, object]) -> Path:
    queue_path = Path(str(payload["queue_path"]))
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return queue_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an AI-assisted import repair queue for markdown sidecars.")
    parser.add_argument("target", help="Learning vault or imported markdown folder/file to scan")
    parser.add_argument("--include-verified", action="store_true", help="Include files marked verify_status: verified")
    parser.add_argument(
        "--classify-evidence",
        action="store_true",
        help="Compatibility flag; queue items always include evidence classification.",
    )
    parser.add_argument("--write-queue", action="store_true", help="Write .student-os/import-repair/queue.json")
    parser.add_argument("--json", action="store_true", help="Print the queue as JSON")
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
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(payload["error"])
        return 2
    if target.is_file() and target.suffix.lower() != ".md":
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "stage": "resolve-target",
            "error": "Target file must be a markdown sidecar.",
            "target": json_path(target),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(payload["error"])
        return 2
    payload = build_queue(target, include_verified=args.include_verified)
    if args.write_queue:
        write_queue(payload)
    if args.json or not args.write_queue:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["queue_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
