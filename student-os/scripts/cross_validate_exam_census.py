#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import unquote

from course_layout import configure_stdout_utf8
from exam_census_utils import (
    course_slug_of,
    exam_scope_key,
    load_annotations_for_manifest,
    load_json,
    load_taxonomy,
    relative_posix,
    resolve_course,
    reviews_dir,
    state_dir,
    write_json,
)

PREP_PACK_FILES = {
    "prep_guide": "备考指南.md",
    "formula_card": "公式总卡.md",
    "answer_templates": "答题模板速查.md",
    "one_hour_checklist": "考前1小时清单.md",
}

PREP_PACK_TYPES = {
    "prep_guide": "exam-prep-guide",
    "formula_card": "formula-cheat-sheet",
    "answer_templates": "answer-template-quickref",
    "one_hour_checklist": "pre-exam-one-hour-checklist",
}

FILL_IN_PLACEHOLDER_RE = re.compile(
    r"\[(?:条件|表达式|值|答案|结论|中间量|步骤[0-9一二三四五六七八九十]*|占位符)\]"
)

ONE_HOUR_SLOTS = ("60-45", "45-30", "30-15", "15-5", "5-0")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase E cross-validation for exam-census coverage and prep-pack layers."
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


def extract_frontmatter_type(text: str) -> str | None:
    match = re.search(r"(?m)^type:\s*(.+)$", text)
    if not match:
        return None
    raw = match.group(1).strip()
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    return raw


def markdown_link_targets(text: str) -> list[str]:
    return [unquote(match.group(1).strip()) for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text)]


def references_path(text: str, needle: str) -> bool:
    """True if needle appears as markdown link target or literal path mention."""
    needle_norm = needle.replace("\\", "/")
    if needle_norm in text.replace("\\", "/"):
        return True
    for target in markdown_link_targets(text):
        if needle_norm in target.replace("\\", "/"):
            return True
    return False


def references_type_analysis(text: str) -> bool:
    return references_path(text, "题型解析/")


def guide_links_type(guide_text: str, type_id: str, skeleton_name: str | None) -> bool:
    """Require a navigable markdown link to the type skeleton (not plain-text co-occurrence)."""
    for target in markdown_link_targets(guide_text):
        normalized = target.replace("\\", "/")
        if skeleton_name and skeleton_name in normalized:
            return True
        if type_id and type_id in normalized and "题型解析/" in normalized:
            return True
        if type_id and "题型解析/" in normalized and type_id.replace("_", "-") in normalized:
            return True
    return False


def has_heading(text: str, title: str) -> bool:
    return bool(re.search(rf"(?m)^#{{1,6}}\s+{re.escape(title)}\b", text))


def section_body_after_heading(text: str, title: str) -> str:
    match = re.search(rf"(?m)^#{{1,6}}\s+{re.escape(title)}\b[^\n]*\n", text)
    if not match:
        return ""
    start = match.end()
    next_heading = re.search(r"(?m)^#{1,6}\s+", text[start:])
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells)


def has_filled_table_data_row(text: str) -> bool:
    """True if any markdown table has a non-header data row with at least one non-empty cell."""
    lines = [line.strip() for line in text.splitlines()]
    index = 0
    while index < len(lines):
        if not lines[index].startswith("|"):
            index += 1
            continue
        table: list[str] = []
        while index < len(lines) and lines[index].startswith("|"):
            table.append(lines[index])
            index += 1
        if len(table) < 3:
            continue
        if not _is_separator_row(_table_cells(table[1])):
            continue
        for row in table[2:]:
            cells = _table_cells(row)
            if any(cell for cell in cells):
                return True
    return False


FILLED_CHECKLIST_ITEM_RE = re.compile(r"(?m)^-\s*\[[ xX]\][ \t]+\S+")


def yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def status_mark(ok: bool) -> str:
    return "✅" if ok else "❌"


def _repo_relative(path: Path, repo: Path) -> str:
    return relative_posix(path, repo)


