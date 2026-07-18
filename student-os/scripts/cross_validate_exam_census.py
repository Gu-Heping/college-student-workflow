#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

from course_layout import configure_stdout_utf8
from exam_census_utils import (
    course_slug_of,
    exam_scope_key,
    load_annotations,
    load_json,
    load_taxonomy,
    resolve_course,
    reviews_dir,
    state_dir,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase E cross-validation for exam-census coverage and skeleton traceability."
    )
    parser.add_argument("repo", help="Target vault repository root")
    parser.add_argument("--course", required=True, help="Course slug or path under courses/")
    parser.add_argument("--exam-scope", required=True, help="Exam scope label such as 期中 or midterm")
    parser.add_argument("--semester", default="", help="Optional semester slug when resolving the course")
    return parser.parse_args()


def extract_exam_type_id(text: str) -> str | None:
    match = re.search(r"(?m)^exam_type_id:\s*(.+)$", text)
    if not match:
        return None
    raw = match.group(1).strip()
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    return raw


def main() -> int:
    configure_stdout_utf8()
    args = parse_args()
    repo = Path(args.repo).resolve()
    course_dir = resolve_course(repo, args.course, semester=args.semester)
    course_key = course_slug_of(course_dir, repo)
    try:
        exam_scope = args.exam_scope.strip()
        exam_scope_key(exam_scope)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    census_state = state_dir(repo, course_key, exam_scope)
    output_root = reviews_dir(course_dir, exam_scope)
    analysis_dir = output_root / "题型解析"
    taxonomy = load_taxonomy(census_state / "taxonomy.yaml")
    annotations = load_annotations(census_state / "annotations")
    manifest = load_json(census_state / "manifest.json")
    papers = list(manifest.get("papers") or [])
    known_ids = {str(item["id"]) for item in taxonomy.get("types", [])}

    skeleton_ids: dict[str, str] = {}
    if analysis_dir.exists():
        for path in sorted(analysis_dir.glob("*.md")):
            type_id = extract_exam_type_id(path.read_text(encoding="utf-8"))
            if type_id:
                skeleton_ids[type_id] = path.name

    annotated_types: set[str] = set()
    papers_missing_types: list[str] = []
    for paper in papers:
        stem = str(paper["stem"])
        annotation = annotations.get(stem)
        if annotation is None:
            papers_missing_types.append(stem)
            continue
        present = [str(item) for item in (annotation.get("types_present") or [])]
        if not present:
            papers_missing_types.append(stem)
        annotated_types.update(present)

    annotated_known = annotated_types & known_ids
    missing_skeletons = sorted(annotated_known - set(skeleton_ids))
    orphan_skeletons = sorted(set(skeleton_ids) - annotated_known)
    unknown_annotated = sorted(annotated_types - known_ids)

    prep_guide = output_root / "备考指南.md"
    guide_missing_links: list[str] = []
    if prep_guide.exists():
        guide_text = prep_guide.read_text(encoding="utf-8")
        for type_id in sorted(annotated_known):
            if type_id not in guide_text and skeleton_ids.get(type_id, "") not in guide_text:
                guide_missing_links.append(type_id)

    today = date.today().isoformat()
    report = {
        "course": course_key,
        "exam_scope": exam_scope,
        "phase": "E",
        "papers_total": len(papers),
        "papers_missing_types": papers_missing_types,
        "annotated_type_ids": sorted(annotated_known),
        "missing_skeletons": missing_skeletons,
        "orphan_skeletons": orphan_skeletons,
        "unknown_annotated_types": unknown_annotated,
        "prep_guide_unlinked_types": guide_missing_links,
        "ok": not (papers_missing_types or missing_skeletons or unknown_annotated),
    }
    write_json(census_state / "cross-validation.json", report)

    human_dir = output_root / "analysis"
    human_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        "type: exam-census-cross-validation",
        f'course: "{course_key}"',
        "status: active",
        f"created: {today}",
        f"updated: {today}",
        "review_scope: exam-census",
        f'exam_scope: "{exam_scope}"',
        "---",
        "",
        f"# {course_key} · {exam_scope} · 覆盖率检查",
        "",
        f"- Papers total: {len(papers)}",
        f"- Papers with empty/missing type lists: {len(papers_missing_types)}",
        f"- Annotated known types: {len(annotated_known)}",
        f"- Missing skeletons for annotated types: {len(missing_skeletons)}",
        f"- Orphan skeletons (no annotated papers): {len(orphan_skeletons)}",
        f"- Unknown annotated type ids: {len(unknown_annotated)}",
        "",
        "## Missing skeletons",
        "",
    ]
    if missing_skeletons:
        lines.extend([f"- `{item}`" for item in missing_skeletons])
    else:
        lines.append("- None")
    lines.extend(["", "## Papers without types", ""])
    if papers_missing_types:
        lines.extend([f"- `{item}`" for item in papers_missing_types])
    else:
        lines.append("- None")
    lines.extend(["", "## Prep guide types not linked", ""])
    if guide_missing_links:
        lines.extend([f"- `{item}`" for item in guide_missing_links])
    else:
        lines.append("- None (or prep guide not created yet)")
    lines.extend(
        [
            "",
            "## Agent follow-ups",
            "",
            "- Randomly sample 3 papers and manually confirm every question maps to a type analysis.",
            "- Ensure 公式总卡 formulas trace back to type-analysis §最少必须记住的公式.",
            "",
        ]
    )
    (human_dir / "覆盖率检查.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
