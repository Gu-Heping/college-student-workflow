#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from course_layout import configure_stdout_utf8
from exam_census_quality import ENTRY_LAYER_MARKERS, FILL_QUEUE_INSTRUCTIONS, REQUIRED_SECTION_HEADINGS
from exam_census_utils import (
    course_slug_of,
    exam_scope_key,
    load_annotations_for_manifest,
    load_json,
    relative_posix,
    resolve_course,
    reviews_dir,
    state_dir,
    write_json,
)

# Subdirs under courses/<course>/references/ that usually hold exam papers, not textbooks.
_EXAM_REFERENCE_DIR_NAMES = frozenset(
    {
        "exams",
        "exam",
        "试卷",
        "真题",
        "文本",
        "text",
        "markdown",
        "md",
        "past-papers",
        "papers",
    }
)

_TEXTBOOK_NAME_HINTS = ("教材", "textbook", "讲义", "课本")
_EXAM_FILENAME_HINTS = (
    "midterm",
    "final",
    "exam",
    "quiz",
    "期中",
    "期末",
    "真题",
    "试卷",
    "测验",
    "past-paper",
    "pastpaper",
)
_REPAIR_ARTIFACT_SUFFIXES = (".raw.md", "-repair-summary.md")


def discover_concept_sources(
    repo: Path,
    course_dir: Path,
    course_key: str,
) -> list[dict[str, str]]:
    """Find textbook / lecture-note markdown sidecars agents should open for 核心概念.

    Returns repo-relative paths only (no file bodies) to keep fill-queue small.
    """
    roots: list[Path] = []
    course_refs = course_dir / "references"
    if course_refs.is_dir():
        roots.append(course_refs)
    vault_textbooks = repo / "references" / "textbooks"
    if vault_textbooks.is_dir():
        roots.append(vault_textbooks)

    slug_tokens = [
        part.lower()
        for part in re.split(r"[/_\-\s]+", course_key)
        if part and part.lower() not in {"courses", "course"}
    ]
    # Prefer human course folder name fragments too (e.g. 线性代数).
    if course_dir.name and course_dir.name.lower() not in {t.lower() for t in slug_tokens}:
        slug_tokens.append(course_dir.name.lower())

    found: list[dict[str, str]] = []
    seen: set[str] = set()

    def _is_repair_artifact(name: str) -> bool:
        lower = name.lower()
        return any(lower.endswith(suffix) for suffix in _REPAIR_ARTIFACT_SUFFIXES) or ".raw." in lower

    def _looks_like_exam_paper(name: str) -> bool:
        lower = name.lower()
        return any(hint in lower for hint in _EXAM_FILENAME_HINTS)

    def _filename_matches_course(name: str, *, require_course_token: bool = False) -> bool:
        name_l = name.lower()
        hint_hit = any(hint in name_l for hint in _TEXTBOOK_NAME_HINTS)
        slug_hit = any(token in name_l for token in slug_tokens if len(token) >= 4)
        if require_course_token:
            # Shared vault textbooks/ must mention this course (avoid cross-course leaks).
            return slug_hit
        return hint_hit or slug_hit

    def consider(path: Path, *, require_course_token: bool = False) -> None:
        if not path.is_file():
            return
        name = path.name
        if not name.endswith(".md"):
            return
        if _is_repair_artifact(name):
            return
        if _looks_like_exam_paper(name):
            return
        if not _filename_matches_course(name, require_course_token=require_course_token):
            return
        rel = relative_posix(path, repo)
        if rel in seen:
            return
        seen.add(rel)
        found.append({"path": rel, "label": path.name})

    for root in roots:
        if root == course_refs:
            exam_names = {n.lower() for n in _EXAM_REFERENCE_DIR_NAMES}
            for child in sorted(root.rglob("*")):
                if not child.is_file():
                    continue
                try:
                    rel_parts = child.relative_to(course_refs).parts
                except ValueError:
                    continue
                # Exclude files under exam-like directories (any ancestor segment).
                if any(part.lower() in exam_names for part in rel_parts[:-1]):
                    continue
                consider(child, require_course_token=False)
        else:
            for child in sorted(root.rglob("*")):
                consider(child, require_course_token=True)

    return found


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Phase A fill queue for exam-census type-analysis skeletons."
    )
    parser.add_argument("repo", help="Target vault repository root")
    parser.add_argument("--course", required=True, help="Course slug or path under courses/")
    parser.add_argument("--exam-scope", required=True, help="Exam scope label such as 期中 or midterm")
    parser.add_argument("--semester", default="", help="Optional semester slug when resolving the course")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max number of skeletons to enqueue (0 = all ranked files)",
    )
    return parser.parse_args()


def extract_exam_type_id(text: str) -> str | None:
    match = re.search(r"(?m)^exam_type_id:\s*(.+)$", text)
    if not match:
        return None
    raw = match.group(1).strip()
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    return raw


def extract_sources(text: str) -> list[str]:
    """Legacy helper: prefer annotations; only read short summary from frontmatter."""
    match = re.search(r"(?m)^source_artifacts:\s*(\[.*\])\s*$", text)
    if match:
        raw = match.group(1).strip()
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            # Legacy / mixed quoting: recover quoted segments first.
            quoted = re.findall(r'"((?:\\.|[^"\\])*)"|\'((?:\\.|[^\'\\])*)\'', raw)
            if quoted:
                return [item[0] or item[1] for item in quoted]
            inner = raw.strip("[]").strip()
            if not inner:
                return []
            return [part.strip().strip('"').strip("'") for part in inner.split(",") if part.strip()]
        if isinstance(value, list):
            return [str(item) for item in value]
        if value in ("", None):
            return []
        return [str(value)]
    summary = re.search(r'(?m)^source_summary:\s*"?(.*?)"?\s*$', text)
    if summary:
        return [summary.group(1).strip()]
    return []


