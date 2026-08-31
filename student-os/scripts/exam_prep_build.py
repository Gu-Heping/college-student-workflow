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
STANDARD_FILES = {
    "quality_standard": "quality-standard.md",
    "source_map": "source-map.json",
    "gold_sample_task": "gold-sample-task.json",
}
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
PREP_PACK_SUFFIXES = {
    "guide": "考试备考指南.md",
    "formula_card": "公式总卡.md",
    "answer_templates": "答题模板速查.md",
    "one_hour_checklist": "考前1小时清单.md",
}
SOURCE_ROLE_PRIORITY = {
    "problem": 0,
    "combined": 1,
    "problem_review": 2,
    "answer_review": 3,
    "answer": 4,
    "unknown": 5,
}
ANSWER_ROLE_PRIORITY = {
    "combined": 0,
    "answer_review": 1,
    "answer": 2,
    "problem_review": 3,
    "problem": 4,
    "unknown": 5,
}
PHASES = [
    "source_inventory",
    "quality_standard",
    "gold_sample",
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


def prep_pack_files(exam_scope: str) -> dict[str, str]:
    scope = exam_scope.strip()
    return {key: _prep_title(scope, suffix) for key, suffix in PREP_PACK_SUFFIXES.items()}


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


def _sidecar_stem(path: Path) -> str:
    name = path.name
    return name.removesuffix(".pdf.md").removesuffix(".md")


def _source_role(path: Path) -> str:
    stem = _sidecar_stem(path)
    if "试卷及答案" in stem or "试题及答案" in stem or "试卷答案" in stem:
        return "combined"
    if "答案" in stem and "复习版" in stem:
        return "answer_review"
    if "答案" in stem:
        return "answer"
    if "试卷" in stem and "复习版" in stem:
        return "problem_review"
    if "试卷" in stem or "试题" in stem:
        return "problem"
    return "unknown"


def _canonical_exam_stem(path: Path) -> str:
    stem = _sidecar_stem(path)
    markers = (
        "试卷及答案复习版",
        "试题及答案复习版",
        "试卷答案复习版",
        "试卷及答案",
        "试题及答案",
        "试卷答案",
        "答案复习版",
        "试卷复习版",
        "试题复习版",
        "复习版",
        "答案",
        "试卷",
        "试题",
    )
    for marker in markers:
        stem = stem.replace(marker, "")
    return stem.strip(" _-—·.。")


def _role_sorted(sources: list[dict[str, str]], priorities: dict[str, int]) -> list[dict[str, str]]:
    return sorted(sources, key=lambda item: (priorities.get(item["role"], 99), item["path"]))


def _canonical_exam_entries(repo: Path, papers_dir: Path, papers: list[Path], output_root: Path, state: Path) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for paper in papers:
        group_id = annotation_id(Path(_canonical_exam_stem(paper)), Path("."))
        grouped.setdefault(group_id, []).append(
            {
                "path": relative_posix(paper, repo),
                "role": _source_role(paper),
                "raw_id": annotation_id(paper, papers_dir),
                "display_stem": _canonical_exam_stem(paper),
            }
        )

    entries: list[dict[str, Any]] = []
    for exam_id, sources in sorted(grouped.items()):
        problem_source = _role_sorted(sources, SOURCE_ROLE_PRIORITY)[0]
        answer_source = _role_sorted(sources, ANSWER_ROLE_PRIORITY)[0]
        source_roles: dict[str, list[str]] = {}
        for source in sorted(sources, key=lambda item: item["path"]):
            source_roles.setdefault(source["role"], []).append(source["path"])
        ambiguous = len(sources) > 1 and (
            len(source_roles.get("problem", [])) > 1
            or len(source_roles.get("combined", [])) > 1
            or len(source_roles.get("unknown", [])) > 1
        )
        entries.append(
            {
                "id": exam_id,
                "display_name": problem_source.get("display_stem") or exam_id,
                "path": problem_source["path"],
                "canonical_problem_source": problem_source["path"],
                "canonical_answer_source": answer_source["path"],
                "source_roles": source_roles,
                "all_sources": [source["path"] for source in sorted(sources, key=lambda item: item["path"])],
                "ambiguous_sources": ambiguous,
                "source_count": len(sources),
                "deep_dive": relative_posix(output_root / "试卷精析" / f"{exam_id}.md", repo),
                "readable_card": relative_posix(output_root / "题目卡" / f"{exam_id}.md", repo),
                "paper_card": relative_posix(state / "paper-cards" / f"{exam_id}.json", repo),
            }
        )
    return entries


def _initial_pack_text(kind: str, course: str, exam_scope: str) -> str:
    pack_files = prep_pack_files(exam_scope)
    if kind == "guide":
        return (
            _frontmatter("exam-prep-guide", course, exam_scope)
            + f"# {course} · {exam_scope} · 考试备考指南\n\n"
            "## 怎么使用这套资料\n\n"
            "| 层级 | 文件 | 用途 |\n| --- | --- | --- |\n"
            "| L1 | 本文件 | 复习优先级、时间分配、风险说明 |\n"
            "| L2 | [题型解析/](题型解析/) | 逐题型学习方法与真题例题 |\n"
            f"| L3 | [{pack_files['formula_card']}]({pack_files['formula_card']}) / [{pack_files['answer_templates']}]({pack_files['answer_templates']}) | 背公式与套模板 |\n"
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
        f"| 60-45 分钟 | 看 P0 高频题型 | [{pack_files['guide']}]({pack_files['guide']}) | 明确先后顺序 |\n"
        f"| 45-30 分钟 | 背公式 | [{pack_files['formula_card']}]({pack_files['formula_card']}) | 只背会用的公式 |\n"
        f"| 30-15 分钟 | 背答题模板 | [{pack_files['answer_templates']}]({pack_files['answer_templates']}) | 保步骤分 |\n"
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
        "默认顺序：读取 gold standard → 资料盘点 → 课程质量规范 → 样板页 → reader audit → 逐批扩展 → tripwire 检查。\n\n"
        "脚本只管理任务、路径、证据索引和机械 tripwire；不要把脚本统计、state JSON 或 paper-card 拼成正文。\n\n"
        "正文必须由 AI 亲自打开来源、理解题目、编辑 Markdown、读回自审。宽泛构建请求先做一份试卷精析样板和一份题型解析 gold page。样板没通过 reader audit 前，不要批量铺开整套资料。\n"
    )


def _quality_standard_text(course: str, exam_scope: str) -> str:
    return (
        _frontmatter("exam-prep-quality-standard", course, exam_scope)
        + f"# {course} · {exam_scope} · 质量规范\n\n"
        "## 目标读者\n\n"
        "默认学生没听过课、没做过作业，需要短时间速成。资料必须能直接学习、直接做题、直接复盘。\n\n"
        "## 写作规则\n\n"
        "- 先读课本、讲义、往年卷、答案和已有高质量参考，再写样板。\n"
        "- 不允许只写“参考某资料风格”；必须提炼成本课程可执行规则。\n"
        "- 题型解析必须有完整题目、完整解析、课本依据、真题例题、真题自测和自测答案。\n"
        "- 知识点讲解必须结合课本小节、图号、题图或讲义位置；习题全解只作为答案/解法参考。\n"
        "- 例题负责教方法，自测负责检查同一方法或常见变式；两者不能重复。\n"
        "- 出现在题目、例题、自测中的概念、符号、公式、图形或电路，前文必须先讲清。\n"
        "- 解答使用动作句、算式、短注：先判什么、再列什么、如何代入、如何验算、最后答什么。\n"
        "- 每次交付前必须做 reader audit：亲自抽读入口页、题型页、试卷精析、例题和自测答案，并写出具体修改。\n"
        "- Subagent 可以写正文 draft，但主 agent 必须读回、审稿、局部编辑后才能交付。\n"
        "- 人看的 Markdown 使用 `2018-2019 第二学期 · 一.2` 这类来源标注；`.json#`、paper-card 等机器引用只能留在 state/dossier。\n"
        "- 禁止用批量正则脚本修补题型解析、例题、自测答案、First look、Answer、Check、Transfer 等正文段落。\n"
        "- `issue_count: 0` 只代表 tripwire 通过，不代表资料可读或数学正确。\n"
        "- 参考 `student-os/references/exam-prep-gold-standard.md` 的写作标准；不要复制私人 vault 内容。\n"
        "- 禁止占位话术、口语化废话、自问自答式标题、只给来源不放题目、只给结论不写过程。\n"
        "- Markdown 和 LaTeX 必须能在 Obsidian 中正常阅读。\n\n"
        "## 样板门禁\n\n"
        "先完成一份 `试卷精析` 样板和一份 `题型解析` 样板。样板通过 `exam_prep_check.py --stage gold-sample` 前，不要批量生成整套资料。\n"
    )


def _source_map_payload(
    repo: Path,
    course_dir: Path,
    canonical_exams: list[dict[str, Any]],
    papers_dir: Path,
    course: str,
    exam_scope: str,
) -> dict[str, Any]:
    course_refs = course_dir / "references"
    source_candidates = {
        "textbook_refs": ["课本/", "textbook/", relative_posix(course_refs / "textbooks", repo)],
        "lecture_refs": [relative_posix(course_refs / "lectures", repo), relative_posix(course_dir / "notes", repo)],
        "assignment_refs": [relative_posix(course_dir / "homework", repo), relative_posix(course_refs / "exercises", repo)],
        "paper_refs": [str(item.get("canonical_problem_source") or "") for item in canonical_exams],
        "answer_refs": [str(item.get("canonical_answer_source") or "") for item in canonical_exams if item.get("canonical_answer_source")],
        "canonical_exams": [
            {
                "exam_id": item.get("id"),
                "display_name": item.get("display_name"),
                "source_roles": item.get("source_roles"),
                "canonical_problem_source": item.get("canonical_problem_source"),
                "canonical_answer_source": item.get("canonical_answer_source"),
                "ambiguous_sources": item.get("ambiguous_sources"),
            }
            for item in canonical_exams
        ],
        "high_quality_examples": [
            "If available, inspect an existing high-quality prep pack in this vault and extract concrete writing rules before drafting.",
        ],
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "workflow": WORKFLOW,
        "course": course,
        "exam_scope": exam_scope,
        "papers_dir": relative_posix(papers_dir, repo),
        "source_priority": [
            "course textbook/lecture notes for concepts and symbols",
            "past papers for examples and self-tests",
            "answer keys/solution books for checking solutions only",
            "homework/typical problems for supplementary coverage",
        ],
        **source_candidates,
        "rules": [
            "Do not treat answer-key text as textbook grounding.",
            "Prefer original past-paper problems over variants.",
            "Mark source gaps as needs-review instead of inventing content.",
        ],
    }


def _gold_sample_task_payload(repo: Path, output_root: Path, state: Path, course: str, exam_scope: str, paper_entries: list[dict[str, Any]]) -> dict[str, Any]:
    first_paper = paper_entries[0] if paper_entries else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "workflow": WORKFLOW,
        "phase": "gold_sample",
        "course": course,
        "exam_scope": exam_scope,
        "status": "pending-ai-sample",
        "inputs": [
            relative_posix(output_root / STANDARD_FILES["quality_standard"], repo),
            relative_posix(state / STANDARD_FILES["source_map"], repo),
            str(first_paper.get("path") or ""),
        ],
        "outputs": [
            str(first_paper.get("deep_dive") or relative_posix(output_root / "试卷精析", repo)),
            relative_posix(output_root / "题型解析", repo),
        ],
        "instructions": [
            "Before bulk generation, write one representative paper deep-dive sample and one representative type-analysis sample.",
            "The sample type-analysis must include a full past-paper problem, textbook-grounded concept explanation, full solution, self-test, answer, human-readable source citations, and readable short blocks.",
            "Run exam_prep_check.py --stage gold-sample --json. Do not expand to the full pack until the sample passes.",
        ],
        "bulk_generation_locked_until": "gold-sample-pass",
    }


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
    source_map_path = state / STANDARD_FILES["source_map"]
    gold_sample_task_path = state / STANDARD_FILES["gold_sample_task"]
    quality_standard_path = output_root / STANDARD_FILES["quality_standard"]
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
    paper_entries = _canonical_exam_entries(repo, papers_dir, papers, output_root, state)
    for item in paper_entries:
        tasks.append(
            {
                "id": item["id"],
                "status": "pending-ai-analysis",
                "display_name": item["display_name"],
                "source": item["canonical_problem_source"],
                "source_roles": item["source_roles"],
                "canonical_problem_source": item["canonical_problem_source"],
                "canonical_answer_source": item["canonical_answer_source"],
                "write_deep_dive": item["deep_dive"],
                "write_readable_card": item["readable_card"],
                "write_paper_card": item["paper_card"],
                "instructions": [
                    "Read the canonical problem source and answer/source evidence listed in source_roles; do not create separate deep dives for duplicate sidecars from the same exam.",
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
        "raw_source_count": len(papers),
        "canonical_exam_count": len(paper_entries),
        "paper_count": len(paper_entries),
        "papers": paper_entries,
        "agent_contract": {
            "semantic_owner": "ai-agent",
            "script_role": "workspace-initialization-state-and-tripwire-only",
            "content_authoring_rule": "AI must personally read sources and edit Markdown body text; scripts must not generate lecture prose, worked solutions, self-test answers, or guide content.",
            "subagent_rule": "Subagents may draft body text only from explicit contracts; the main agent must read back, review, and locally edit drafts before delivery.",
            "citation_rule": "Machine refs such as paper-card JSON anchors stay in state/dossiers. Human-facing Markdown uses readable sources such as 2018-2019 第二学期 · 一.2.",
            "canonical_exam_rule": "Group duplicate sidecars for the same exam into one canonical paper task with source roles before writing deep dives.",
            "body_patch_rule": "Do not use batch regex scripts to patch teaching prose, worked examples, answers, First look, Check, or Transfer sections; open the page and edit the local prose.",
            "default_order": [
                "read_exam_prep_gold_standard",
                "source_inventory",
                "canonical_exam_manifest",
                "quality_standard",
                "gold_sample",
                "reader_audit",
                "paper_deep_dive_v0",
                "paper_card",
                "cross_paper_synthesis",
                "paper_deep_dive_v1_backfill",
                "type_dossier",
                "type_analysis",
                "prep_pack",
                "tripwire_check",
                "reader_audit",
            ],
            "repeat_analysis_rule": "Original-repeat, close-variant, same-type, and trends are written after cross-paper synthesis, then backfilled into paper deep dives.",
            "bulk_generation_rule": "Do not generate the full pack before one paper-deep-dive sample and one type-analysis gold page pass tripwire checks and reader audit.",
            "delivery_rule": "Do not report completed from issue_count:0. Final delivery requires a concrete reader audit describing sampled files, blockers, edits, and remaining risks.",
            "target_reader": "Student may have skipped lectures and homework; write for short-term exam catch-up.",
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
            "status": "blocked-until-gold-sample-pass",
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
            "status": "blocked-until-gold-sample-and-paper-v0-complete",
            "inputs": [
                relative_posix(quality_standard_path, repo),
                relative_posix(source_map_path, repo),
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
                    "Every cross-paper conclusion must cite human-readable year/term/question sources in Markdown and paper-card question refs in state JSON.",
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
                "Include type links, repeat/variant status, related years/questions, review priority, and human-readable sources.",
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
                relative_posix(quality_standard_path, repo),
                relative_posix(source_map_path, repo),
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
                "Human-facing 题型备课卡 may summarize sources readably, but machine question refs stay in dossier JSON.",
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
            "status": "blocked-until-type-dossier-and-gold-sample-complete",
            "inputs": [
                relative_posix(quality_standard_path, repo),
                relative_posix(type_dossiers_dir, repo),
                relative_posix(output_root / "题型备课卡", repo),
            ],
            "outputs": [relative_posix(output_root / "题型解析", repo)],
            "instructions": [
                "Write type-analysis pages from the matching type dossier, not from a blank template.",
                "Follow the passed gold sample. Do not bulk-fill pages with generic placeholders.",
                "Every worked example and self-test must use a past-paper question from the dossier, but cite it in human-facing form, not as .json#.",
                "Do not reuse the same question ref across examples and self-tests.",
                "Write a tutoring handout: recognition cues, method choice, worked reasoning, scoring, checks, and pitfalls.",
                "Subagent drafts are allowed only as drafts; the main agent must read them back and edit weak prose before marking the page done.",
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
                "Each type must cite representative paper-card question references in JSON; Markdown reports must use human-readable citations.",
                ],
            },
        )
    write_json(
        status_path,
        {
            "schema_version": SCHEMA_VERSION,
            "workflow": WORKFLOW,
            "status": "initialized",
            "current_phase": "source_inventory",
            "phases": PHASES,
            "next_action": "Create the quality standard, source map, and one gold sample before bulk paper/type generation.",
            "ready_for_stage": {
                "standard": False,
                "source-map": False,
                "gold-sample": False,
                "paper-v0": False,
                "synthesis": False,
                "type-dossier": False,
                "type-analysis-sample": False,
                "final": False,
            },
        },
    )

    _write_if_missing(output_root / "README.md", _readme_text(course_key, scope))
    _write_if_missing(quality_standard_path, _quality_standard_text(course_key, scope))
    if not source_map_path.exists() or args.overwrite:
        write_json(source_map_path, _source_map_payload(repo, course_dir, paper_entries, papers_dir, course_key, scope))
    if not gold_sample_task_path.exists() or args.overwrite:
        write_json(gold_sample_task_path, _gold_sample_task_payload(repo, output_root, state, course_key, scope, paper_entries))
    _write_if_missing(output_root / "试卷精析" / "README.md", _readme_text(course_key, scope))
    _write_if_missing(output_root / "题目卡" / "README.md", _readme_text(course_key, scope))
    _write_if_missing(output_root / "题型备课卡" / "README.md", _readme_text(course_key, scope))
    _write_if_missing(output_root / "题型解析" / "README.md", _readme_text(course_key, scope))
    for filename in CORE_ANALYSIS_FILES:
        _write_if_missing(output_root / "分析" / filename, _analysis_text(filename, course_key, scope))
    for kind, filename in prep_pack_files(scope).items():
        _write_if_missing(output_root / filename, _initial_pack_text(kind, course_key, scope))

    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "workflow": WORKFLOW,
        "repo": str(repo),
        "course": course_key,
        "exam_scope": scope,
        "papers_dir": relative_posix(papers_dir, repo),
        "raw_source_count": len(papers),
        "canonical_exam_count": len(paper_entries),
        "paper_count": len(paper_entries),
        "state_dir": str(state),
        "manifest": str(manifest_path),
        "paper_tasks": str(paper_tasks_path),
        "synthesis_tasks": str(synthesis_tasks_path),
        "backfill_tasks": str(backfill_tasks_path),
        "type_dossier_tasks": str(type_dossier_tasks_path),
        "type_analysis_tasks": str(type_analysis_tasks_path),
        "quality_standard": str(quality_standard_path),
        "source_map": str(source_map_path),
        "gold_sample_task": str(gold_sample_task_path),
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
        "next_action": "AI should read student-os/references/exam-prep-gold-standard.md, write one gold sample by hand from real sources, run gold-sample tripwire, then perform reader audit before expanding.",
        "check_argv": [
            "python",
            "student-os/scripts/exam_prep_check.py",
            str(repo),
            "--course",
            args.course,
            "--exam-scope",
            scope,
            "--stage",
            "gold-sample",
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
