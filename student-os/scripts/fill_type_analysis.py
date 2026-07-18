#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from course_layout import configure_stdout_utf8
from exam_census_quality import ENTRY_LAYER_MARKERS, REQUIRED_SECTION_HEADINGS
from exam_census_utils import (
    course_slug_of,
    exam_scope_key,
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
    match = re.search(r"(?m)^source_artifacts:\s*\[(.*)\]\s*$", text)
    if not match:
        return []
    inner = match.group(1).strip()
    if not inner:
        return []
    return [part.strip().strip('"').strip("'") for part in inner.split(",") if part.strip()]


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

    items: list[dict] = []
    for path in sorted(analysis_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        type_id = extract_exam_type_id(text) or path.stem
        items.append(
            {
                "path": relative_posix(path, repo),
                "exam_type_id": type_id,
                "sources": extract_sources(text),
                "required_sections": REQUIRED_SECTION_HEADINGS,
                "entry_layer_markers": ENTRY_LAYER_MARKERS,
                "instructions": [
                    "Fill this page to content-standard v2 (see references/exam-census-quality.md).",
                    "Answer the zero-foundation entry four questions before deeper theory.",
                    "Assign every annotated past-paper instance of this type to 例题精讲 or 自测题.",
                    "Use blockquote patterns for badge / 关键 / 注意 / 技巧总结 / 填空式答题模板.",
                ],
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
        "quality_reference": "student-os/references/exam-census-quality.md",
        "template": "student-os/templates/exam-type-analysis.md",
    }
    write_json(queue_path, payload)
    print(json.dumps({"queue": str(queue_path), **{k: payload[k] for k in ("course", "exam_scope", "item_count")}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