def papers_for_type(
    annotations: dict[str, dict],
    papers: list[dict],
    type_id: str,
) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    papers_by_stem = {str(item.get("stem") or ""): item for item in papers}
    for stem, annotation in annotations.items():
        present = [str(item) for item in (annotation.get("types_present") or [])]
        if type_id not in present:
            continue
        paper = papers_by_stem.get(stem) or {}
        source = str(paper.get("path") or "").strip()
        if source and source not in seen:
            seen.add(source)
            paths.append(source)
    return paths


def _question_fields(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(item)
        elif item not in (None, ""):
            out.append({"question_id": str(item)})
    return out


def instances_for_type(
    annotations: dict[str, dict],
    papers: list[dict],
    type_id: str,
) -> list[dict[str, str]]:
    """Build per-paper evidence rows for fill agents (question ids when present)."""
    papers_by_stem = {str(item.get("stem") or ""): item for item in papers}
    instances: list[dict[str, str]] = []
    for stem, annotation in annotations.items():
        present = [str(item) for item in (annotation.get("types_present") or [])]
        if type_id not in present:
            continue
        paper = papers_by_stem.get(stem) or {}
        paper_path = str(paper.get("path") or annotation.get("source") or "").strip()
        exam_label = str(annotation.get("exam_label") or stem).strip()
        confidence = str(annotation.get("confidence") or "").strip()
        type_counts = annotation.get("type_counts") if isinstance(annotation.get("type_counts"), dict) else {}
        count_hint = type_counts.get(type_id)

        question_rows = _question_fields(annotation.get("questions"))
        typed_rows = [
            row
            for row in question_rows
            if not row.get("type_id") or str(row.get("type_id")) == type_id
        ]
        if typed_rows:
            for row in typed_rows:
                instances.append(
                    {
                        "paper": paper_path,
                        "exam_label": exam_label,
                        "question_id": str(
                            row.get("question_id") or row.get("label") or row.get("id") or ""
                        ).strip(),
                        "type_id": type_id,
                        "confidence": str(row.get("confidence") or confidence).strip(),
                    }
                )
            continue

        # No per-question metadata: one evidence row per paper (agent must look up 题号).
        payload = {
            "paper": paper_path,
            "exam_label": exam_label,
            "question_id": "",
            "type_id": type_id,
            "confidence": confidence,
        }
        if count_hint not in (None, ""):
            payload["type_count"] = str(count_hint)
        instances.append(payload)
    return instances


def main() -> int:
    configure_stdout_utf8()
    args = parse_args()
    repo = Path(args.repo).resolve()
    course_dir = resolve_course(repo, args.course, semester=args.semester)
    course_key = course_slug_of(course_dir, repo)
    try:
        exam_scope = args.exam_scope.strip()
        scope_key = exam_scope_key(exam_scope)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    census_state = state_dir(repo, course_key, exam_scope)
    analysis_dir = reviews_dir(course_dir, exam_scope) / "题型解析"
    if not analysis_dir.exists():
        raise SystemExit(f"Missing type-analysis directory. Run build_exam_type_stats.py first: {analysis_dir}")

    manifest_path = census_state / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Missing exam-census manifest: {manifest_path}")
    papers = list(load_json(manifest_path).get("papers") or [])
    annotations, _aliases, _errors = load_annotations_for_manifest(
        census_state / "annotations", papers
    )
    concept_sources = discover_concept_sources(repo, course_dir, course_key)
    if concept_sources:
        concept_note = (
            "Open concept_sources markdown sidecars before writing 核心概念; "
            "cite them as 参考：<filename> 第X章…"
        )
    else:
        concept_note = (
            "No textbook sidecars discovered under course references/ or "
            "references/textbooks/; write 基于考纲整理，未参考指定教材 in 核心概念."
        )
    items: list[dict] = []
    for path in sorted(analysis_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        type_id = extract_exam_type_id(text) or path.stem
        sources = extract_sources(text)
        source_papers = papers_for_type(annotations, papers, type_id) or sources
        source_instances = instances_for_type(annotations, papers, type_id)
        items.append(
            {
                "path": relative_posix(path, repo),
                "exam_type_id": type_id,
                "sources": sources,
                "source_papers": source_papers,
                "source_instances": source_instances,
                "concept_sources": concept_sources,
                "required_sections": REQUIRED_SECTION_HEADINGS,
                "entry_layer_markers": ENTRY_LAYER_MARKERS,
                "instructions": list(FILL_QUEUE_INSTRUCTIONS),
            }
        )
        if args.limit > 0 and len(items) >= args.limit:
            break

    queue_path = census_state / "fill-queue.json"
    payload = {
        "course": course_key,
        "exam_scope": exam_scope,
        "exam_scope_key": scope_key,
        "phase": "A",
        "item_count": len(items),
        "items": items,
        "concept_sources": concept_sources,
        "concept_sources_note": concept_note,
        "quality_reference": "references/exam-census-quality.md",
        "template": "templates/exam-type-analysis.md",
    }
    write_json(queue_path, payload)
    print(
        json.dumps(
            {
                "queue": str(queue_path),
                **{k: payload[k] for k in ("course", "exam_scope", "item_count")},
                "concept_source_count": len(concept_sources),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
