#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from course_layout import configure_stdout_utf8
from exam_census_utils import (
    DEFAULT_BATCH_SIZE,
    annotation_id,
    chunk_batches,
    course_slug_of,
    course_tag_slug,
    default_taxonomy,
    discover_papers,
    exam_scope_key,
    relative_posix,
    resolve_course,
    resolve_papers_dir,
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
    course_key = course_slug_of(course_dir, repo)
    try:
        exam_scope = args.exam_scope.strip()
        exam_scope_key(exam_scope)  # validate early for clear errors
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    census_state = state_dir(repo, course_key, exam_scope)
    annotations_dir = census_state / "annotations"
    manifest_path = census_state / "manifest.json"
    taxonomy_path = census_state / "taxonomy.yaml"
    output_reviews = reviews_dir(course_dir, exam_scope)

    if args.papers_dir:
        papers_root = Path(args.papers_dir)
        papers_dir = papers_root if papers_root.is_absolute() else (repo / papers_root)
    else:
        papers_dir = course_dir / "references"
    papers_dir = papers_dir.resolve()
    papers_dir, papers_subdir_fallback = resolve_papers_dir(papers_dir, args.pattern)

    papers = discover_papers(papers_dir, args.pattern)
    if not papers:
        raise SystemExit(f"No .pdf.md papers found under {papers_dir} with pattern {args.pattern!r}")

    if manifest_path.exists() and not args.overwrite:
        raise SystemExit(f"Manifest already exists: {manifest_path}. Re-run with --overwrite to replace it.")

    paper_entries = []
    seen_ids: dict[str, str] = {}
    for paper in papers:
        paper_key = annotation_id(paper, papers_dir)
        paper_path = relative_posix(paper, repo)
        if paper_key in seen_ids:
            raise SystemExit(
                f"Annotation id collision for {paper_key!r}: {seen_ids[paper_key]} and {paper_path}. "
                "Rename one of the papers or narrow --pattern."
            )
        seen_ids[paper_key] = paper_path
        paper_entries.append(
            {
                "path": paper_path,
                "annotation": f"annotations/{paper_key}.json",
                "stem": paper_key,
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
        "course": course_key,
        "course_tag": course_tag_slug(course_key),
        "course_path": relative_posix(course_dir, repo),
        "exam_scope": exam_scope,
        "papers_dir": relative_posix(papers_dir, repo),
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
        course_name = course_tag_slug(course_key).replace("-", " ")
        index_path = course_dir / "index.md"
        if index_path.exists():
            for line in index_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("# "):
                    course_name = line[2:].strip() or course_name
                    break
        write_taxonomy(taxonomy_path, default_taxonomy(course_name, exam_scope))

    result = {
        "repo": str(repo),
        "course": course_key,
        "exam_scope": exam_scope,
        "papers_dir": relative_posix(papers_dir, repo),
        "papers_dir_fallback_subdir": papers_subdir_fallback,
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
