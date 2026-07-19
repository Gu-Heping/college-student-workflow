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
        "quality_reference": "references/exam-census-quality.md",
        "template": "templates/exam-type-analysis.md",
    }
    write_json(queue_path, payload)
    print(
        json.dumps(
            {"queue": str(queue_path), **{k: payload[k] for k in ("course", "exam_scope", "item_count")}},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
