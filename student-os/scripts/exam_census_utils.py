#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from course_layout import resolve_course_dir, slugify


PAPER_SUFFIXES = (".pdf.md",)
DEFAULT_BATCH_SIZE = 6
MUST_KNOW_RATE = 0.6


def course_state_key(course_dir: Path, repo: Path) -> str:
    """Stable census key that includes semester nesting when present."""
    courses_root = (repo / "courses").resolve()
    try:
        return course_dir.resolve().relative_to(courses_root).as_posix()
    except ValueError:
        return course_dir.name


def course_tag_slug(course_key: str) -> str:
    return course_key.replace("/", "-")


def state_dir(repo: Path, course_key: str, exam_scope: str) -> Path:
    return repo / ".student-os" / "state" / "exam-census" / Path(course_key) / slugify(exam_scope, fallback="exam")


def reviews_dir(course_dir: Path, exam_scope: str) -> Path:
    return course_dir / "reviews" / exam_scope


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


def chunk_batches(items: list[Any], batch_size: int) -> list[list[Any]]:
    size = max(1, batch_size)
    return [items[index : index + size] for index in range(0, len(items), size)]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _parse_scalar(raw: str) -> Any:
    text = raw.strip()
    if not text:
        return ""
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in _split_csv(inner)]
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if text in {"true", "false"}:
        return text == "true"
    if text == "null":
        return None
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


def _yaml_quote(value: str) -> str:
    if re.search(r'[:#\[\]{},\n"]', value) or value.strip() != value:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def dump_taxonomy_yaml(taxonomy: dict[str, Any]) -> str:
    lines = [
        f"version: {int(taxonomy.get('version', 1))}",
        f"course: {_yaml_quote(str(taxonomy.get('course', '')))}",
        f"exam_scope: {_yaml_quote(str(taxonomy.get('exam_scope', '')))}",
        "types:",
    ]
    for item in taxonomy.get("types", []):
        lines.append(f"  - id: {_yaml_quote(str(item['id']))}")
        lines.append(f"    name: {_yaml_quote(str(item.get('name', item['id'])))}")
        aliases = item.get("aliases") or []
        keywords = item.get("keywords") or []
        alias_text = ", ".join(_yaml_quote(str(alias)) for alias in aliases)
        keyword_text = ", ".join(_yaml_quote(str(keyword)) for keyword in keywords)
        lines.append(f"    aliases: [{alias_text}]")
        lines.append(f"    keywords: [{keyword_text}]")
    lines.append("")
    return "\n".join(lines)


def load_taxonomy_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data: dict[str, Any] = {"version": 1, "course": "", "exam_scope": "", "types": []}
    current: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("version:"):
            data["version"] = int(str(_parse_scalar(raw_line.split(":", 1)[1])))
            continue
        if raw_line.startswith("course:"):
            data["course"] = str(_parse_scalar(raw_line.split(":", 1)[1]))
            continue
        if raw_line.startswith("exam_scope:"):
            data["exam_scope"] = str(_parse_scalar(raw_line.split(":", 1)[1]))
            continue
        if raw_line.startswith("types:"):
            continue
        match = re.match(r"^  - id:\s*(.+)$", raw_line)
        if match:
            if current is not None:
                data["types"].append(current)
            current = {
                "id": str(_parse_scalar(match.group(1))),
                "name": "",
                "aliases": [],
                "keywords": [],
            }
            continue
        if current is None:
            continue
        if raw_line.startswith("    name:"):
            current["name"] = str(_parse_scalar(raw_line.split(":", 1)[1]))
            continue
        if raw_line.startswith("    aliases:"):
            value = _parse_scalar(raw_line.split(":", 1)[1])
            current["aliases"] = value if isinstance(value, list) else [str(value)]
            continue
        if raw_line.startswith("    keywords:"):
            value = _parse_scalar(raw_line.split(":", 1)[1])
            current["keywords"] = value if isinstance(value, list) else [str(value)]
            continue
    if current is not None:
        data["types"].append(current)
    for item in data["types"]:
        if not item.get("name"):
            item["name"] = item["id"]
    return data


def write_taxonomy(path: Path, taxonomy: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_taxonomy_yaml(taxonomy), encoding="utf-8", newline="\n")


def load_taxonomy(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        payload = load_json(path)
        if not isinstance(payload, dict):
            raise ValueError(f"Taxonomy JSON must be an object: {path}")
        return payload
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
        return Path(os.path.relpath(target, start=from_doc.parent)).as_posix()
    except ValueError:
        try:
            return target.resolve().relative_to(repo.resolve()).as_posix()
        except ValueError:
            return source


def md_table_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