def validate_prep_pack(output_root: Path, analysis_dir: Path, repo: Path | None = None) -> dict:
    files_meta: dict[str, dict] = {}
    missing_files: list[str] = []
    layer_link_issues: list[str] = []
    content_issues: list[str] = []
    texts: dict[str, str] = {}
    root = repo.resolve() if repo is not None else None

    for key, filename in PREP_PACK_FILES.items():
        path = output_root / filename
        exists = path.exists()
        if exists and root is not None:
            recorded = _repo_relative(path, root)
        elif exists:
            recorded = filename
        else:
            recorded = filename
        files_meta[key] = {"exists": exists, "path": recorded}
        if not exists:
            missing_files.append(filename)
            continue
        text = path.read_text(encoding="utf-8")
        texts[key] = text
        expected_type = PREP_PACK_TYPES[key]
        actual_type = extract_frontmatter_type(text)
        if actual_type != expected_type:
            content_issues.append(
                f"{filename}: frontmatter type expected {expected_type!r}, got {actual_type!r}"
            )

    guide = texts.get("prep_guide", "")
    formula = texts.get("formula_card", "")
    templates = texts.get("answer_templates", "")
    checklist = texts.get("one_hour_checklist", "")

    if guide:
        for label, needle in (
            ("题型解析/", "题型解析/"),
            ("公式总卡.md", "公式总卡.md"),
            ("答题模板速查.md", "答题模板速查.md"),
            ("考前1小时清单.md", "考前1小时清单.md"),
        ):
            if not references_path(guide, needle):
                layer_link_issues.append(f"备考指南.md: missing link/mention of {label}")
        for section in ("怎么使用这套资料", "题型优先级", "复习时间分配"):
            if not has_heading(guide, section):
                content_issues.append(f"备考指南.md: missing section {section!r}")

    if formula:
        if not references_type_analysis(formula):
            layer_link_issues.append("公式总卡.md: missing link/mention of 题型解析/")
        if not has_heading(formula, "高频公式速查"):
            content_issues.append("公式总卡.md: missing section '高频公式速查'")
        formula_section = section_body_after_heading(formula, "高频公式速查") or formula
        if not has_filled_table_data_row(formula_section):
            content_issues.append("公式总卡.md: missing filled formula table data rows")
        if "来源" not in formula and not references_type_analysis(formula):
            content_issues.append("公式总卡.md: missing 来源 column/text or 题型解析 link")

    if templates:
        if not references_type_analysis(templates):
            layer_link_issues.append("答题模板速查.md: missing link/mention of 题型解析/")
        if not has_heading(templates, "标准答题模板"):
            content_issues.append("答题模板速查.md: missing section '标准答题模板'")
        template_section = section_body_after_heading(templates, "标准答题模板")
        if not FILL_IN_PLACEHOLDER_RE.search(template_section):
            content_issues.append(
                "答题模板速查.md: missing fill-in placeholders like [条件]/[表达式]/[答案] "
                "in 标准答题模板"
            )

    if checklist:
        for label, needle in (
            ("备考指南.md", "备考指南.md"),
            ("公式总卡.md", "公式总卡.md"),
            ("答题模板速查.md", "答题模板速查.md"),
        ):
            if not references_path(checklist, needle):
                layer_link_issues.append(f"考前1小时清单.md: missing link/mention of {label}")
        if not references_type_analysis(checklist):
            layer_link_issues.append("考前1小时清单.md: missing link/mention of 题型解析/")
        missing_slots = [slot for slot in ONE_HOUR_SLOTS if slot not in checklist]
        if missing_slots:
            content_issues.append(
                f"考前1小时清单.md: missing time slots {', '.join(missing_slots)}"
            )
        if not FILLED_CHECKLIST_ITEM_RE.search(checklist):
            content_issues.append(
                "考前1小时清单.md: missing filled checklist items (- [ ] with text)"
            )

    l2_ok = analysis_dir.exists() and any(analysis_dir.glob("*.md"))
    prep_ok = not (missing_files or layer_link_issues or content_issues)
    return {
        "files": files_meta,
        "missing_files": missing_files,
        "layer_link_issues": layer_link_issues,
        "content_issues": content_issues,
        "l2_type_analysis_ok": l2_ok,
        "ok": prep_ok and l2_ok,
    }


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
    manifest = load_json(census_state / "manifest.json")
    papers = list(manifest.get("papers") or [])
    annotations, _aliases, _errors = load_annotations_for_manifest(
        census_state / "annotations", papers
    )
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

    prep_pack = validate_prep_pack(output_root, analysis_dir, repo=repo)
    prep_guide = output_root / PREP_PACK_FILES["prep_guide"]
    guide_missing_links: list[str] = []
    guide_exists = prep_guide.exists()
    if guide_exists:
        guide_text = prep_guide.read_text(encoding="utf-8")
        for type_id in sorted(annotated_known):
            if not guide_links_type(guide_text, type_id, skeleton_ids.get(type_id)):
                guide_missing_links.append(type_id)

    today = date.today().isoformat()
    coverage_ok = not (
        papers_missing_types
        or missing_skeletons
        or unknown_annotated
        or orphan_skeletons
        or guide_missing_links
    )
    ok = coverage_ok and bool(prep_pack.get("ok"))
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
        "prep_guide_exists": guide_exists,
        "prep_guide_unlinked_types": guide_missing_links,
        "prep_pack": {
            "files": prep_pack["files"],
            "missing_files": prep_pack["missing_files"],
            "layer_link_issues": prep_pack["layer_link_issues"],
            "content_issues": prep_pack["content_issues"],
        },
        "ok": ok,
    }
    write_json(census_state / "cross-validation.json", report)

    human_dir = output_root / "analysis"
    human_dir.mkdir(parents=True, exist_ok=True)

    def file_status(key: str) -> tuple[bool, str]:
        meta = prep_pack["files"].get(key) or {}
        exists = bool(meta.get("exists"))
        issues: list[str] = []
        filename = PREP_PACK_FILES[key]
        if not exists:
            issues.append("missing")
        issues.extend(
            item.split(": ", 1)[-1]
            for item in prep_pack["layer_link_issues"] + prep_pack["content_issues"]
            if item.startswith(f"{filename}:")
        )
        return exists and not issues, "; ".join(issues) if issues else ""

    guide_ok, guide_issues = file_status("prep_guide")
    formula_ok, formula_issues = file_status("formula_card")
    templates_ok, templates_issues = file_status("answer_templates")
    checklist_ok, checklist_issues = file_status("one_hour_checklist")
    l2_ok = bool(prep_pack.get("l2_type_analysis_ok"))
    l2_issues = "" if l2_ok else "missing 题型解析/*.md"

    lines = [
        "---",
        "type: exam-census-cross-validation",
        f"course: {yaml_string(course_key)}",
        "status: active",
        f"created: {today}",
        f"updated: {today}",
        "review_scope: exam-census",
        f"exam_scope: {yaml_string(exam_scope)}",
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
        f"- Prep guide unlinked types: {len(guide_missing_links)}",
        f"- Prep pack missing files: {len(prep_pack['missing_files'])}",
        f"- Prep pack layer link issues: {len(prep_pack['layer_link_issues'])}",
        f"- Prep pack content issues: {len(prep_pack['content_issues'])}",
        "",
        "## Prep pack 四层结构",
        "",
        "| 层级 | 文件 | 状态 | 问题 |",
        "| --- | --- | --- | --- |",
        f"| L1 | 备考指南.md | {status_mark(guide_ok)} | {guide_issues} |",
        f"| L2 | 题型解析/ | {status_mark(l2_ok)} | {l2_issues} |",
        f"| L3 | 公式总卡.md | {status_mark(formula_ok)} | {formula_issues} |",
        f"| L3 | 答题模板速查.md | {status_mark(templates_ok)} | {templates_issues} |",
        f"| L4 | 考前1小时清单.md | {status_mark(checklist_ok)} | {checklist_issues} |",
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
    lines.extend(["", "## Orphan skeletons", ""])
    if orphan_skeletons:
        lines.extend([f"- `{item}`" for item in orphan_skeletons])
    else:
        lines.append("- None")
    lines.extend(["", "## Prep guide types not linked", ""])
    if not guide_exists:
        lines.append("- Prep guide missing (counted under Prep pack missing files)")
    elif guide_missing_links:
        lines.extend([f"- `{item}`" for item in guide_missing_links])
    else:
        lines.append("- None")
    lines.extend(["", "## Prep pack issues", ""])
    pack_issues = (
        [f"missing: `{item}`" for item in prep_pack["missing_files"]]
        + prep_pack["layer_link_issues"]
        + prep_pack["content_issues"]
    )
    if pack_issues:
        lines.extend([f"- {item}" for item in pack_issues])
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Agent follow-ups",
            "",
            "- Randomly sample 3 papers and manually confirm every question maps to a type analysis.",
            "- Ensure 公式总卡 formulas trace back to type-analysis formula tables (do not invent).",
            "- Ensure 答题模板速查 templates trace back to 2分钟下笔模板 / 快速得分技巧.",
            "- Re-run Phase E after updating any prep-pack layer.",
            "",
        ]
    )
    (human_dir / "覆盖率检查.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
