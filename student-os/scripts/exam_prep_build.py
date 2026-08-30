#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from course_layout import configure_stdout_utf8
from exam_census_utils import (
    annotation_id,
    course_slug_of,
    course_tag_slug,
    discover_papers,
    exam_scope_key,
    relative_posix,
    resolve_course,
    resolve_papers_dir,
    reviews_dir,
    write_json,
)


SCHEMA_VERSION = 1
WORKFLOW = "ai-first-exam-prep"
CORE_ANALYSIS_FILES = [
    "01-题型频率统计.md",
    "02-跨年原题重复记录.md",
    "03-教材或课件覆盖分析.md",
    "04-典型题或作业覆盖分析.md",
    "05-近年趋势与教考分离.md",
]
PREP_PACK_FILES = {
    "guide": "期末考试备考指南.md",
    "formula_card": "期末公式总卡.md",
    "answer_templates": "期末答题模板速查.md",
    "one_hour_checklist": "考前1小时清单.md",
}
PHASES = [
    "paper_deep_dive_v0",
    "cross_paper_synthesis",
    "paper_deep_dive_v1_backfill",
    "type_dossier",
    "type_analysis",
    "final_prep_pack",
    "quality_check",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Initialize an AI-first exam prep workspace. Scripts manage tasks and "
            "evidence; agents read papers and write the teaching material."
        )
    )
    parser.add_argument("repo", help="Target learning vault root")
    parser.add_argument("--course", required=True, help="Course slug or path under courses/")
    parser.add_argument("--exam-scope", required=True, help="Exam scope label such as 期中 or 期末")
    parser.add_argument(
        "--papers-dir",
        required=True,
        help="Directory containing paper .pdf.md sidecars (relative to repo or absolute)",
    )
    parser.add_argument("--pattern", default="**/*.pdf.md", help="Glob under papers-dir")
    parser.add_argument("--semester", default="", help="Optional semester slug when resolving course")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace manifest/task/status files. Existing AI-authored review artifacts are kept.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable result")
    return parser.parse_args()


def exam_prep_state_dir(repo: Path, course_key: str, exam_scope: str) -> Path:
    return repo / ".student-os" / "state" / "exam-prep" / Path(course_key) / exam_scope_key(exam_scope)


def _resolve_papers_root(repo: Path, papers_dir_arg: str) -> Path:
    raw = Path(papers_dir_arg)
    return raw.resolve() if raw.is_absolute() else (repo / raw).resolve()


