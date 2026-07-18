#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Any

from course_layout import configure_stdout_utf8
from exam_census_utils import (
    DIFFICULTY_DISPLAY,
    FORMAT_DISPLAY,
    RELIABILITY_DISPLAY,
    course_slug_of,
    display_annotation_label,
    exam_scope_key,
    load_annotations,
    load_json,
    load_taxonomy,
    md_table_cell,
    resolve_course,
    reviews_dir,
    state_dir,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase C multi-dimensional exam-census analysis from annotations."
    )
    parser.add_argument("repo", help="Target vault repository root")
    parser.add_argument("--course", required=True, help="Course slug or path under courses/")
    parser.add_argument("--exam-scope", required=True, help="Exam scope label such as 期中 or midterm")
    parser.add_argument("--semester", default="", help="Optional semester slug when resolving the course")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing analysis drafts (default: skip files that already exist)",
    )
    return parser.parse_args()


def yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def write_md(path: Path, lines: list[str], *, overwrite: bool) -> bool:
    if path.exists() and not overwrite:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8", newline="\n")
    return True


def frontmatter(course_key: str, exam_scope: str, doc_type: str, today: str) -> list[str]:
    return [
        "---",
        f"type: {doc_type}",
        f"course: {yaml_string(course_key)}",
        "status: draft",
        f"created: {today}",
        f"updated: {today}",
        "review_scope: exam-census",
        f"exam_scope: {yaml_string(exam_scope)}",
        "---",
        "",
    ]


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
    manifest_path = census_state / "manifest.json"
    taxonomy_path = census_state / "taxonomy.yaml"
    if not manifest_path.exists() or not taxonomy_path.exists():
        raise SystemExit("Missing manifest/taxonomy. Run init + taxonomy + annotate first.")

    manifest = load_json(manifest_path)
    taxonomy = load_taxonomy(taxonomy_path)
    annotations = load_annotations(census_state / "annotations")
    type_names = {str(item["id"]): str(item.get("name", item["id"])) for item in taxonomy.get("types", [])}
    papers = list(manifest.get("papers") or [])
    today = date.today().isoformat()
    analysis_dir = reviews_dir(course_dir, exam_scope) / "analysis"

    format_counter: Counter[str] = Counter()
    pair_counter: Counter[tuple[str, str]] = Counter()
    paper_rows: list[dict[str, Any]] = []
    for paper in papers:
        stem = str(paper["stem"])
        annotation = annotations.get(stem) or {}
        present = list(dict.fromkeys(str(item) for item in (annotation.get("types_present") or [])))
        reliability = str(annotation.get("paper_reliability") or annotation.get("reliability") or "unspecified")
        difficulty = annotation.get("difficulty_stars") or annotation.get("difficulty") or "unspecified"
        paper_format = str(annotation.get("paper_format") or annotation.get("format") or "unspecified")
        format_counter[paper_format] += 1
        for left, right in combinations(sorted(present), 2):
            pair_counter[(left, right)] += 1
        paper_rows.append(
            {
                "stem": stem,
                "label": annotation.get("exam_label") or stem,
                "types": present,
                "reliability": reliability,
                "difficulty": difficulty,
                "format": paper_format,
            }
        )

    # 题型关联
    co_lines = frontmatter(course_key, exam_scope, "exam-type-cooccurrence", today)
    co_lines.extend(
        [
            f"# {course_key} · {exam_scope} · 题型关联分析",
            "",
            "同一份已标注试卷中共同出现的题型对（计数 = 同时含两种题型的试卷数）。",
            "",
            "| 题型 A | 题型 B | 共现试卷数 |",
            "| --- | --- | ---: |",
        ]
    )
    if pair_counter:
        for (left, right), count in pair_counter.most_common():
            co_lines.append(
                f"| {md_table_cell(type_names.get(left, left))} (`{left}`) | "
                f"{md_table_cell(type_names.get(right, right))} (`{right}`) | {count} |"
            )
    else:
        co_lines.append("| - | - | 0 |")

    format_lines = frontmatter(course_key, exam_scope, "exam-format-frequency", today)
    format_lines.extend(
        [
            f"# {course_key} · {exam_scope} · 分题型频率统计",
            "",
            "根据标注中可选的 `paper_format` / `format` 字段汇总。",
            "填写题型解析后，可再细分为选择 / 填空 / 计算等桶。",
            "",
            "| 题型格式 | 试卷数 |",
            "| --- | ---: |",
        ]
    )
    if format_counter:
        for label, count in format_counter.most_common():
            shown = display_annotation_label(label, FORMAT_DISPLAY)
            format_lines.append(f"| {md_table_cell(shown)} | {count} |")
    else:
        format_lines.append("| （暂无标注） | 0 |")
    format_lines.extend(
        [
            "",
            "## 各卷题型列表",
            "",
            "| 试卷 | 格式 | 题型 |",
            "| --- | --- | --- |",
        ]
    )
    for row in paper_rows:
        types = ", ".join(row["types"]) or "-"
        format_shown = display_annotation_label(str(row["format"]), FORMAT_DISPLAY)
        format_lines.append(
            f"| {md_table_cell(str(row['label']))} | {md_table_cell(format_shown)} | {md_table_cell(types)} |"
        )

    diff_lines = frontmatter(course_key, exam_scope, "exam-difficulty-grading", today)
    diff_lines.extend(
        [
            f"# {course_key} · {exam_scope} · 题型难度分级",
            "",
            "根据标注中可选的 `difficulty` / `difficulty_stars` 汇总；填写题型解析后可为各题型补星级。",
            "",
            "| 试卷 | 难度 | 题型 |",
            "| --- | --- | --- |",
        ]
    )
    for row in paper_rows:
        diff_shown = display_annotation_label(str(row["difficulty"]), DIFFICULTY_DISPLAY)
        diff_lines.append(
            f"| {md_table_cell(str(row['label']))} | {md_table_cell(diff_shown)} | "
            f"{md_table_cell(', '.join(row['types']) or '-')} |"
        )

    rel_lines = frontmatter(course_key, exam_scope, "exam-paper-reliability", today)
    rel_lines.extend(
        [
            f"# {course_key} · {exam_scope} · 卷源可靠性分级",
            "",
            "根据标注中可选的 `paper_reliability` / `reliability` 汇总"
            "（答案卷 / 复习版 / 回忆版 / 未标注）。",
            "",
            "| 试卷 | 可靠性 |",
            "| --- | --- |",
        ]
    )
    for row in paper_rows:
        rel_shown = display_annotation_label(str(row["reliability"]), RELIABILITY_DISPLAY)
        rel_lines.append(f"| {md_table_cell(str(row['label']))} | {md_table_cell(rel_shown)} |")

    written: list[str] = []
    skipped: list[str] = []
    for path, lines in (
        (analysis_dir / "题型关联分析.md", co_lines),
        (analysis_dir / "分题型频率统计.md", format_lines),
        (analysis_dir / "题型难度分级.md", diff_lines),
        (analysis_dir / "卷源可靠性分级.md", rel_lines),
    ):
        if write_md(path, lines, overwrite=args.overwrite):
            written.append(str(path))
        else:
            skipped.append(str(path))

    result = {
        "course": course_key,
        "exam_scope": exam_scope,
        "analysis_dir": str(analysis_dir),
        "pair_count": len(pair_counter),
        "format_labels": dict(format_counter),
        "overwrite": args.overwrite,
        "written": written,
        "skipped_existing": skipped,
        "outputs": written + skipped,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
