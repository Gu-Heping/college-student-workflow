#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import hashlib
import json
import os
import re
import subprocess
from collections.abc import Iterator
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
COMPACT_QUEUE_NAME = "queue.compact.json"
SCHEMA_VERSION = "import-repair-queue/v1"
SKIP_DIRS = {".git", ".student-os", "node_modules", "__pycache__"}
FORMAT_RISKS = {
    "unicode-escape",
    "question-heading-promoted",
    "control-character",
    "latex-nonumber",
    "latex-binom-fragment",
    "latex-left-right-unbalanced",
    "latex-array-column-mismatch",
    "latex-math-span-brace-unbalanced",
    "latex-dangling-close-before-dollar",
    "latex-array-wrapper-malformed",
    "obsidian-inline-array-render-risk",
    "display-math-delimiter-not-standalone",
    "inline-math-delimiter-space",
    "math-dollar-unbalanced",
}
HEURISTIC_RISKS = {"math-dollar-unbalanced", "math-dollar-heuristic-suspect"}
BLOCKING_RISKS = {
    "math-dollar-odd-line",
    "latex-left-right-unbalanced",
    "latex-array-column-mismatch",
    "latex-math-span-brace-unbalanced",
    "latex-dangling-close-before-dollar",
    "latex-array-wrapper-malformed",
    "obsidian-inline-array-render-risk",
    "display-math-delimiter-not-standalone",
    "inline-math-delimiter-space",
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


def configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
        sys.stderr.reconfigure(encoding="utf-8", newline="\n")
    except AttributeError:
        pass


def relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def git_root_for(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip()).resolve()


def state_root_for_scan(target: Path) -> Path:
    target = target.resolve()
    git_root = git_root_for(target)
    if git_root is not None and (git_root / ".student-os").exists():
        return git_root
    start = target if target.is_dir() else target.parent
    for parent in [start, *start.parents]:
        if (parent / ".student-os").exists():
            return parent.resolve()
    return start.resolve()


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


def iter_import_markdown(root: Path) -> Iterator[tuple[Path, str | None]]:
    if root.is_file():
        if root.suffix.lower() != ".md":
            return
        header = read_markdown_header(root)
        if is_repair_target_markdown(root, header):
            yield root, header
        return
    paths = sorted(
        (path for path in root.rglob("*.md") if not any(part in SKIP_DIRS for part in path.parts)),
        key=lambda item: item.as_posix().lower(),
    )
    for path in paths:
        header = read_markdown_header(path)
        if is_repair_target_markdown(path, header):
            yield path, header


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
    parsed = read_frontmatter(text)
    body = text[parsed[2] :] if parsed else text
    solution_match = SOLUTION_LEAD_RE.search(body)
    candidate = body[: solution_match.start() if solution_match else min(len(body), 3000)]
    structural_patterns = [
        r"(?m)^\s*(?:#{1,3}\s*)?(?:第?\s*)?(?:[一二三四五六七八九十]+|[0-9]+)[\.、．)]\s*\S+",
        r"(?:题干|已知|求证|本题|试证明)",
        r"(?:求|计算)[^。\n]{0,80}(?:值|解|概率|面积|体积|矩阵|特征|导数|积分)",
    ]
    return any(re.search(pattern, candidate) for pattern in structural_patterns)


def section_id(title: str, line: int) -> str:
    digest = hashlib.sha1(f"{line}:{title}".encode("utf-8", errors="replace")).hexdigest()[:8]
    return f"section-{line}-{digest}"


QUESTION_SECTION_RE = re.compile(
    r"^\s*(?:#{1,3}\s*)?"
    r"(?:(?:第\s*)?(?:[一二三四五六七八九十]+|[0-9]+)\s*(?:[\.、．)]|[（(]\s*\d+\s*分\s*[）)]\s*[\.、．:]?)|"
    r"[（(]\s*[0-9一二三四五六七八九十]+\s*[）)])"
)


def split_sections(text: str) -> list[dict[str, object]]:
    lines = text.splitlines()
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if re.match(r"^#{1,3}\s+\S", stripped) or QUESTION_SECTION_RE.match(stripped):
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
        "latex-array-column-mismatch": [r"\\begin\{array\}"],
        "latex-math-span-brace-unbalanced": [r"(?<!\\)(?<!\$)\$(?!\$).*?(?<!\\)(?<!\$)\$(?!\$)"],
        "latex-dangling-close-before-dollar": [r"}\s*(?<!\\)\$\s*$"],
        "latex-array-wrapper-malformed": [r"\\begin\{array\}\s*\{[^}]*\}\s*\{"],
        "obsidian-inline-array-render-risk": [r"(?<!\\)\$.*\\begin\{(?:array|matrix|[pbvBV]?matrix)\}.*(?<!\\)\$"],
        "display-math-delimiter-not-standalone": [r"(?<!\\)\$\$"],
        "inline-math-delimiter-space": [r"(?<!\\)(?<!\$)\$(?!\$)\s|\s(?<!\\)(?<!\$)\$(?!\$)"],
        "math-dollar-unbalanced": [r"\$"],
        "math-dollar-heuristic-suspect": [r"\$"],
        "math-dollar-odd-line": [r"\$"],
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
        aggregate = ""
        aggregate_start = body_start
        for body_index, line in enumerate(lines[body_start:], start=body_start):
            stripped = line.strip()
            if not stripped or re.match(r"^---$|^##\s+Page\b|^<!--", stripped, flags=re.I):
                aggregate = ""
                aggregate_start = body_index + 1
                continue
            visible = re.sub(r"\s+", "", stripped)
            cjk_count = len(re.findall(r"[\u4e00-\u9fff]", visible))
            if cjk_count:
                aggregate = ""
                aggregate_start = body_index + 1
                continue
            if not aggregate:
                aggregate_start = body_index
            aggregate += visible
            if len(aggregate) >= 80:
                start = max(0, aggregate_start - radius)
                end = min(len(lines), body_index + radius + 1)
                return {
                    "code": code,
                    "line": aggregate_start + 1,
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


def risk_metadata(code: str) -> dict[str, object]:
    metadata: dict[str, dict[str, object]] = {
        "unicode-escape": {
            "severity": "info",
            "confidence": "high",
            "actionability": "safe-autofix",
            "safe_fix_kind": "decode-yaml-unicode-escapes",
            "description": "YAML unicode escapes are usually semantically valid but hard to read.",
        },
        "legacy-repaired-unverified": {
            "severity": "warning",
            "confidence": "high",
            "actionability": "metadata-governance",
            "safe_fix_kind": "mark-auto-repaired-unverified",
            "description": "Legacy repaired means machine repaired, not human verified.",
        },
        "frontmatter-repair-risk": {
            "severity": "warning",
            "confidence": "high",
            "actionability": "human-review-required",
            "safe_fix_kind": "preserve-risk-marker",
            "description": "The sidecar already declares a human-review risk.",
        },
        "question-heading-promoted": {
            "severity": "warning",
            "confidence": "medium",
            "actionability": "local-format-repair",
            "safe_fix_kind": "demote-promoted-question-heading",
            "description": "A question heading may have been promoted to document structure.",
        },
        "control-character": {
            "severity": "warning",
            "confidence": "high",
            "actionability": "localized-text-repair",
            "safe_fix_kind": "replace-control-character-with-source-grounded-token",
            "description": "A control character is present in imported markdown.",
        },
        "latex-left-right-unbalanced": {
            "severity": "error",
            "confidence": "high",
            "actionability": "localized-render-repair",
            "safe_fix_kind": "prefer-display-math-and-structural-array-rewrite",
            "description": "A LaTeX left/right delimiter mismatch is render-blocking; do not stop at token balancing when the formula is a matrix.",
            "suggestion": "For matrix/array formulas, prefer a display math block and a structurally correct array column spec instead of only swapping delimiters.",
        },
        "latex-array-column-mismatch": {
            "severity": "error",
            "confidence": "high",
            "actionability": "localized-render-repair",
            "safe_fix_kind": "align-array-column-spec-with-row-cells",
            "description": "An array column declaration does not match the row cell counts, which can break Obsidian/MathJax rendering.",
            "suggestion": "Count the cells in each row and change the array spec to match, e.g. ccc for three columns or ccc|cc for an augmented matrix.",
        },
        "latex-math-span-brace-unbalanced": {
            "severity": "error",
            "confidence": "high",
            "actionability": "localized-render-repair",
            "safe_fix_kind": "repair-local-math-span-brace-structure",
            "description": "An inline math span has obvious unbalanced braces, which usually renders literally or breaks the nearby formula.",
            "suggestion": "Inspect only the reported math span and remove or add the local brace that is clearly unmatched; do not rewrite unrelated content.",
        },
        "latex-dangling-close-before-dollar": {
            "severity": "error",
            "confidence": "high",
            "actionability": "localized-render-repair",
            "safe_fix_kind": "repair-dangling-math-delimiter",
            "description": "A line ends with a close brace immediately before a lone dollar delimiter, a common sign of broken imported math.",
            "suggestion": "Inspect the local line and remove the stray brace or restore the missing math opener based on nearby visible content.",
        },
        "latex-array-wrapper-malformed": {
            "severity": "error",
            "confidence": "high",
            "actionability": "localized-render-repair",
            "safe_fix_kind": "repair-array-wrapper",
            "description": "An array environment appears to have an extra brace group after the column spec, e.g. \\begin{array}{r}{...}.",
            "suggestion": "Use a normal array form \\begin{array}{...} rows \\end{array}; keep delimiters and row cells structurally consistent.",
        },
        "obsidian-inline-array-render-risk": {
            "severity": "error",
            "confidence": "high",
            "actionability": "localized-render-repair",
            "safe_fix_kind": "convert-long-inline-array-to-display-math",
            "description": "A long inline matrix/array formula is likely to appear as literal TeX in Obsidian; use a display math block with standalone delimiters.",
            "suggestion": "Convert the local inline `$...\\begin{array}...$` span to a display math block whose opening and closing `$$` are each alone on their own line.",
        },
        "display-math-delimiter-not-standalone": {
            "severity": "error",
            "confidence": "high",
            "actionability": "localized-render-repair",
            "safe_fix_kind": "put-display-math-delimiters-on-standalone-lines",
            "description": "A display math delimiter is glued to prose, which can leave nearby LaTeX outside a proper display block in Obsidian.",
            "suggestion": "Move each `$$` delimiter to its own line without changing formula content.",
        },
        "inline-math-delimiter-space": {
            "severity": "error",
            "confidence": "high",
            "actionability": "localized-render-repair",
            "safe_fix_kind": "trim-inline-math-delimiter-adjacent-space",
            "description": "Obsidian may render inline math literally when whitespace touches the inside of `$...$` delimiters.",
            "suggestion": "Remove only the whitespace immediately inside inline `$...$` delimiters; do not rewrite formula content.",
        },
        "math-dollar-unbalanced": {
            "severity": "warning",
            "confidence": "low",
            "actionability": "inspect-local-snippets-only",
            "safe_fix_kind": "do-not-debug-detector",
            "description": "Heuristic dollar count is odd; inspect localized snippets instead of reading tool source.",
        },
        "math-dollar-heuristic-suspect": {
            "severity": "warning",
            "confidence": "low",
            "actionability": "inspect-local-snippets-only",
            "safe_fix_kind": "normalize-obvious-inline-math-delimiters",
            "description": "Inline math may be valid but confuses the heuristic counter.",
        },
        "math-dollar-odd-line": {
            "severity": "error",
            "confidence": "medium",
            "actionability": "localized-render-repair",
            "safe_fix_kind": "repair-one-line-inline-math-boundary",
            "description": "A line has an odd number of unescaped dollar delimiters.",
        },
        "answer-missing-question-stem": {
            "severity": "warning",
            "confidence": "medium",
            "actionability": "paired-paper-crosscheck",
            "safe_fix_kind": "requires-source-or-paired-sidecar",
            "description": "An answer sidecar appears to start with a solution but no problem stem.",
        },
    }
    return metadata.get(
        code,
        {
            "severity": "warning",
            "confidence": "medium",
            "actionability": "inspect-local-snippets-only",
            "safe_fix_kind": "no-automatic-fix",
            "description": "Inspect the localized evidence before changing markdown.",
        },
    )


def enrich_risks(risks: list[dict[str, object]]) -> list[dict[str, object]]:
    enriched: list[dict[str, object]] = []
    for risk in risks:
        code = str(risk.get("code", "")).strip()
        if not code:
            continue
        enriched_risk = {**risk_metadata(code), **risk}
        enriched.append(enriched_risk)
    return enriched


def highest_severity(risks: list[dict[str, object]]) -> str:
    if any(risk.get("severity") == "error" for risk in risks):
        return "error"
    if any(risk.get("severity") == "warning" for risk in risks):
        return "warning"
    return "info"


def primary_risk(risks: list[dict[str, object]]) -> dict[str, object]:
    order = {"error": 3, "warning": 2, "info": 1}
    actionable = {"localized-render-repair": 3, "localized-text-repair": 2, "local-format-repair": 1}
    code_priority = {
        "obsidian-inline-array-render-risk": 5,
        "display-math-delimiter-not-standalone": 5,
        "inline-math-delimiter-space": 5,
        "latex-array-column-mismatch": 4,
        "latex-math-span-brace-unbalanced": 5,
        "latex-dangling-close-before-dollar": 5,
        "latex-array-wrapper-malformed": 5,
        "latex-left-right-unbalanced": 3,
        "math-dollar-odd-line": 2,
    }
    if not risks:
        return {}
    return max(
        risks,
        key=lambda risk: (
            order.get(str(risk.get("severity")), 0),
            actionable.get(str(risk.get("actionability")), 0),
            code_priority.get(str(risk.get("code")), 0),
            1 if risk.get("code") not in HEURISTIC_RISKS else 0,
        ),
    )


def blocking_risk_lines(risks: list[dict[str, object]], snippets: list[dict[str, object]]) -> list[int]:
    lines: set[int] = set()
    for risk in risks:
        if str(risk.get("code", "")) not in BLOCKING_RISKS:
            continue
        line = risk.get("line")
        if isinstance(line, int):
            lines.add(line)
        risk_lines = risk.get("lines")
        if isinstance(risk_lines, list):
            for value in risk_lines:
                if isinstance(value, int):
                    lines.add(value)
                elif isinstance(value, dict) and isinstance(value.get("line"), int):
                    lines.add(value["line"])
    for snippet in snippets:
        if str(snippet.get("code", "")) in BLOCKING_RISKS and isinstance(snippet.get("line"), int):
            lines.add(int(snippet["line"]))
    return sorted(lines)


def blocking_risk_count(risks: list[dict[str, object]]) -> int:
    total = 0
    for risk in risks:
        if str(risk.get("code", "")) not in BLOCKING_RISKS:
            continue
        count = risk.get("count")
        total += count if isinstance(count, int) and count > 0 else 1
    return total


def section_for_line(sections: list[dict[str, object]], line: int) -> dict[str, object] | None:
    for section in sections:
        start = section.get("start_line")
        end = section.get("end_line")
        if isinstance(start, int) and isinstance(end, int) and start <= line <= end:
            return section
    return None


def target_section_for_blocking_lines(sections: list[dict[str, object]], lines: list[int]) -> dict[str, object] | None:
    if not lines:
        return None
    matched = [section_for_line(sections, line) for line in lines]
    if any(section is None for section in matched):
        return None
    first = matched[0]
    if first is None:
        return None
    first_id = str(first.get("id", ""))
    if first_id and all(str(section.get("id", "")) == first_id for section in matched if section is not None):
        return first
    return None


def repair_scope_required_for(blocking_count: int, lines: list[int], target_section: dict[str, object] | None) -> str:
    if blocking_count == 0:
        return "metadata-or-nonblocking"
    if target_section is not None:
        return "single-section"
    if len(lines) > 1:
        return "widened"
    return "blocked"


def review_strategy_for(blocking_count: int, lines: list[int], target_section: dict[str, object] | None) -> str:
    if blocking_count == 0:
        return "metadata-or-nonblocking-review"
    if target_section is not None:
        return "single-local-section"
    return "blocked-or-split-into-smaller-cases"


def suggested_next_step_for(strategy: str) -> str:
    if strategy == "single-local-section":
        return "Generate one case and repair the local section that contains the blocking display/render issue; keep verify_status: unverified."
    if strategy == "blocked-or-split-into-smaller-cases":
        return "Create a blocked case or choose a smaller item/section; do not attempt a broad whole-file rewrite from this queue item."
    return "Handle metadata or nonblocking readability repairs only; do not claim human verification."


def build_queue_item(root: Path, path: Path, *, text: str | None = None, decode_error: bool | None = None) -> dict[str, object] | None:
    if text is None or decode_error is None:
        text, decode_error = read_markdown(path)
    parsed = read_frontmatter(text)
    frontmatter = parsed[0] if parsed else {}
    risks = merge_risks(
        [
            *diagnose_import_risks(text),
            *extra_risks(path, text, frontmatter, decode_error=decode_error),
        ]
    )
    if not risks:
        return None
    risks = enrich_risks(risks)

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
    blocking_lines = blocking_risk_lines(risks, snippets)
    blocking_count = blocking_risk_count(risks)
    target_section = target_section_for_blocking_lines(sections, blocking_lines)
    repair_scope_required = repair_scope_required_for(blocking_count, blocking_lines, target_section)
    review_strategy = review_strategy_for(blocking_count, blocking_lines, target_section)
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
        "highest_severity": highest_severity(risks),
        "primary_risk": primary_risk(risks),
        "snippets": snippets[:8],
        "sections": sections,
        "suspect_sections": suspect_sections,
        "blocking_risk_count": blocking_count,
        "blocking_risk_lines": blocking_lines,
        "target_section": target_section or {},
        "repair_scope_required": repair_scope_required,
        "single_section_candidate": review_strategy == "single-local-section",
        "review_strategy": review_strategy,
        "evidence": evidence,
        "repair_class": evidence["class"],
        "recommended_evidence_mode": evidence["recommended_mode"],
        "blocked": evidence["blocked"],
        "suggested_next_step": suggested_next_step_for(review_strategy),
    }
    return item


def risk_score(item: dict[str, object]) -> int:
    score = 0
    for risk in item.get("risks", []):
        if not isinstance(risk, dict):
            continue
        severity = risk.get("severity")
        actionability = risk.get("actionability")
        code = risk.get("code")
        if severity == "error":
            score += 100
        elif severity == "warning":
            score += 30
        else:
            score += 5
        if actionability in {"localized-render-repair", "localized-text-repair"}:
            score += 20
        if code in {
            "obsidian-inline-array-render-risk",
            "display-math-delimiter-not-standalone",
            "inline-math-delimiter-space",
            "latex-array-column-mismatch",
        }:
            score += 40
        if code == "unicode-escape":
            score -= 20
        if code in HEURISTIC_RISKS:
            score -= 10
    return score


def compact_item(item: dict[str, object], *, queue_path: str) -> dict[str, object]:
    risks = [risk for risk in item.get("risks", []) if isinstance(risk, dict)]
    highest = highest_severity(risks)
    item_id = str(item.get("id", ""))
    primary = item.get("primary_risk") if isinstance(item.get("primary_risk"), dict) else primary_risk(risks)
    snippets = [snippet for snippet in item.get("snippets", []) if isinstance(snippet, dict)]
    primary_code = str(primary.get("code", ""))
    primary_snippet = next((snippet for snippet in snippets if str(snippet.get("code", "")) == primary_code), snippets[0] if snippets else {})
    return {
        "id": item_id,
        "path": item.get("path", ""),
        "relative_path": item.get("relative_path", ""),
        "repair_class": item.get("repair_class", ""),
        "recommended_evidence_mode": item.get("recommended_evidence_mode", ""),
        "blocked": item.get("blocked", ""),
        "highest_severity": highest,
        "primary_risk": {
            "code": primary.get("code", ""),
            "severity": primary.get("severity", ""),
            "actionability": primary.get("actionability", ""),
            "safe_fix_kind": primary.get("safe_fix_kind", ""),
            "lines": primary.get("lines", []),
            "suggestion": primary.get("suggestion", ""),
        },
        "risk_codes": item.get("risk_codes", []),
        "blocking_risk_count": item.get("blocking_risk_count", 0),
        "blocking_risk_lines": item.get("blocking_risk_lines", []),
        "target_section": item.get("target_section", {}),
        "repair_scope_required": item.get("repair_scope_required", ""),
        "single_section_candidate": item.get("single_section_candidate", False),
        "review_strategy": item.get("review_strategy", ""),
        "primary_snippet": {
            "code": primary_snippet.get("code", ""),
            "line": primary_snippet.get("line", ""),
            "excerpt": primary_snippet.get("excerpt", ""),
        },
        "risks": [
            {
                "code": risk.get("code", ""),
                "severity": risk.get("severity", "warning"),
                "confidence": risk.get("confidence", "medium"),
                "actionability": risk.get("actionability", "inspect-local-snippets-only"),
                "safe_fix_kind": risk.get("safe_fix_kind", "no-automatic-fix"),
                "line": risk.get("line", ""),
                "count": risk.get("count", ""),
                "left": risk.get("left", ""),
                "right": risk.get("right", ""),
                "lines": risk.get("lines", []),
                "expected_columns": risk.get("expected_columns", ""),
                "actual_columns": risk.get("actual_columns", ""),
                "suggestion": risk.get("suggestion", ""),
            }
            for risk in risks
        ],
        "localized_snippet_count": len(item.get("snippets", [])) if isinstance(item.get("snippets"), list) else 0,
        "suspect_section_count": len(item.get("suspect_sections", [])) if isinstance(item.get("suspect_sections"), list) else 0,
        "recommended_action": item.get("suggested_next_step", ""),
        "case_argv": [
            "python",
            json_path(Path(__file__).resolve().with_name("repair_import_case.py")),
            "--queue",
            queue_path,
            "--queue-item",
            item_id,
            "--evidence-mode",
            "auto",
            "--write-case",
            "--json",
        ],
    }


def compact_queue_payload(payload: dict[str, object], *, limit: int) -> dict[str, object]:
    items = [item for item in payload.get("items", []) if isinstance(item, dict)]
    ranked = sorted(items, key=risk_score, reverse=True)
    queue_path = str(payload.get("queue_path", ""))
    compact_items = [compact_item(item, queue_path=queue_path) for item in ranked[:limit]]
    top_item = compact_items[0] if compact_items else {}
    top_source = ranked[0] if ranked else {}
    top_blocked_item = compact_item(top_source, queue_path=queue_path) if top_source and top_source.get("single_section_candidate") is not True else {}
    next_repairable_source = next(
        (
            item
            for item in ranked
            if item.get("single_section_candidate") is True
            and str(item.get("blocked") or "") == ""
            and int(item.get("blocking_risk_count") or 0) > 0
        ),
        None,
    )
    next_repairable_item = compact_item(next_repairable_source, queue_path=queue_path) if next_repairable_source else {}
    recommended_item = next_repairable_item or top_item
    if next_repairable_item and top_blocked_item:
        recommended_reason = (
            "Highest-risk item is not a single-section candidate; use next_repairable_item.case_argv "
            "instead of reading full queue.json."
        )
    elif next_repairable_item:
        recommended_reason = "Use recommended_item.case_argv to generate exactly one local repair case."
    elif top_blocked_item:
        recommended_reason = "No single-section repair candidate was found; create a blocked case or narrow the target folder."
    else:
        recommended_reason = "No import repair queue items were found."
    return {
        "schema_version": payload.get("schema_version"),
        "ok": payload.get("ok"),
        "recommended_item": recommended_item,
        "recommended_reason": recommended_reason,
        "next_repairable_item": next_repairable_item,
        "top_blocked_item": top_blocked_item,
        "top_item": top_item,
        "target_root": payload.get("target_root"),
        "queue_path": queue_path,
        "compact_queue_path": json_path(Path(queue_path).with_name(COMPACT_QUEUE_NAME)) if queue_path else "",
        "counts": payload.get("counts", {}),
        "compact": True,
        "items_returned": min(limit, len(ranked)),
        "items_total": len(ranked),
        "items": compact_items,
        "agent_rules": [
            "Process one queue item at a time.",
            "Do not generate multiple cases in parallel.",
            "Do not write .fixed files or vault-local debug scripts.",
            "Do not inspect Student OS source code to interpret diagnostics unless a script crashes.",
            "If top_blocked_item is present, use next_repairable_item.case_argv before reading full queue.json.",
        ],
    }


def build_queue(root: Path, *, include_verified: bool = False) -> dict[str, object]:
    root = root.resolve()
    state_root = state_root_for_scan(root)
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


def write_compact_queue(payload: dict[str, object]) -> Path:
    queue_path = Path(str(payload["queue_path"]))
    compact_path = queue_path.with_name(COMPACT_QUEUE_NAME)
    compact_path.parent.mkdir(parents=True, exist_ok=True)
    compact_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return compact_path


def main() -> int:
    configure_stdout()
    parser = argparse.ArgumentParser(description="Build an AI-assisted import repair queue for markdown sidecars.")
    parser.add_argument("target", help="Learning vault or imported markdown folder/file to scan")
    parser.add_argument("--include-verified", action="store_true", help="Include files marked verify_status: verified")
    parser.add_argument(
        "--classify-evidence",
        action="store_true",
        help="Compatibility flag; queue items always include evidence classification.",
    )
    parser.add_argument("--write-queue", action="store_true", help="Write .student-os/import-repair/queue.json")
    parser.add_argument(
        "--compact-json",
        action="store_true",
        help="With --json, print a compact agent-facing summary while still writing the full queue when --write-queue is used.",
    )
    parser.add_argument("--full-json", action="store_true", help="Force full JSON output even when --compact-json is present.")
    parser.add_argument("--limit", type=int, default=1, help="Maximum items returned by --compact-json")
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
        if args.compact_json and not args.full_json:
            limit = max(1, args.limit)
            payload = compact_queue_payload(payload, limit=limit)
            if args.write_queue:
                payload["compact_queue_path"] = json_path(write_compact_queue(payload))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["queue_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
