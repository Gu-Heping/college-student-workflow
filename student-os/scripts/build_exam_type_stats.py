#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import date
from pathlib import Path
from typing import Any

from course_layout import configure_stdout_utf8, slugify
from exam_census_utils import (
    MUST_KNOW_RATE,
    course_slug_of,
    course_tag_slug,
    exam_scope_key,
    load_annotations,
    load_json,
    load_taxonomy,
    markdown_rel_link,
    md_table_cell,
    relative_posix,
    resolve_course,
    reviews_dir,
    state_dir,
    write_json,
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


def _positive_int_count(raw: Any) -> int | None:
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, int):
        return raw if raw > 0 else None
    if isinstance(raw, float):
        if raw.is_integer() and raw > 0:
            return int(raw)
        return None
    if isinstance(raw, str):
        text = raw.strip()
        if not re.fullmatch(r"[1-9]\d*", text):
            return None
        return int(text)
    return None


def aggregate(
    *,
    taxonomy: dict[str, Any],
    annotations: dict[str, dict[str, Any]],
    papers: list[dict[str, Any]],
    must_know_rate: float,
) -> tuple[
    list[dict[str, Any]],
    list[str],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
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
    unknown_count_keys: list[dict[str, Any]] = []
    invalid_count_values: list[dict[str, Any]] = []

    for paper in papers:
        stem = str(paper["stem"])
        annotation = annotations.get(stem)
        if annotation is None:
            missing.append(stem)
            continue
        confidence = str(annotation.get("confidence", "high")).lower()
        if confidence in {"low", "uncertain", "needs-review"}:
            low_confidence.append({"stem": stem, "confidence": confidence})

        raw_present = [str(item) for item in annotation.get("types_present") or []]
        present = list(dict.fromkeys(raw_present))
        counts = annotation.get("type_counts")
        if counts is None:
            counts = {}
        elif not isinstance(counts, dict):
            invalid_count_values.append({"stem": stem, "type_id": "*", "value": counts})
            counts = {}

        for type_id in present:
            if type_id not in known_ids:
                unknown_types.append({"stem": stem, "type_id": type_id})
                continue
            bucket = stats[type_id]
            bucket["paper_count"] += 1
            if type_id in counts:
                count_value = _positive_int_count(counts.get(type_id))
                if count_value is None:
                    invalid_count_values.append(
                        {"stem": stem, "type_id": type_id, "value": counts.get(type_id)}
                    )
                    count_value = 0
            else:
                count_value = 1
            bucket["question_count"] += count_value
            source = annotation.get("source") or paper_by_stem.get(stem, {}).get("path") or stem
            label = annotation.get("exam_label") or stem
            bucket["papers"].append({"stem": stem, "label": label, "source": source})

        present_set = set(present)
        for count_key in counts:
            key = str(count_key)
            if key not in known_ids or key not in present_set:
                unknown_count_keys.append({"stem": stem, "type_id": key})

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
    return ranked, missing, low_confidence, unknown_types, unknown_count_keys, invalid_count_values


def render_frequency_report(
    *,
    course_name: str,
    course_tag: str,
    exam_scope: str,
    taxonomy: dict[str, Any],
    paper_count: int,
    annotated_count: int,
    ranked: list[dict[str, Any]],
    missing: list[str],
    low_confidence: list[dict[str, Any]],
    unknown_types: list[dict[str, Any]],
    unknown_count_keys: list[dict[str, Any]],
    invalid_count_values: list[dict[str, Any]],
    report_path: Path,
    repo: Path,
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
        f"tags: [course/{course_tag}, review, exam-census]",
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
        "- Ranking key: paper appearance count (not raw question repeats)",
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
            "[{label}]({href})".format(
                label=md_table_cell(str(paper["label"])),
                href=markdown_rel_link(str(paper["source"]), report_path, repo),
            )
            for paper in item["papers"][:3]
        ) or "-"
        lines.append(
            "| {rank} | {name} (`{type_id}`) | {papers} | {rate:.0%} | {questions} | {must} | {samples} |".format(
                rank=index,
                name=md_table_cell(str(item["name"])),
                type_id=md_table_cell(str(item["id"])),
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

    if unknown_types:
        lines.append("### Unknown type ids in types_present")
        lines.extend([f"- `{item['stem']}` -> `{item['type_id']}`" for item in unknown_types])
        lines.append("")
    else:
        lines.extend(["### Unknown type ids in types_present", "", "- None", ""])

    if unknown_count_keys:
        lines.append("### Unknown or unmatched type_counts keys")
        lines.extend([f"- `{item['stem']}` -> `{item['type_id']}`" for item in unknown_count_keys])
        lines.append("")
    else:
        lines.extend(["### Unknown or unmatched type_counts keys", "", "- None", ""])

    if invalid_count_values:
        lines.append("### Invalid type_counts values")
        for item in invalid_count_values:
            lines.append(f"- `{item['stem']}` -> `{item['type_id']}` = `{item['value']!r}`")
        lines.append("")
    else:
        lines.extend(["### Invalid type_counts values", "", "- None", ""])

    scope_key = exam_scope_key(exam_scope)
    lines.extend(
        [
            "## Next Steps",
            "",
            f"- Fill `reviews/{scope_key}/题型解析/` skeletons in frequency order.",
            "- Draft `备考指南.md`, `公式总卡.md`, `答题模板速查.md`, and `考前1小时清单.md`.",
            "",
        ]
    )
    return "\n".join(lines)


def fingerprint_skeleton_body(text: str, *, keep_source_artifacts: bool = False) -> str:
    # Strip machine-only fingerprint line, then hash.
    normalized = re.sub(r"(?m)^generated_fingerprint:\s*.*\n?", "", text)
    if not keep_source_artifacts:
        normalized = re.sub(r"(?m)^source_artifacts:\s*\[.*\]\s*\n?", "", normalized)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def extract_fingerprint(text: str) -> str | None:
    match = re.search(r'(?m)^generated_fingerprint:\s*"?([a-f0-9]+)"?\s*$', text)
    if not match:
        return None
    return match.group(1)


def fingerprint_matches(text: str, expected: str) -> bool:
    if fingerprint_skeleton_body(text) == expected:
        return True
    # Legacy skeletons hashed with the bulky source_artifacts line still present.
    return fingerprint_skeleton_body(text, keep_source_artifacts=True) == expected


def fingerprint_store_path(census_state: Path) -> Path:
    return census_state / "skeleton-fingerprints.json"


def load_fingerprint_store(census_state: Path) -> dict[str, str]:
    path = fingerprint_store_path(census_state)
    if not path.exists():
        return {}
    try:
        payload = load_json(path)
    except (OSError, json.JSONDecodeError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items()}


def save_fingerprint_store(census_state: Path, store: dict[str, str]) -> None:
    write_json(fingerprint_store_path(census_state), store)


def source_summary_text(paper_count: int) -> str:
    return f"共 {paper_count} 份试卷；详见 题型频率统计.md"


def render_type_skeleton(
    *,
    course_name: str,
    course_tag: str,
    exam_scope: str,
    item: dict[str, Any],
    rank: int,
    today: str,
    target_path: Path,
    repo: Path,
) -> str:
    paper_count = int(item["paper_count"])
    source_summary = source_summary_text(paper_count)
    lines = [
        "---",
        "type: exam-type-analysis",
        f"course: {yaml_string(course_name)}",
        f"exam_scope: {yaml_string(exam_scope)}",
        f"exam_type_id: {yaml_string(item['id'])}",
        f"exam_type_name: {yaml_string(str(item['name']))}",
        f"rank: {rank}",
        f"paper_count: {paper_count}",
        f"must_know: {'true' if item['must_know'] else 'false'}",
        "quality: draft",
        "status: active",
        f"source_summary: {yaml_string(source_summary)}",
        "---",
        "",
        f"# {rank:02d} · {item['name']}",
        "",
        "## 普查信号",
        "",
        f"- 出现率：{item['appearance_rate']:.0%}（{paper_count} 份试卷）",
        f"- 标注题量：{item['question_count']}",
        f"- 必掌握：{'是' if item['must_know'] else '否'}",
        "",
        "## 来源依据",
        "",
        f"- {source_summary}",
        "",
    ]
    if item["papers"]:
        for paper in item["papers"]:
            href = markdown_rel_link(str(paper["source"]), target_path, repo)
            lines.append(f"- [{paper['label']}]({href})")
    else:
        lines.append("- （暂无试卷命中）")
    lines.extend(
        [
            "",
            "## 方法提纲",
            "",
            "- _(fill by review-coach)_",
            "",
            "## 易错点",
            "",
            "- _(fill by review-coach)_",
            "",
            "## 练习目标",
            "",
            "- [ ] 重做一道高频真题",
            "- [ ] 不看笔记复述核心方法",
            "",
        ]
    )
    return "\n".join(lines)


def extract_exam_type_id(text: str) -> str | None:
    match = re.search(r"(?m)^exam_type_id:\s*(.+)$", text)
    if not match:
        return None
    raw = match.group(1).strip()
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    return raw


def extract_frontmatter_quality(text: str) -> str | None:
    match = re.search(r"(?m)^quality:\s*(.+)$", text)
    if not match:
        return None
    raw = match.group(1).strip()
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    return raw


def is_generated_skeleton(text: str, *, type_id: str | None = None, store: dict[str, str] | None = None) -> bool:
    expected = extract_fingerprint(text)
    if expected is None and store is not None and type_id:
        expected = store.get(type_id)
    if not expected:
        # No trusted fingerprint → treat as user-owned (never overwrite from a weak heuristic).
        return False
    return fingerprint_matches(text, expected)


def find_skeletons_by_type_id(analysis_dir: Path) -> dict[str, list[Path]]:
    mapping: dict[str, list[Path]] = {}
    if not analysis_dir.exists():
        return mapping
    for path in sorted(analysis_dir.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        type_id = extract_exam_type_id(text)
        if not type_id:
            continue
        mapping.setdefault(type_id, []).append(path)
    return mapping


def _split_frontmatter_and_body(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    match = re.match(r"^---\r?\n(.*?)\r?\n---\s*(?:\r?\n)?(.*)$", text, flags=re.S)
    if not match:
        return "", text
    return match.group(1), match.group(2)


def update_census_metadata_in_text(
    text: str,
    *,
    rank: int,
    item: dict[str, Any],
    course_name: str,
    exam_scope: str,
) -> str:
    """Refresh generated census frontmatter while preserving the user-authored body."""
    _old_fm, body = _split_frontmatter_and_body(text)
    quality = extract_frontmatter_quality(text) or "draft"
    paper_count = int(item["paper_count"])
    source_summary = source_summary_text(paper_count)
    frontmatter = "\n".join(
        [
            "---",
            "type: exam-type-analysis",
            f"course: {yaml_string(course_name)}",
            f"exam_scope: {yaml_string(exam_scope)}",
            f"exam_type_id: {yaml_string(item['id'])}",
            f"exam_type_name: {yaml_string(str(item['name']))}",
            f"rank: {rank}",
            f"paper_count: {paper_count}",
            f"must_know: {'true' if item['must_know'] else 'false'}",
            f"quality: {quality}",
            "status: active",
            f"source_summary: {yaml_string(source_summary)}",
            "---",
            "",
        ]
    )
    updated_body = re.sub(r"(?m)^#\s+\d+\s*·", f"# {rank:02d} ·", body, count=1)
    return frontmatter + updated_body.lstrip("\n")


def _archive_path(analysis_dir: Path, path: Path) -> Path:
    archive_dir = analysis_dir / "_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    destination = archive_dir / path.name
    if destination.exists():
        stem = path.stem
        suffix = path.suffix
        index = 1
        while True:
            candidate = archive_dir / f"{stem}-{index}{suffix}"
            if not candidate.exists():
                destination = candidate
                break
            index += 1
    return destination


def remove_or_archive_skeleton(
    analysis_dir: Path,
    path: Path,
    *,
    type_id: str | None = None,
    store: dict[str, str] | None = None,
) -> str:
    """Delete unchanged generated skeletons; archive everything else."""
    text = path.read_text(encoding="utf-8")
    resolved_type = type_id or extract_exam_type_id(text)
    if is_generated_skeleton(text, type_id=resolved_type, store=store):
        path.unlink(missing_ok=True)
        return "deleted"
    destination = _archive_path(analysis_dir, path)
    shutil.move(str(path), str(destination))
    return "archived"


def reconcile_skeleton(
    *,
    analysis_dir: Path,
    target: Path,
    type_id: str,
    rank: int,
    body: str,
    overwrite: bool,
    existing_by_type: dict[str, list[Path]],
    fingerprint_store: dict[str, str],
    item: dict[str, Any],
    course_name: str,
    exam_scope: str,
) -> tuple[str, str | None]:
    """Write/reconcile one skeleton. Returns (action, path)."""
    analysis_dir.mkdir(parents=True, exist_ok=True)
    existing = list(existing_by_type.get(type_id, []))
    others = [path for path in existing if path.resolve() != target.resolve()]

    def _is_user(path: Path) -> bool:
        return not is_generated_skeleton(
            path.read_text(encoding="utf-8"), type_id=type_id, store=fingerprint_store
        )

    if not overwrite and others:
        # Alternate path already holds this type id — do not migrate or delete.
        if target.exists():
            return "skipped", str(target)
        return "skipped", str(others[-1])

    if overwrite and others:
        user_sources = [path for path in others if _is_user(path)]
        target_is_user = target.exists() and _is_user(target)

        if target_is_user:
            # Protect the existing target; archive alternate paths first.
            for path in others:
                remove_or_archive_skeleton(
                    analysis_dir, path, type_id=type_id, store=fingerprint_store
                )
            migrated = update_census_metadata_in_text(
                target.read_text(encoding="utf-8"),
                rank=rank,
                item=item,
                course_name=course_name,
                exam_scope=exam_scope,
            )
            write_text(target, migrated, overwrite=True)
            fingerprint_store.pop(type_id, None)
            return "migrated", str(target)

        if user_sources:
            # Prefer a single user source; archive every other alternate first.
            source = user_sources[-1]
            for path in others:
                if path.resolve() == source.resolve():
                    continue
                remove_or_archive_skeleton(
                    analysis_dir, path, type_id=type_id, store=fingerprint_store
                )
            migrated = update_census_metadata_in_text(
                source.read_text(encoding="utf-8"),
                rank=rank,
                item=item,
                course_name=course_name,
                exam_scope=exam_scope,
            )
            remove_or_archive_skeleton(
                analysis_dir, source, type_id=type_id, store=fingerprint_store
            )
            write_text(target, migrated, overwrite=True)
            fingerprint_store.pop(type_id, None)
            return "migrated", str(target)

        for path in others:
            remove_or_archive_skeleton(
                analysis_dir, path, type_id=type_id, store=fingerprint_store
            )

    target_exists = target.exists()
    target_text = target.read_text(encoding="utf-8") if target_exists else ""
    target_is_generated = (not target_exists) or is_generated_skeleton(
        target_text, type_id=type_id, store=fingerprint_store
    )

    if target_exists and not target_is_generated:
        if overwrite:
            write_text(
                target,
                update_census_metadata_in_text(
                    target_text,
                    rank=rank,
                    item=item,
                    course_name=course_name,
                    exam_scope=exam_scope,
                ),
                overwrite=True,
            )
            fingerprint_store.pop(type_id, None)
            return "migrated", str(target)
        return "skipped", str(target)

    if target_exists and not overwrite:
        return "skipped", str(target)

    write_text(target, body, overwrite=True)
    fingerprint_store[type_id] = fingerprint_skeleton_body(body)
    return "written", str(target)


def retire_obsolete_generated(
    *,
    analysis_dir: Path,
    keep_type_ids: set[str],
    existing_by_type: dict[str, list[Path]],
    fingerprint_store: dict[str, str],
) -> list[str]:
    retired: list[str] = []
    for type_id, paths in existing_by_type.items():
        if type_id in keep_type_ids:
            continue
        for path in paths:
            try:
                action = remove_or_archive_skeleton(
                    analysis_dir, path, type_id=type_id, store=fingerprint_store
                )
            except OSError:
                continue
            retired.append(f"{action}:{path}")
        fingerprint_store.pop(type_id, None)
    return retired


def has_validation_errors(
    missing: list[str],
    unknown_types: list[dict[str, Any]],
    unknown_count_keys: list[dict[str, Any]],
    invalid_count_values: list[dict[str, Any]],
) -> bool:
    return bool(missing or unknown_types or unknown_count_keys or invalid_count_values)


def main() -> int:
    configure_stdout_utf8()
    args = parse_args()
    if not 0 <= args.must_know_rate <= 1:
        raise SystemExit("--must-know-rate must be between 0 and 1")

    repo = Path(args.repo).resolve()
    course_dir = resolve_course(repo, args.course, semester=args.semester)
    course_key = course_slug_of(course_dir, repo)
    course_tag = course_tag_slug(course_key)
    try:
        exam_scope = args.exam_scope.strip()
        scope_key = exam_scope_key(exam_scope)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    census_state = state_dir(repo, course_key, exam_scope)
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
    course_name = str(taxonomy.get("course") or course_key)

    ranked, missing, low_confidence, unknown_types, unknown_count_keys, invalid_count_values = aggregate(
        taxonomy=taxonomy,
        annotations=annotations,
        papers=papers,
        must_know_rate=args.must_know_rate,
    )
    annotated_count = len(papers) - len(missing)
    today = date.today().isoformat()
    validation_failed = has_validation_errors(
        missing, unknown_types, unknown_count_keys, invalid_count_values
    )

    report = render_frequency_report(
        course_name=course_name,
        course_tag=course_tag,
        exam_scope=exam_scope,
        taxonomy=taxonomy,
        paper_count=len(papers),
        annotated_count=annotated_count,
        ranked=ranked,
        missing=missing,
        low_confidence=low_confidence,
        unknown_types=unknown_types,
        unknown_count_keys=unknown_count_keys,
        invalid_count_values=invalid_count_values,
        report_path=report_path,
        repo=repo,
        today=today,
    )
    # Always refresh the durable report so Validation stays visible.
    wrote_report = write_text(report_path, report, overwrite=True)

    written_skeletons: list[str] = []
    skipped_skeletons: list[str] = []
    migrated_skeletons: list[str] = []
    retired: list[str] = []
    keep_type_ids: set[str] = set()
    skip_skeletons = bool(args.validate and validation_failed)
    fingerprint_store = load_fingerprint_store(census_state)

    if not skip_skeletons:
        existing_by_type = find_skeletons_by_type_id(analysis_dir)
        for index, item in enumerate(ranked, start=1):
            if item["paper_count"] <= 0:
                continue
            keep_type_ids.add(str(item["id"]))
            filename = f"{index:02d}-{slugify(item['id'], fallback='type')}.md"
            target = analysis_dir / filename
            body = render_type_skeleton(
                course_name=course_name,
                course_tag=course_tag,
                exam_scope=exam_scope,
                item=item,
                rank=index,
                today=today,
                target_path=target,
                repo=repo,
            )
            action, path = reconcile_skeleton(
                analysis_dir=analysis_dir,
                target=target,
                type_id=str(item["id"]),
                rank=index,
                body=body,
                overwrite=args.overwrite,
                existing_by_type=existing_by_type,
                fingerprint_store=fingerprint_store,
                item=item,
                course_name=course_name,
                exam_scope=exam_scope,
            )
            if action == "written" and path:
                written_skeletons.append(relative_posix(Path(path), repo))
            elif action == "migrated" and path:
                migrated_skeletons.append(relative_posix(Path(path), repo))
            elif action == "skipped" and path:
                skipped_skeletons.append(relative_posix(Path(path), repo))

        if args.overwrite:
            existing_by_type = find_skeletons_by_type_id(analysis_dir)
            retired = []
            for entry in retire_obsolete_generated(
                analysis_dir=analysis_dir,
                keep_type_ids=keep_type_ids,
                existing_by_type=existing_by_type,
                fingerprint_store=fingerprint_store,
            ):
                _action, _, path_text = entry.partition(":")
                retired.append(relative_posix(Path(path_text or entry), repo))
        save_fingerprint_store(census_state, fingerprint_store)

    result = {
        "repo": str(repo),
        "course": course_key,
        "exam_scope": exam_scope,
        "exam_scope_key": scope_key,
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
        "skeletons_migrated": migrated_skeletons,
        "skeletons_skipped": skipped_skeletons,
        "skeletons_retired": retired,
        "skeletons_skipped_due_to_validate": skip_skeletons,
        "missing_annotations": missing,
        "low_confidence": low_confidence,
        "unknown_types": unknown_types,
        "unknown_count_keys": unknown_count_keys,
        "invalid_count_values": invalid_count_values,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.validate and validation_failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
