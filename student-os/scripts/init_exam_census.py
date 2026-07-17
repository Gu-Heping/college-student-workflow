#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from course_layout import configure_stdout_utf8
from exam_census_utils import (
    DEFAULT_BATCH_SIZE,
    annotation_stem,
    chunk_batches,
    course_slug_of,
    default_taxonomy,
    discover_papers,
    relative_posix,
    resolve_course,
    reviews_dir,
    state_dir,
    write_json,
    write_taxonomy,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize exam-census state: scan paper sidecars and write manifest.json."
    )
    parser.add_argument("repo", help="Target vault repository root")
    parser.add_argument("--course", required=True, help="Course slug or path under courses/")
    parser.add_argument("--exam-scope", required=True, help="Exam scope label such as 期中 or midterm")
    parser.add_argument(
        "--papers-dir",
        help="Directory that contains .pdf.md paper sidecars (relative to repo or absolute)",
    )
    parser.add_argument(
        "--pattern",
        default="**/*.pdf.md",
        help="Glob under papers-dir (default: **/*.pdf.md)",
    )
    parser.add_argument("--semester", default="", help="Optional semester slug when resolving the course")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Papers per parallel annotation batch (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing manifest.json (keeps annotations/ and taxonomy.yaml unless missing)",
    )
    return parser.parse_args()


def main() -> int:
    configure_stdout_utf8()
    args = parse_args()
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be a positive integer")

    repo = Path(args.repo).resolve()
    course_dir = resolve_course(repo, args.course, semester=args.semester)
    course_slug = course_slug_of(course_dir, repo)
    exam_scope = args.exam_scope.strip()
    census_state = state_dir(repo, course_slug, exam_scope)
    annotations_dir = census_state / "annotations"
    manifest_path = census_state / "manifest.json"
    taxonomy_path = census_state / "taxonomy.yaml"
    output_reviews = reviews_dir(course_dir, exam_scope)

    if args.papers_dir:
        papers_root = Path(args.papers_dir)
        papers_dir = papers_root if papers_root.is_absolute() else (repo / papers_root)
    else:
        papers_dir = course_dir / "references"

    papers = discover_papers(papers_dir.resolve(), args.pattern)
    if not papers:
        raise SystemExit(f"No .pdf.md papers found under {papers_dir} with pattern {args.pattern!r}")

    if manifest_path.exists() and not args.overwrite:
        raise SystemExit(f"Manifest already exists: {manifest_path}. Re-run with --overwrite to replace it.")

    paper_entries = []
    for paper in papers:
        paper_entries.append(
            {
                "path": relative_posix(paper, repo),
                "annotation": f"annotations/{annotation_stem(paper)}.json",
                "stem": annotation_stem(paper),
            }
        )

    batches = []
    for index, batch in enumerate(chunk_batches(paper_entries, args.batch_size), start=1):
        batches.append(
            {
                "id": f"batch-{index:02d}",
                "papers": [item["stem"] for item in batch],
            }
        )

    manifest = {
        "version": 1,
        "created": date.today().isoformat(),
        "updated": date.today().isoformat(),
        "course": course_slug,
        "course_path": relative_posix(course_dir, repo),
        "exam_scope": exam_scope,
        "papers_dir": relative_posix(papers_dir.resolve(), repo),
        "pattern": args.pattern,
        "batch_size": args.batch_size,
        "state_dir": relative_posix(census_state, repo),
        "reviews_dir": relative_posix(output_reviews, repo),
        "paper_count": len(paper_entries),
        "papers": paper_entries,
        "batches": batches,
    }

    annotations_dir.mkdir(parents=True, exist_ok=True)
    output_reviews.mkdir(parents=True, exist_ok=True)
    (output_reviews / "题型解析").mkdir(parents=True, exist_ok=True)
    write_json(manifest_path, manifest)

    if not taxonomy_path.exists():
        course_name = course_slug.replace("-", " ")
        index_path = course_dir / "index.md"
        if index_path.exists():
            # Prefer a readable course title from the first markdown heading when present.
            for line in index_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("# "):
                    course_name = line[2:].strip() or course_name
                    break
        write_taxonomy(taxonomy_path, default_taxonomy(course_name, exam_scope))

    result = {
        "repo": str(repo),
        "course": course_slug,
        "exam_scope": exam_scope,
        "state_dir": str(census_state),
        "manifest": str(manifest_path),
        "taxonomy": str(taxonomy_path),
        "reviews_dir": str(output_reviews),
        "paper_count": len(paper_entries),
        "batch_count": len(batches),
        "batches": batches,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
