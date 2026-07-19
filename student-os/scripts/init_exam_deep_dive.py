#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

from course_layout import configure_stdout_utf8, slugify
from exam_census_utils import (
    course_slug_of,
    exam_scope_key,
    load_annotations_for_manifest,
    load_json,
    relative_posix,
    resolve_course,
    reviews_dir,
    state_dir,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase D: scaffold representative paper deep-dive pages from annotations."
    )
    parser.add_argument("repo", help="Target vault repository root")
    parser.add_argument("--course", required=True, help="Course slug or path under courses/")
    parser.add_argument("--exam-scope", required=True, help="Exam scope label such as 期中 or midterm")
    parser.add_argument("--semester", default="", help="Optional semester slug when resolving the course")
    parser.add_argument(
        "--limit",
        type=int,
        default=2,
        help="How many representative papers to scaffold (default: 2)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing deep-dive pages",
    )
    return parser.parse_args()


def yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def find_skeleton_for_type(analysis_dir: Path, type_id: str) -> str | None:
    if not analysis_dir.exists():
        return None
    for path in sorted(analysis_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r'(?m)^exam_type_id:\s*"?([^"\n]+)"?\s*$', text)
        if match and match.group(1) == type_id:
            return path.name
    return None


def main() -> int:
    configure_stdout_utf8()
    args = parse_args()
    if args.limit <= 0:
        raise SystemExit("--limit must be a positive integer")

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
    deep_dir = output_root / "真题精析"
    deep_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_json(census_state / "manifest.json")
    papers = list(manifest.get("papers") or [])
    annotations, _aliases, _errors = load_annotations_for_manifest(
        census_state / "annotations", papers
    )
    today = date.today().isoformat()

    ranked = sorted(
        papers,
        key=lambda item: (
            -len((annotations.get(str(item["stem"])) or {}).get("types_present") or []),
            str(item["stem"]),
        ),
    )[: args.limit]

    written: list[str] = []
    skipped: list[str] = []
    for paper in ranked:
        stem = str(paper["stem"])
        annotation = annotations.get(stem) or {}
        label = str(annotation.get("exam_label") or stem)
        source = str(paper.get("path") or annotation.get("source") or stem)
        types = [str(item) for item in (annotation.get("types_present") or [])]
        filename = f"{slugify(stem, fallback='paper')}-精析.md"
        target = deep_dir / filename
        if target.exists() and not args.overwrite:
            skipped.append(str(target))
            continue

        lines = [
            "---",
            "type: exam-paper-deep-dive",
            f"course: {yaml_string(course_key)}",
            "status: draft",
            f"created: {today}",
            f"updated: {today}",
            "review_scope: exam-census",
            f"exam_scope: {yaml_string(exam_scope)}",
            f"source_artifacts: [{yaml_string(source)}]",
            "---",
            "",
            f"# {label} · 真题精析",
            "",
            "## Why this paper",
            "",
            "- Representativeness: high type coverage in census annotations",
            f"- Reliability: {annotation.get('paper_reliability') or annotation.get('reliability') or 'unspecified'}",
            "",
            "## Question walkthrough",
            "",
        ]
        if not types:
            lines.extend(
                [
                    "### Q1",
                    "",
                    "- Type analysis: _(annotate types first)_",
                    "- Prompt:",
                    "- Method link:",
                    "- Solution outline:",
                    "",
                ]
            )
        else:
            for index, type_id in enumerate(types, start=1):
                skeleton = find_skeleton_for_type(analysis_dir, type_id) or f"NN-{type_id}.md"
                lines.extend(
                    [
                        f"### Q{index}",
                        "",
                        f"- Type analysis: [`{type_id}`](../题型解析/{skeleton})",
                        "- Prompt:",
                        "- Method link:",
                        "- Solution outline:",
                        "",
                    ]
                )
        lines.extend(
            [
                "## Coverage note",
                "",
                "- Every question above must link to an existing type-analysis page.",
                "- Orphan questions → expand taxonomy / fill queue, then re-run Phase E.",
                "",
            ]
        )
        target.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        written.append(relative_posix(target, repo))

    result = {
        "course": course_key,
        "exam_scope": exam_scope,
        "phase": "D",
        "written": written,
        "skipped": skipped,
        "deep_dive_dir": str(deep_dir),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
