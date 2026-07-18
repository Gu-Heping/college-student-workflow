#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from course_layout import configure_stdout_utf8
from exam_census_quality import analysis_report_review, structural_review
from exam_census_utils import (
    course_slug_of,
    exam_scope_key,
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

    reviews: list[dict] = []
    for path in sorted(analysis_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        reviews.append(structural_review(relative_posix(path, repo), text))

    analysis_reports_dir = review_root / "analysis"
    if analysis_reports_dir.exists():
        for path in sorted(analysis_reports_dir.glob("*.md")):
            # Gate only machine-seeded multi-dim reports; skip quality/coverage digests.
            if path.name in {"质量门禁.md", "覆盖率检查.md"}:
                continue
            text = path.read_text(encoding="utf-8")
            reviews.append(analysis_report_review(relative_posix(path, repo), text))

    passed = [item for item in reviews if item["verdict"] == "pass"]
    failed = [item for item in reviews if item["verdict"] != "pass"]
    report = {
        "course": course_key,
        "exam_scope": exam_scope,
        "exam_scope_key": scope_key,
        "phase": "B",
        "max_rounds": args.max_rounds,
        "file_count": len(reviews),
        "pass_count": len(passed),
        "needs_revision_count": len(failed),
        "reviews": reviews,
        "agent_note": (
            "Agents should revise needs-revision files at most max_rounds times; "
            "if still failing, set frontmatter quality: needs-review for humans."
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
        f"- Agent 最多修订轮数：{args.max_rounds}",
        "",
        "## 失败项",
        "",
    ]
    if not failed:
        lines.append("- 无")
    else:
        for item in failed:
            lines.append(f"- `{item['file']}` — {', '.join(item['failed_checks'])}")
    lines.append("")
    (human_dir / "质量门禁.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(json.dumps({"report": str(out_path), "pass_count": len(passed), "needs_revision_count": len(failed)}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
