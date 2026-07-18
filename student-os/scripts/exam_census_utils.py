#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from course_layout import resolve_course_dir, slugify


PAPER_SUFFIXES = (".pdf.md",)
DEFAULT_BATCH_SIZE = 6
MUST_KNOW_RATE = 0.6


CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = frozenset({"low", "uncertain", "needs-review"})
CONFIDENCE_ALLOWED = frozenset({"high", "medium", "low", "uncertain", "needs-review"})

PAPER_SUBDIR_CANDIDATES = ("文本", "text", "markdown", "md")


def course_state_key(course_dir: Path, repo: Path) -> str:
    """Stable census key that includes semester nesting when present."""
    courses_root = (repo / "courses").resolve()
    try:
        return course_dir.resolve().relative_to(courses_root).as_posix()
    except ValueError:
        return course_dir.name


def course_tag_slug(course_key: str) -> str:
    return course_key.replace("/", "-")


def exam_scope_key(exam_scope: str) -> str:
    """Normalize exam_scope for state and reviews directory segments."""
    raw = str(exam_scope or "").strip()
    if not raw:
        raise ValueError("exam_scope must be a non-empty label")
    if raw in {".", ".."} or any(sep in raw for sep in ("/", "\\", ":")):
        raise ValueError(
            "exam_scope must not contain path separators or drive markers "
            f"(got {exam_scope!r})"
        )
    key = slugify(raw, fallback="")
    if not key:
        raise ValueError(f"exam_scope does not yield a usable directory key: {exam_scope!r}")
    return key


def state_dir(repo: Path, course_key: str, exam_scope: str) -> Path:
    return repo / ".student-os" / "state" / "exam-census" / Path(course_key) / exam_scope_key(exam_scope)


def reviews_dir(course_dir: Path, exam_scope: str) -> Path:
    return course_dir / "reviews" / exam_scope_key(exam_scope)


def annotation_id(paper_path: Path, papers_dir: Path) -> str:
    """Unique annotation id derived from the paper path relative to papers_dir."""
    try:
        relative = paper_path.resolve().relative_to(papers_dir.resolve())
    except ValueError:
        relative = Path(paper_path.name)
    text = relative.as_posix()
    if text.endswith(".pdf.md"):
        text = text[: -len(".pdf.md")]
    elif text.endswith(".md"):
        text = text[: -len(".md")]
    return text.replace("/", "__")


def annotation_stem(paper_path: Path) -> str:
    # Backward-compatible helper for basename-only callers/tests.
    name = paper_path.name
    if name.endswith(".pdf.md"):
        return name[: -len(".pdf.md")]
    return paper_path.stem


def resolve_course(repo: Path, course: str, semester: str = "") -> Path:
    return resolve_course_dir(repo, course, semester=semester)


def course_slug_of(course_dir: Path, repo: Path) -> str:
    return course_state_key(course_dir, repo)


def discover_papers(papers_dir: Path, pattern: str) -> list[Path]:
    if not papers_dir.exists():
        raise FileNotFoundError(f"Papers directory does not exist: {papers_dir}")
    matches = sorted(path for path in papers_dir.glob(pattern) if path.is_file())
    papers = [path for path in matches if path.name.endswith(PAPER_SUFFIXES)]
    return papers


def resolve_papers_dir(papers_dir: Path, pattern: str) -> tuple[Path, str | None]:
    """Prefer a known text subdirectory when the papers root has no top-level sidecars.

    Fallback names: 文本 / text / markdown / md.
    Only used when the requested directory itself has zero top-level `*.pdf.md`
    files (recursive matches under those children still trigger fallback).
    """
    resolved = papers_dir.resolve()
    if discover_papers(resolved, "*.pdf.md"):
        return resolved, None
    for name in PAPER_SUBDIR_CANDIDATES:
        candidate = resolved / name
        if not candidate.is_dir():
            continue
        found = discover_papers(candidate, pattern)
        if not found:
            found = discover_papers(candidate, "**/*.pdf.md")
        if found:
            return candidate.resolve(), name
    return resolved, None