def _write_if_missing(path: Path, text: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def _frontmatter(doc_type: str, course: str, exam_scope: str) -> str:
    return (
        "---\n"
        f"type: {doc_type}\n"
        f"course: {course}\n"
        f"exam_scope: {exam_scope}\n"
        "status: draft\n"
        "review_scope: exam-prep\n"
        "---\n\n"
    )


def _prep_title(exam_scope: str, suffix: str) -> str:
    return f"{exam_scope}{suffix}" if exam_scope else suffix


def _initial_pack_text(kind: str, course: str, exam_scope: str) -> str:
    if kind == "guide":
        return (
            _frontmatter("exam-prep-guide", course, exam_scope)
            + f"# {course} · {exam_scope} · 考试备考指南\n\n"
            "## 怎么使用这套资料\n\n"
            "| 层级 | 文件 | 用途 |\n| --- | --- | --- |\n"
            "| L1 | 本文件 | 复习优先级、时间分配、风险说明 |\n"
            "| L2 | [题型解析/](题型解析/) | 逐题型学习方法与真题例题 |\n"
            "| L3 | [期末公式总卡.md](期末公式总卡.md) / [期末答题模板速查.md](期末答题模板速查.md) | 背公式与套模板 |\n"
            "| L4 | [考前1小时清单.md](考前1小时清单.md) | 最后冲刺 |\n\n"
            "## 题型优先级\n\n"
            "> AI 读取 `试卷精析/` 与 `题目卡/` 后填写。不要只依据脚本统计。\n\n"
            "## 复习时间分配\n\n"
            "> AI 按高频题型、近年趋势和用户剩余时间填写。\n"
        )
    if kind == "formula_card":
        return (
            _frontmatter("formula-cheat-sheet", course, exam_scope)
            + f"# {course} · {exam_scope} · 公式总卡\n\n"
            "## 高频公式速查\n\n"
            "| 题型 | 看到什么 | 公式 / 结论 | 先算什么 | 来源 |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 待 AI 从题型解析提取 | | | | [题型解析/](题型解析/) |\n"
        )
    if kind == "answer_templates":
        return (
            _frontmatter("answer-template-quickref", course, exam_scope)
            + f"# {course} · {exam_scope} · 答题模板速查\n\n"
            "## 标准答题模板\n\n"
            "| 题型 | 识别特征 | 第一句写什么 | 填空式模板 | 来源 |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 待 AI 从题型解析提取 | | | 由[条件]，可得[结论]，因此[答案]。 | [题型解析/](题型解析/) |\n"
        )
    return (
        _frontmatter("pre-exam-one-hour-checklist", course, exam_scope)
        + f"# {course} · {exam_scope} · 考前1小时清单\n\n"
        "## 最后 60 分钟怎么用\n\n"
        "| 时间 | 做什么 | 文件 | 目标 |\n"
        "| --- | --- | --- | --- |\n"
        "| 60-45 分钟 | 看 P0 高频题型 | [期末考试备考指南.md](期末考试备考指南.md) | 明确先后顺序 |\n"
        "| 45-30 分钟 | 背公式 | [期末公式总卡.md](期末公式总卡.md) | 只背会用的公式 |\n"
        "| 30-15 分钟 | 背答题模板 | [期末答题模板速查.md](期末答题模板速查.md) | 保步骤分 |\n"
        "| 15-5 分钟 | 看易错清单 | [题型解析/](题型解析/) | 避免低级错 |\n"
        "| 5-0 分钟 | 停止刷新题 | 本文件 | 稳住 |\n"
    )


def _analysis_text(filename: str, course: str, exam_scope: str) -> str:
    title = filename.removesuffix(".md")
    return (
        _frontmatter("exam-prep-analysis", course, exam_scope)
        + f"# {course} · {exam_scope} · {title}\n\n"
        "> AI 从 `题目卡/`、`试卷精析/` 和真实来源材料整理。脚本不自动生成语义结论。\n\n"
        "## 待整理\n\n"
        "- 证据来源：\n"
        "- 结论：\n"
    )


def _readme_text(course: str, exam_scope: str) -> str:
    return (
        f"# {course} · {exam_scope} · AI-first exam prep workspace\n\n"
        "默认顺序：逐卷精析 → 题目卡 → AI 归纳题型 → 备考资料包 → 机械验收。\n\n"
        "脚本只管理任务、路径、证据索引和机械检查；不要把脚本统计当成最终考试分析。\n"
    )


def build(repo: Path, args: argparse.Namespace) -> dict[str, Any]:
    course_dir = resolve_course(repo, args.course, semester=args.semester)
    course_key = course_slug_of(course_dir, repo)
    scope = args.exam_scope.strip()
    exam_scope_key(scope)

    papers_root = _resolve_papers_root(repo, args.papers_dir)
    papers_dir, fallback_subdir, effective_pattern = resolve_papers_dir(papers_root, args.pattern)
    papers = discover_papers(papers_dir, effective_pattern)
    if not papers:
        raise SystemExit(f"No .pdf.md papers found under {papers_dir} with pattern {effective_pattern!r}")

    state = exam_prep_state_dir(repo, course_key, scope)
    output_root = reviews_dir(course_dir, scope)
    paper_cards_dir = state / "paper-cards"
    type_dossiers_dir = state / "type-dossiers"
    manifest_path = state / "manifest.json"
    paper_tasks_path = state / "paper-tasks.json"
    synthesis_tasks_path = state / "synthesis-tasks.json"
    backfill_tasks_path = state / "backfill-tasks.json"
    type_dossier_tasks_path = state / "type-dossier-tasks.json"
    type_analysis_tasks_path = state / "type-analysis-tasks.json"
    taxonomy_path = state / "taxonomy.json"
    status_path = state / "build-status.json"

    if manifest_path.exists() and not args.overwrite:
        raise SystemExit(f"Exam-prep manifest already exists: {manifest_path}. Re-run with --overwrite to replace it.")

    for directory in (
        output_root,
        output_root / "试卷精析",
        output_root / "题目卡",
        output_root / "题型备课卡",
        output_root / "题型解析",
        output_root / "分析",
        paper_cards_dir,
        type_dossiers_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    paper_entries: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    for paper in papers:
        paper_id = annotation_id(paper, papers_dir)
        paper_rel = relative_posix(paper, repo)
        deep_dive_rel = relative_posix(output_root / "试卷精析" / f"{paper_id}.md", repo)
        readable_card_rel = relative_posix(output_root / "题目卡" / f"{paper_id}.md", repo)
        state_card_rel = relative_posix(paper_cards_dir / f"{paper_id}.json", repo)
        paper_entries.append(
            {
                "id": paper_id,
                "path": paper_rel,
                "deep_dive": deep_dive_rel,
                "readable_card": readable_card_rel,
                "paper_card": state_card_rel,
            }
        )
        tasks.append(
            {
                "id": paper_id,
                "status": "pending-ai-analysis",
                "source": paper_rel,
                "write_deep_dive": deep_dive_rel,
                "write_readable_card": readable_card_rel,
                "write_paper_card": state_card_rel,
                "instructions": [
                    "Read the paper sidecar and any answer/source evidence available nearby.",
                    "Write a teaching-oriented v0 paper deep dive using only within-paper evidence.",
                    "Write a paper-card JSON with question_id, prompt_summary, solution_summary, initial_type, evidence_refs, confidence, repeat_status, and notes.",
                    "For v0, set repeat_status to unknown-pending-cross-paper-analysis or needs-review; do not assert original-repeat/variant yet.",
                    "Use low/needs-review confidence when the source is unclear instead of guessing.",
                ],
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "workflow": WORKFLOW,
        "created": date.today().isoformat(),
        "updated": date.today().isoformat(),
        "course": course_key,
        "course_tag": course_tag_slug(course_key),
        "course_path": relative_posix(course_dir, repo),
        "exam_scope": scope,
        "papers_dir": relative_posix(papers_dir, repo),
        "papers_dir_fallback_subdir": fallback_subdir,
        "pattern": effective_pattern,
        "state_dir": relative_posix(state, repo),
        "reviews_dir": relative_posix(output_root, repo),
        "paper_count": len(paper_entries),
        "papers": paper_entries,
        "agent_contract": {
            "semantic_owner": "ai-agent",
            "script_role": "task-state-and-mechanical-validation",
            "default_order": [
                "paper_deep_dive_v0",
                "paper_card",
                "cross_paper_synthesis",
                "paper_deep_dive_v1_backfill",
                "type_dossier",
                "type_analysis",
                "prep_pack",
                "quality_check",
            ],
            "repeat_analysis_rule": "Original-repeat, close-variant, same-type, and trends are written after cross-paper synthesis, then backfilled into paper deep dives.",
        },
    }
    write_json(manifest_path, manifest)
    write_json(
        paper_tasks_path,
        {
            "schema_version": SCHEMA_VERSION,
            "workflow": WORKFLOW,
            "phase": "paper_deep_dive_v0",
            "course": course_key,
            "exam_scope": scope,
            "tasks": tasks,
        },
    )
    write_json(
        synthesis_tasks_path,
        {
            "schema_version": SCHEMA_VERSION,
            "workflow": WORKFLOW,
            "phase": "cross_paper_synthesis",
            "course": course_key,
            "exam_scope": scope,
            "status": "blocked-until-paper-v0-complete",
            "inputs": [
                relative_posix(paper_tasks_path, repo),
                relative_posix(paper_cards_dir, repo),
                relative_posix(output_root / "试卷精析", repo),
            ],
            "outputs": [
                relative_posix(taxonomy_path, repo),
                relative_posix(output_root / "分析" / "01-题型频率统计.md", repo),
                relative_posix(output_root / "分析" / "02-跨年原题重复记录.md", repo),
                relative_posix(output_root / "分析" / "05-近年趋势与教考分离.md", repo),
            ],
            "instructions": [
                "Read all paper-card JSONs and representative v0 paper deep dives.",
                "Cluster same-type questions and identify original repeats or close variants with confidence.",
                "Every cross-paper conclusion must cite paper-card question refs.",
            ],
        },
    )
    write_json(
        backfill_tasks_path,
        {
            "schema_version": SCHEMA_VERSION,
            "workflow": WORKFLOW,
            "phase": "paper_deep_dive_v1_backfill",
            "course": course_key,
            "exam_scope": scope,
            "status": "blocked-until-synthesis-complete",
            "tasks": [
                {
                    "id": item["id"],
                    "status": "pending-cross-paper-backfill",
                    "target": item["deep_dive"],
                    "source_card": item["paper_card"],
                    "instructions": [
                        "Add or update a cross-paper relationship section.",
                        "Include type links, repeat/variant status, related years/questions, review priority, and source refs.",
                        "Do not rewrite the whole v0 deep dive unless the user explicitly asks.",
                    ],
                }
                for item in paper_entries
            ],
        },
    )
    write_json(
        type_dossier_tasks_path,
        {
            "schema_version": SCHEMA_VERSION,
            "workflow": WORKFLOW,
            "phase": "type_dossier",
            "course": course_key,
            "exam_scope": scope,
            "status": "blocked-until-cross-paper-synthesis-complete",
            "inputs": [
                relative_posix(taxonomy_path, repo),
                relative_posix(paper_cards_dir, repo),
                relative_posix(output_root / "分析", repo),
                relative_posix(output_root / "试卷精析", repo),
            ],
            "outputs": [
                relative_posix(type_dossiers_dir, repo),
                relative_posix(output_root / "题型备课卡", repo),
            ],
            "instructions": [
                "Create one type-dossier JSON and one readable 题型备课卡 markdown per taxonomy type.",
                "Use only paper-card question refs for worked_example_candidates and self_test_candidates.",
                "Worked examples and self-tests must be disjoint; do not invent simulated questions.",
                "If there are not enough past-paper questions, set quality/needs-review and explain insufficient_evidence_notes.",
            ],
        },
    )
    write_json(
        type_analysis_tasks_path,
        {
            "schema_version": SCHEMA_VERSION,
            "workflow": WORKFLOW,
            "phase": "type_analysis",
            "course": course_key,
            "exam_scope": scope,
            "status": "blocked-until-type-dossier-complete",
            "inputs": [
                relative_posix(type_dossiers_dir, repo),
                relative_posix(output_root / "题型备课卡", repo),
            ],
            "outputs": [relative_posix(output_root / "题型解析", repo)],
            "instructions": [
                "Write type-analysis pages from the matching type dossier, not from a blank template.",
                "Every worked example and self-test must cite a past-paper question ref from the dossier.",
                "Do not reuse the same question ref across examples and self-tests.",
                "Write a tutoring handout: recognition cues, method choice, worked reasoning, scoring, checks, and pitfalls.",
            ],
        },
    )
    if not taxonomy_path.exists() or args.overwrite:
        write_json(
            taxonomy_path,
            {
                "schema_version": SCHEMA_VERSION,
                "workflow": WORKFLOW,
                "course": course_key,
                "exam_scope": scope,
                "types": [],
                "phase": "cross_paper_synthesis",
                "instructions": [
                    "AI clusters types from completed paper-cards; scripts do not keyword-classify question semantics.",
                    "Each type must cite representative paper-card question references.",
                ],
            },
        )
    write_json(
        status_path,
        {
            "schema_version": SCHEMA_VERSION,
            "workflow": WORKFLOW,
            "status": "initialized",
            "current_phase": "paper_deep_dive_v0",
            "phases": PHASES,
            "next_action": "Complete v0 paper deep dives and paper-card JSONs before cross-paper synthesis.",
            "ready_for_stage": {
                "paper-v0": False,
                "synthesis": False,
                "type-dossier": False,
                "final": False,
            },
        },
    )

    _write_if_missing(output_root / "README.md", _readme_text(course_key, scope))
    _write_if_missing(output_root / "试卷精析" / "README.md", _readme_text(course_key, scope))
    _write_if_missing(output_root / "题目卡" / "README.md", _readme_text(course_key, scope))
    _write_if_missing(output_root / "题型备课卡" / "README.md", _readme_text(course_key, scope))
    _write_if_missing(output_root / "题型解析" / "README.md", _readme_text(course_key, scope))
    for filename in CORE_ANALYSIS_FILES:
        _write_if_missing(output_root / "分析" / filename, _analysis_text(filename, course_key, scope))
    for kind, filename in PREP_PACK_FILES.items():
        _write_if_missing(output_root / filename, _initial_pack_text(kind, course_key, scope))

    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "workflow": WORKFLOW,
        "repo": str(repo),
        "course": course_key,
        "exam_scope": scope,
        "papers_dir": relative_posix(papers_dir, repo),
        "paper_count": len(paper_entries),
        "state_dir": str(state),
        "manifest": str(manifest_path),
        "paper_tasks": str(paper_tasks_path),
        "synthesis_tasks": str(synthesis_tasks_path),
        "backfill_tasks": str(backfill_tasks_path),
        "type_dossier_tasks": str(type_dossier_tasks_path),
        "type_analysis_tasks": str(type_analysis_tasks_path),
        "taxonomy": str(taxonomy_path),
        "paper_cards_dir": str(paper_cards_dir),
        "type_dossiers_dir": str(type_dossiers_dir),
        "reviews_dir": str(output_root),
        "created_dirs": [
            str(output_root / "试卷精析"),
            str(output_root / "题目卡"),
            str(output_root / "题型备课卡"),
            str(output_root / "题型解析"),
            str(output_root / "分析"),
        ],
        "next_action": "AI should fill v0 paper deep dives and paper-card JSONs first; after synthesis/backfill, create type dossiers before writing type-analysis pages.",
        "check_argv": [
            "python",
            "student-os/scripts/exam_prep_check.py",
            str(repo),
            "--course",
            args.course,
            "--exam-scope",
            scope,
            "--stage",
            "paper-v0",
            "--json",
        ],
    }


def main() -> int:
    configure_stdout_utf8()
    args = parse_args()
    repo = Path(args.repo).resolve()
    payload = build(repo, args)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Initialized {payload['workflow']} for {payload['course']} {payload['exam_scope']}")
        print(f"Reviews: {payload['reviews_dir']}")
        print(f"State: {payload['state_dir']}")
        print(f"Next: {payload['next_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
