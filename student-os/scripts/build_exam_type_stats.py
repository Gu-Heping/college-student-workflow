#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from course_layout import configure_stdout_utf8, slugify
from exam_census_utils import (
    MUST_KNOW_RATE,
    course_slug_of,
    load_annotations,
    load_json,
    load_taxonomy,
    relative_posix,
    resolve_course,
    reviews_dir,
    state_dir,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate exam-census annotations into frequency report and type-analysis skeletons."
    )
    parser.add_argument("repo", help="Target vault repository root")
    parser.add_argument("--course", required=True, help="Course slug or path under courses/")
    parser.add_argument("--exam-scope", required=True, help="Exam scope label such as 期中 or midterm")
    parser.add_argument("--semester", default="", help="Optional semester slug when resolving the course")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Exit nonzero when papers are missing annotations or use unknown type ids",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing frequency report and type-analysis skeletons",
    )
    parser.add_argument(
        "--must-know-rate",
        type=float,
        default=MUST_KNOW_RATE,
        help=f"Appearance rate threshold for must-know tier (default: {MUST_KNOW_RATE})",
    )
    return parser.parse_args()


def yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def write_text(path: Path, text: str, *, overwrite: bool) -> bool:
    if path.exists() and not overwrite:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8", newline="\n")
    return True


