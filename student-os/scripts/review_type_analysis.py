#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from course_layout import configure_stdout_utf8
from exam_census_quality import QUALITY_CHECK_LABELS, analysis_report_review, structural_review
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
        description="Phase B structural quality gate for exam-census type-analysis pages."
    )
    parser.add_argument("repo", help="Target vault repository root")
    parser.add_argument("--course", required=True, help="Course slug or path under courses/")
    parser.add_argument("--exam-scope", required=True, help="Exam scope label such as 期中 or midterm")
    parser.add_argument("--semester", default="", help="Optional semester slug when resolving the course")
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=2,
        help="Documented revision budget for agents (default: 2); encoded into review report only",
    )
    return parser.parse_args()


def yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def extract_exam_type_id(text: str) -> str | None:
    match = re.search(r"(?m)^exam_type_id:\s*(.+)$", text)
    if not match:
        return None
    raw = match.group(1).strip()
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    return raw


def check_label(name: str) -> str:
    return QUALITY_CHECK_LABELS.get(name, name)


def main() -> int:
    configure_stdout_utf8()
    args = parse_args()
    if not 0 <= args.max_rounds <= 2:
        raise SystemExit("--max-rounds must be between 0 and 2")

    repo = Path(args.repo).resolve()
    course_dir = resolve_course(repo, args.course, semester=args.semester)
    course_key = course_slug_of(course_dir, repo)
    try:
        exam_scope = args.exam_scope.strip()
        scope_key = exam_scope_key(exam_scope)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    review_root = reviews_dir(course_dir, exam_scope)
    analysis_dir = review_root / "题型解析"
    if not analysis_dir.exists():
        raise SystemExit(f"Missing type-analysis directory: {analysis_dir}")

    census_state = state_dir(repo, course_key, exam_scope)
    fill_queue_path = census_state / "fill-queue.json"
    concept_sources: list[dict[str, str]] = []
    if fill_queue_path.exists():
        queue_payload = load_json(fill_queue_path)
        raw_sources = queue_payload.get("concept_sources") or []
        if isinstance(raw_sources, list):
            concept_sources = [item for item in raw_sources if isinstance(item, dict)]

    reviews: list[dict] = []
    for path in sorted(analysis_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        review = structural_review(
            relative_posix(path, repo),
            text,
            concept_sources=concept_sources,
        )
        review["exam_type_id"] = extract_exam_type_id(text) or path.stem
        review["path"] = review["file"]
        reviews.append(review)

    analysis_reports_dir = review_root / "analysis"
    if analysis_reports_dir.exists():
        for path in sorted(analysis_reports_dir.glob("*.md")):
            # Gate only machine-seeded multi-dim reports; skip quality/coverage digests.
            if path.name in {"质量门禁.md", "覆盖率检查.md"}:
                continue
            text = path.read_text(encoding="utf-8")
            review = analysis_report_review(relative_posix(path, repo), text)
            review["path"] = review["file"]
            review["exam_type_id"] = ""
            reviews.append(review)

    passed = [item for item in reviews if item["verdict"] == "pass"]
    failed = [item for item in reviews if item["verdict"] != "pass"]
    type_failures = [item for item in failed if item.get("kind") != "analysis-report"]
    analysis_failures = [item for item in failed if item.get("kind") == "analysis-report"]
    report = {
        "course": course_key,
        "exam_scope": exam_scope,
        "exam_scope_key": scope_key,
        "phase": "B",
        "max_rounds": args.max_rounds,
        "file_count": len(reviews),
        "pass_count": len(passed),
        "needs_revision_count": len(failed),
        "type_needs_revision": [
            {
                "path": item["path"],
                "exam_type_id": item.get("exam_type_id") or "",
                "failed_checks": item["failed_checks"],
            }
            for item in type_failures
        ],
        "analysis_needs_revision": [
            {
                "path": item["path"],
                "failed_checks": item["failed_checks"],
            }
            for item in analysis_failures
        ],
        "reviews": reviews,
        "agent_note": (
            "Agents should revise needs-revision type pages at most max_rounds times; "
            "analysis-report failures should be fixed separately after Phase C. "
            "If still failing, set frontmatter quality: needs-review for humans."
        ),
    }
    out_path = state_dir(repo, course_key, exam_scope) / "quality-reviews.json"
    write_json(out_path, report)

    human_dir = analysis_reports_dir
    human_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        "type: exam-census-quality-gate",
        f"course: {yaml_string(course_key)}",
        "status: active",
        f"exam_scope: {yaml_string(exam_scope)}",
        "review_scope: exam-census",
        "---",
        "",
        f"# {course_key} · {exam_scope} · 题型解析质量门禁",
        "",
        f"- 检查文件数：{len(reviews)}",
        f"- 通过：{len(passed)}",
        f"- 需修订：{len(failed)}",
        f"- 助手最多修订轮数：{args.max_rounds}",
        "",
        "## 失败项",
        "",
    ]
    if not failed:
        lines.append("- 无")
    else:
        for item in failed:
            labels = "、".join(check_label(name) for name in item["failed_checks"])
            lines.append(f"- `{item['file']}` — {labels}")
    lines.append("")
    (human_dir / "质量门禁.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(
        json.dumps(
            {
                "report": str(out_path),
                "pass_count": len(passed),
                "needs_revision_count": len(failed),
                "type_needs_revision_count": len(type_failures),
                "analysis_needs_revision_count": len(analysis_failures),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