def chunk_batches(items: list[Any], batch_size: int) -> list[list[Any]]:
    size = max(1, batch_size)
    return [items[index : index + size] for index in range(0, len(items), size)]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _json_scalar(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _parse_scalar(raw: str) -> Any:
    text = raw.strip()
    if not text:
        return ""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _split_csv(text: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    in_quote: str | None = None
    for char in text:
        if in_quote:
            current.append(char)
            if char == in_quote:
                in_quote = None
            continue
        if char in {'"', "'"}:
            in_quote = char
            current.append(char)
            continue
        if char == ",":
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    if current or parts:
        parts.append("".join(current).strip())
    return [part for part in parts if part]


def _parse_string_list(raw: str) -> list[str]:
    text = raw.strip()
    if not text:
        return []
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = None
    else:
        if isinstance(value, list):
            return [str(item) for item in value]
        if value == "" or value is None:
            return []
        return [str(value)]
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [str(_parse_scalar(part)) for part in _split_csv(inner)]
    return [str(_parse_scalar(text))]


def dump_taxonomy_yaml(taxonomy: dict[str, Any]) -> str:
    lines = [
        f"version: {int(taxonomy.get('version', 1))}",
        f"course: {_json_scalar(str(taxonomy.get('course', '')))}",
        f"exam_scope: {_json_scalar(str(taxonomy.get('exam_scope', '')))}",
        "types:",
    ]
    for item in taxonomy.get("types", []):
        lines.append(f"  - id: {_json_scalar(str(item['id']))}")
        lines.append(f"    name: {_json_scalar(str(item.get('name', item['id'])))}")
        aliases = [str(alias) for alias in (item.get("aliases") or [])]
        keywords = [str(keyword) for keyword in (item.get("keywords") or [])]
        alias_text = ", ".join(_json_scalar(alias) for alias in aliases)
        keyword_text = ", ".join(_json_scalar(keyword) for keyword in keywords)
        lines.append(f"    aliases: [{alias_text}]")
        lines.append(f"    keywords: [{keyword_text}]")
    lines.append("")
    return "\n".join(lines)


def _assign_taxonomy_type_field(current: dict[str, Any], key: str, raw_value: str) -> None:
    if key == "id":
        current["id"] = str(_parse_scalar(raw_value)).strip()
        return
    if key == "name":
        current["name"] = str(_parse_scalar(raw_value)).strip()
        return
    if key in {"aliases", "keywords"}:
        current[key] = _parse_string_list(raw_value)
        return


def _normalize_taxonomy(payload: dict[str, Any]) -> dict[str, Any]:
    types: list[dict[str, Any]] = []
    for index, item in enumerate(payload.get("types") or []):
        if not isinstance(item, dict):
            raise ValueError(f"taxonomy types[{index}] must be a mapping")
        type_id = str(item.get("id", "")).strip()
        if not type_id:
            raise ValueError(f"taxonomy types[{index}] has empty id")
        name = str(item.get("name") or type_id).strip() or type_id
        aliases = item.get("aliases") or []
        keywords = item.get("keywords") or []
        if not isinstance(aliases, list):
            aliases = [aliases]
        if not isinstance(keywords, list):
            keywords = [keywords]
        types.append(
            {
                "id": type_id,
                "name": name,
                "aliases": [str(alias) for alias in aliases],
                "keywords": [str(keyword) for keyword in keywords],
            }
        )
    version_raw = payload.get("version", 1)
    try:
        version = int(version_raw)
    except (TypeError, ValueError):
        version = 1
    return {
        "version": version,
        "course": str(payload.get("course", "")),
        "exam_scope": str(payload.get("exam_scope", "")),
        "types": types,
    }


def _parse_taxonomy_yaml_fallback(text: str) -> dict[str, Any]:
    """Parse project YAML and common PyYAML dump shapes without PyYAML."""
    data: dict[str, Any] = {"version": 1, "course": "", "exam_scope": "", "types": []}
    current: dict[str, Any] | None = None
    current_item_indent = -1
    current_list_key: str | None = None
    in_types = False

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        if re.match(r"^version\s*:", raw_line):
            data["version"] = int(str(_parse_scalar(raw_line.split(":", 1)[1])))
            in_types = False
            current = None
            current_list_key = None
            continue
        if re.match(r"^course\s*:", raw_line):
            data["course"] = str(_parse_scalar(raw_line.split(":", 1)[1]))
            in_types = False
            current = None
            current_list_key = None
            continue
        if re.match(r"^exam_scope\s*:", raw_line):
            data["exam_scope"] = str(_parse_scalar(raw_line.split(":", 1)[1]))
            in_types = False
            current = None
            current_list_key = None
            continue
        if re.match(r"^types\s*:\s*$", raw_line):
            in_types = True
            current = None
            current_list_key = None
            continue
        if not in_types:
            continue

        dash_match = re.match(r"^(\s*)-\s+(.*)$", raw_line)
        if dash_match:
            indent = len(dash_match.group(1).expandtabs(2))
            rest = dash_match.group(2).strip()
            if (
                current is not None
                and current_list_key is not None
                and indent > current_item_indent
            ):
                current[current_list_key].append(str(_parse_scalar(rest)))
                continue

            if current is not None:
                data["types"].append(current)
            current = {"id": "", "name": "", "aliases": [], "keywords": []}
            current_item_indent = indent
            current_list_key = None
            if ":" in rest:
                key, _, value = rest.partition(":")
                key = key.strip()
                value = value.strip()
                if key in {"aliases", "keywords"} and value == "":
                    current_list_key = key
                    current[key] = []
                else:
                    _assign_taxonomy_type_field(current, key, value)
            continue

        if current is None:
            continue

        field_match = re.match(r"^(\s*)([A-Za-z_][\w-]*)\s*:\s*(.*)$", raw_line)
        if field_match:
            indent = len(field_match.group(1).expandtabs(2))
            if indent <= current_item_indent:
                continue
            key = field_match.group(2)
            value = field_match.group(3).strip()
            if key in {"aliases", "keywords"} and value in {"", "|", ">"}:
                current_list_key = key
                current[key] = []
                continue
            current_list_key = None
            _assign_taxonomy_type_field(current, key, value)
            continue

    if current is not None:
        data["types"].append(current)
    return data


def load_taxonomy_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None
    if yaml is not None:
        try:
            loaded = yaml.safe_load(text)
        except Exception:
            loaded = None
        if isinstance(loaded, dict):
            return _normalize_taxonomy(loaded)
    return _normalize_taxonomy(_parse_taxonomy_yaml_fallback(text))


def write_taxonomy(path: Path, taxonomy: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_taxonomy_yaml(taxonomy), encoding="utf-8", newline="\n")


def load_taxonomy(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        payload = load_json(path)
        if not isinstance(payload, dict):
            raise ValueError(f"Taxonomy JSON must be an object: {path}")
        return _normalize_taxonomy(payload)
    return load_taxonomy_yaml(path)


def default_taxonomy(course_name: str, exam_scope: str) -> dict[str, Any]:
    return {
        "version": 1,
        "course": course_name,
        "exam_scope": exam_scope,
        "types": [],
    }


def load_annotations(annotations_dir: Path) -> dict[str, dict[str, Any]]:
    if not annotations_dir.exists():
        return {}
    payload: dict[str, dict[str, Any]] = {}
    for path in sorted(annotations_dir.rglob("*.json")):
        item = load_json(path)
        if not isinstance(item, dict):
            raise ValueError(f"Annotation must be an object: {path}")
        key = path.relative_to(annotations_dir).with_suffix("").as_posix().replace("/", "__")
        payload[key] = item
    return payload


def _normalize_repo_rel(path_text: str) -> str:
    return str(path_text or "").replace("\\", "/").lstrip("./")


def _paths_equivalent(left: str, right: str) -> bool:
    a = _normalize_repo_rel(left)
    b = _normalize_repo_rel(right)
    if not a or not b:
        return False
    return a == b or a.endswith("/" + b) or b.endswith("/" + a)


def load_annotations_for_manifest(
    annotations_dir: Path,
    papers: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]], list[dict[str, Any]]]:
    """Load annotations keyed by manifest stem, with filename/source fallbacks.

    Returns:
      annotations_by_stem,
      annotation_aliases_used (fallback reads),
      annotation_load_errors (ambiguous matches)
    """
    by_stem: dict[str, dict[str, Any]] = {}
    aliases_used: list[dict[str, str]] = []
    errors: list[dict[str, Any]] = []

    indexed: list[tuple[Path, dict[str, Any]]] = []
    if annotations_dir.exists():
        for path in sorted(annotations_dir.rglob("*.json")):
            item = load_json(path)
            if not isinstance(item, dict):
                raise ValueError(f"Annotation must be an object: {path}")
            indexed.append((path, item))

    for paper in papers:
        stem = str(paper.get("stem") or "")
        if not stem:
            continue
        paper_path = _normalize_repo_rel(str(paper.get("path") or ""))
        expected_name = f"{stem}.json"
        preferred_rel = str(paper.get("annotation") or f"annotations/{expected_name}")
        preferred_name = Path(preferred_rel).name or expected_name

        matches: list[tuple[str, Path, dict[str, Any]]] = []
        seen_paths: set[Path] = set()

        def _add(kind: str, path: Path, payload: dict[str, Any]) -> None:
            resolved = path.resolve()
            if resolved in seen_paths:
                return
            seen_paths.add(resolved)
            matches.append((kind, path, payload))

        for path, payload in indexed:
            if path.name == preferred_name or path.name == expected_name:
                _add("preferred", path, payload)

        if not matches:
            for alias_name in (f"{stem}.pdf.md.json", f"{stem}.md.json"):
                for path, payload in indexed:
                    if path.name == alias_name:
                        _add("filename_alias", path, payload)

        if not matches and paper_path:
            for path, payload in indexed:
                source = _normalize_repo_rel(str(payload.get("source") or ""))
                if _paths_equivalent(source, paper_path):
                    _add("source_match", path, payload)

        if not matches:
            continue

        preferred_matches = [item for item in matches if item[0] == "preferred"]
        if preferred_matches:
            kind, path, payload = preferred_matches[0]
            by_stem[stem] = payload
            continue

        if len(matches) > 1:
            errors.append(
                {
                    "stem": stem,
                    "error": "ambiguous_annotation_fallback",
                    "candidates": [str(path) for _, path, _ in matches],
                }
            )
            continue

        kind, path, payload = matches[0]
        by_stem[stem] = payload
        aliases_used.append(
            {
                "stem": stem,
                "expected": expected_name,
                "actual": path.name,
                "match": kind,
            }
        )

    return by_stem, aliases_used, errors


def classify_confidence(raw: Any) -> tuple[str, str]:
    """Return (normalized_confidence, bucket) where bucket is high|medium|low|invalid."""
    confidence = str(raw if raw is not None else CONFIDENCE_HIGH).strip().lower() or CONFIDENCE_HIGH
    if confidence == CONFIDENCE_HIGH:
        return confidence, "high"
    if confidence == CONFIDENCE_MEDIUM:
        return confidence, "medium"
    if confidence in CONFIDENCE_LOW:
        return confidence, "low"
    return confidence, "invalid"


def relative_posix(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_repo_path(repo: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (repo / candidate).resolve()


def markdown_rel_link(source: str, from_doc: Path, repo: Path) -> str:
    import os

    target = resolve_repo_path(repo, source)
    try:
        relative = Path(os.path.relpath(target, start=from_doc.parent)).as_posix()
    except ValueError:
        try:
            relative = target.resolve().relative_to(repo.resolve()).as_posix()
        except ValueError:
            relative = source
    # Preserve non-ASCII path segments (common in vaults); encode only Markdown/URL breakers.
    return "".join(
        quote(char, safe="") if char in " ?#<>[]{}|\\%()" else char for char in relative
    )


# $|A|$ / $|λE-A|$ → $\lvert …\rvert$ so Markdown tables keep column counts.
_MATH_ABS_PIPE_RE = re.compile(r"\$\|([^|$]+)\|\$")
# Bare determinant/absolute forms that commonly break tables: |A|, |A*|, |λE-A|.
_BARE_DET_PIPE_RE = re.compile(
    r"(?<![\\|$])\|([A-Za-zΑ-Ωα-ωλΛ*][A-Za-z0-9Α-Ωα-ωλΛ*\+\-−–]*)\|(?![\\|$\w])"
)

# Annotation enum → Chinese display labels for user-facing Markdown reports.
RELIABILITY_DISPLAY = {
    "answer-key": "答案卷",
    "review-copy": "复习版",
    "recall": "回忆版",
    "unspecified": "未标注",
}
FORMAT_DISPLAY = {
    "unspecified": "未标注",
    "choice": "选择",
    "multiple-choice": "选择",
    "mcq": "选择",
    "select": "选择",
    "fill": "填空",
    "fill-in": "填空",
    "blank": "填空",
    "calculation": "计算",
    "compute": "计算",
    "short-answer": "简答",
    "true-false": "判断",
    "proof": "证明",
}
DIFFICULTY_DISPLAY = {
    "unspecified": "未标注",
    "easy": "易",
    "medium": "中",
    "hard": "难",
    "1": "★",
    "2": "★★",
    "3": "★★★",
    "4": "★★★★",
    "5": "★★★★★",
    "*": "★",
    "**": "★★",
    "***": "★★★",
    "****": "★★★★",
    "*****": "★★★★★",
}


def display_annotation_label(value: str, mapping: dict[str, str] | None = None) -> str:
    text = str(value).strip()
    if not text:
        return "未标注"
    table = mapping or {}
    if text in table:
        return table[text]
    if text.lower() in table:
        return table[text.lower()]
    return text


def md_table_cell(value: str) -> str:
    """Escape a Markdown table cell so bare `|` cannot split columns.

    Preference for math absolute/determinant forms:
    - `$|A|$` → `$\\lvert A\\rvert$`
    - bare `|A|` / `|λE-A|` → `$\\lvert …\\rvert$`
    Remaining pipes become `\\|`. Already-escaped `\\|` is left alone.
    """
    text = str(value).replace("\n", " ")
    text = _MATH_ABS_PIPE_RE.sub(r"$\\lvert \1\\rvert$", text)
    text = _BARE_DET_PIPE_RE.sub(r"$\\lvert \1\\rvert$", text)
    pieces: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text) and text[index + 1] == "|":
            pieces.append("\\|")
            index += 2
            continue
        if char == "|":
            pieces.append("\\|")
            index += 1
            continue
        pieces.append(char)
        index += 1
    return "".join(pieces)


def count_markdown_table_columns(line: str) -> int | None:
    """Return column count for a Markdown table row, or None if not a table row."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    # Separator rows like | --- | ---: |
    if re.fullmatch(r"\|[\s\-:|]+\|?", stripped):
        cells = [cell for cell in _split_table_cells(stripped) if cell.strip() != ""]
        return len(cells) if cells else None
    cells = _split_table_cells(stripped)
    # Leading/trailing empty cells from edge pipes are normal; drop only pure edge empties.
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return len(cells)


def _split_table_cells(row: str) -> list[str]:
    cells: list[str] = []
    current: list[str] = []
    index = 0
    text = row.strip()
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text) and text[index + 1] == "|":
            current.append("\\|")
            index += 2
            continue
        if char == "|":
            cells.append("".join(current))
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    cells.append("".join(current))
    return cells


def markdown_table_pipe_issues(text: str) -> list[str]:
    """Detect table rows whose column count diverges from the header (often unescaped `|`)."""
    issues: list[str] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        header_cols = count_markdown_table_columns(lines[index])
        if header_cols is None or header_cols < 1:
            index += 1
            continue
        if index + 1 >= len(lines):
            break
        sep_cols = count_markdown_table_columns(lines[index + 1])
        sep_line = lines[index + 1].strip()
        if sep_cols is None or not re.fullmatch(r"\|[\s\-:|]+\|?", sep_line):
            index += 1
            continue
        expected = header_cols
        if sep_cols != expected:
            issues.append(
                f"table separator mismatch near line {index + 2}: "
                f"expected {expected} columns, found {sep_cols}"
            )
            index += 1
            continue
        row_index = index + 2
        while row_index < len(lines):
            row = lines[row_index]
            if not row.strip():
                break
            cols = count_markdown_table_columns(row)
            if cols is None:
                break
            if cols != expected:
                issues.append(
                    f"table column mismatch near line {row_index + 1}: "
                    f"expected {expected} columns, found {cols} ({row.strip()[:80]})"
                )
            row_index += 1
        index = row_index
    return issues