def aggregate(
    *,
    taxonomy: dict[str, Any],
    annotations: dict[str, dict[str, Any]],
    papers: list[dict[str, Any]],
    must_know_rate: float,
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    type_meta = {str(item["id"]): item for item in taxonomy.get("types", [])}
    known_ids = set(type_meta)
    paper_by_stem = {str(item["stem"]): item for item in papers}

    stats: dict[str, dict[str, Any]] = {
        type_id: {
            "id": type_id,
            "name": type_meta[type_id].get("name", type_id),
            "paper_count": 0,
            "question_count": 0,
            "papers": [],
        }
        for type_id in known_ids
    }

    missing: list[str] = []
    low_confidence: list[dict[str, Any]] = []
    unknown_types: list[dict[str, Any]] = []

    for paper in papers:
        stem = str(paper["stem"])
        annotation = annotations.get(stem)
        if annotation is None:
            missing.append(stem)
            continue
        confidence = str(annotation.get("confidence", "high")).lower()
        if confidence in {"low", "uncertain", "needs-review"}:
            low_confidence.append({"stem": stem, "confidence": confidence})

        present = [str(item) for item in annotation.get("types_present") or []]
        counts = annotation.get("type_counts") or {}
        if not isinstance(counts, dict):
            counts = {}

        for type_id in present:
            if type_id not in known_ids:
                unknown_types.append({"stem": stem, "type_id": type_id})
                continue
            bucket = stats[type_id]
            bucket["paper_count"] += 1
            try:
                count_value = int(counts.get(type_id, 1))
            except (TypeError, ValueError):
                count_value = 1
            bucket["question_count"] += max(count_value, 1)
            source = annotation.get("source") or paper_by_stem.get(stem, {}).get("path") or stem
            label = annotation.get("exam_label") or stem
            bucket["papers"].append({"stem": stem, "label": label, "source": source})

    annotated_count = len(papers) - len(missing)
    ranked: list[dict[str, Any]] = []
    for type_id, bucket in stats.items():
        rate = (bucket["paper_count"] / annotated_count) if annotated_count else 0.0
        ranked.append(
            {
                **bucket,
                "appearance_rate": rate,
                "must_know": rate >= must_know_rate and bucket["paper_count"] > 0,
            }
        )
    ranked.sort(key=lambda item: (-item["paper_count"], -item["question_count"], item["id"]))
    return ranked, missing, low_confidence, unknown_types


def render_frequency_report(
    *,
    course_name: str,
    course_slug: str,
    exam_scope: str,
    taxonomy: dict[str, Any],
    paper_count: int,
    annotated_count: int,
    ranked: list[dict[str, Any]],
    missing: list[str],
    low_confidence: list[dict[str, Any]],
    today: str,
) -> str:
    coverage = (annotated_count / paper_count) if paper_count else 0.0
    lines = [
        "---",
        "type: exam-type-frequency-report",
        f"course: {yaml_string(course_name)}",
        "status: active",
        f"created: {today}",
        f"updated: {today}",
        f"tags: [course/{course_slug}, review, exam-census]",
        "review_scope: exam-census",
        f"exam_scope: {yaml_string(exam_scope)}",
        "---",
        "",
        f"# {course_name} · {exam_scope} · 题型频率统计",
        "",
        "## Census Metadata",
        "",
        f"- Taxonomy version: {taxonomy.get('version', 1)}",
        f"- Papers total: {paper_count}",
        f"- Annotated: {annotated_count}",
        f"- Coverage: {coverage:.0%}",
        f"- Ranking key: paper appearance count (not raw question repeats)",
        "",
        "## Frequency Table",
        "",
        "| Rank | Type | Papers | Appearance rate | Questions | Must-know | Sample papers |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    if not ranked:
        lines.append("| - | _(no taxonomy types yet)_ | 0 | 0% | 0 | no | - |")
    for index, item in enumerate(ranked, start=1):
        samples = ", ".join(
            f"[{paper['label']}]({paper['source']})" for paper in item["papers"][:3]
        ) or "-"
        lines.append(
            "| {rank} | {name} (`{type_id}`) | {papers} | {rate:.0%} | {questions} | {must} | {samples} |".format(
                rank=index,
                name=item["name"],
                type_id=item["id"],
                papers=item["paper_count"],
                rate=item["appearance_rate"],
                questions=item["question_count"],
                must="yes" if item["must_know"] else "no",
                samples=samples,
            )
        )

    lines.extend(["", "## Validation", ""])
    if missing:
        lines.append("### Missing annotations")
        lines.extend([f"- `{stem}`" for stem in missing])
        lines.append("")
    else:
        lines.extend(["### Missing annotations", "", "- None", ""])

    if low_confidence:
        lines.append("### Low-confidence annotations")
        lines.extend([f"- `{item['stem']}` ({item['confidence']})" for item in low_confidence])
        lines.append("")
    else:
        lines.extend(["### Low-confidence annotations", "", "- None", ""])

    lines.extend(
        [
            "## Next Steps",
            "",
            f"- Fill `reviews/{exam_scope}/题型解析/` skeletons in frequency order.",
            f"- Draft `备考指南.md`, `公式总卡.md`, `答题模板速查.md`, and `考前1小时清单.md`.",
            "",
        ]
    )
    return "\n".join(lines)


def render_type_skeleton(
    *,
    course_name: str,
    course_slug: str,
    exam_scope: str,
    item: dict[str, Any],
    rank: int,
    today: str,
) -> str:
    sources = [str(paper["source"]) for paper in item["papers"]]
    source_yaml = ", ".join(yaml_string(source) for source in sources) if sources else ""
    lines = [
        "---",
        "type: exam-type-analysis",
        f"course: {yaml_string(course_name)}",
        "status: draft",
        f"created: {today}",
        f"updated: {today}",
        f"tags: [course/{course_slug}, review, exam-census]",
        "review_scope: exam-census",
        f"exam_scope: {yaml_string(exam_scope)}",
        f"exam_type_id: {yaml_string(item['id'])}",
        f"exam_type_rank: {rank}",
        f"source_artifacts: [{source_yaml}]",
        "---",
        "",
        f"# {rank:02d} · {item['name']}",
        "",
        "## Census Signal",
        "",
        f"- Appearance rate: {item['appearance_rate']:.0%} ({item['paper_count']} papers)",
        f"- Question count (annotated): {item['question_count']}",
        f"- Must-know tier: {'yes' if item['must_know'] else 'no'}",
        "",
        "## Method Outline",
        "",
        "- _(fill by review-coach)_",
        "",
        "## Representative Problems",
        "",
    ]
    if item["papers"]:
        for paper in item["papers"]:
            lines.append(f"- [{paper['label']}]({paper['source']})")
    else:
        lines.append("- _(none yet)_")
    lines.extend(
        [
            "",
            "## Common Pitfalls",
            "",
            "- _(fill by review-coach)_",
            "",
            "## Practice Targets",
            "",
            "- [ ] Rework one high-frequency instance",
            "- [ ] Recite the core method without notes",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    configure_stdout_utf8()
    args = parse_args()
    if not 0 <= args.must_know_rate <= 1:
        raise SystemExit("--must-know-rate must be between 0 and 1")

    repo = Path(args.repo).resolve()
    course_dir = resolve_course(repo, args.course, semester=args.semester)
    course_slug = course_slug_of(course_dir, repo)
    exam_scope = args.exam_scope.strip()
    census_state = state_dir(repo, course_slug, exam_scope)
    manifest_path = census_state / "manifest.json"
    taxonomy_path = census_state / "taxonomy.yaml"
    annotations_dir = census_state / "annotations"
    output_root = reviews_dir(course_dir, exam_scope)
    analysis_dir = output_root / "题型解析"
    report_path = output_root / "题型频率统计.md"

    if not manifest_path.exists():
        raise SystemExit(f"Missing manifest. Run init_exam_census.py first: {manifest_path}")
    if not taxonomy_path.exists():
        raise SystemExit(f"Missing taxonomy.yaml: {taxonomy_path}")

    manifest = load_json(manifest_path)
    taxonomy = load_taxonomy(taxonomy_path)
    annotations = load_annotations(annotations_dir)
    papers = list(manifest.get("papers") or [])
    course_name = str(taxonomy.get("course") or course_slug)

    ranked, missing, low_confidence, unknown_types = aggregate(
        taxonomy=taxonomy,
        annotations=annotations,
        papers=papers,
        must_know_rate=args.must_know_rate,
    )
    annotated_count = len(papers) - len(missing)
    today = date.today().isoformat()

    report = render_frequency_report(
        course_name=course_name,
        course_slug=course_slug,
        exam_scope=exam_scope,
        taxonomy=taxonomy,
        paper_count=len(papers),
        annotated_count=annotated_count,
        ranked=ranked,
        missing=missing,
        low_confidence=low_confidence,
        today=today,
    )
    wrote_report = write_text(report_path, report, overwrite=args.overwrite)

    written_skeletons: list[str] = []
    skipped_skeletons: list[str] = []
    for index, item in enumerate(ranked, start=1):
        if item["paper_count"] <= 0:
            continue
        filename = f"{index:02d}-{slugify(item['id'], fallback='type')}.md"
        target = analysis_dir / filename
        body = render_type_skeleton(
            course_name=course_name,
            course_slug=course_slug,
            exam_scope=exam_scope,
            item=item,
            rank=index,
            today=today,
        )
        if write_text(target, body, overwrite=args.overwrite):
            written_skeletons.append(relative_posix(target, repo))
        else:
            skipped_skeletons.append(relative_posix(target, repo))

    result = {
        "repo": str(repo),
        "course": course_slug,
        "exam_scope": exam_scope,
        "report": str(report_path),
        "report_written": wrote_report,
        "annotated_count": annotated_count,
        "paper_count": len(papers),
        "coverage": (annotated_count / len(papers)) if papers else 0.0,
        "ranked_types": [
            {
                "id": item["id"],
                "name": item["name"],
                "paper_count": item["paper_count"],
                "appearance_rate": item["appearance_rate"],
                "must_know": item["must_know"],
            }
            for item in ranked
            if item["paper_count"] > 0
        ],
        "skeletons_written": written_skeletons,
        "skeletons_skipped": skipped_skeletons,
        "missing_annotations": missing,
        "low_confidence": low_confidence,
        "unknown_types": unknown_types,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.validate and (missing or unknown_types):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
