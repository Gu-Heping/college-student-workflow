#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from course_layout import configure_stdout_utf8
from exam_census_utils import (
    course_slug_of,
    exam_scope_key,
    load_json,
    markdown_table_pipe_issues,
    relative_posix,
    resolve_course,
    reviews_dir,
    write_json,
)
from exam_prep_build import CORE_ANALYSIS_FILES, PREP_PACK_FILES, SCHEMA_VERSION, STANDARD_FILES, WORKFLOW, exam_prep_state_dir
from import_governance import diagnose_import_risks


REQUIRED_TYPE_BLOCKS = (
    "考前速记",
    "符号",
    "核心概念",
    "核心方法",
    "例题",
    "自测",
    "快速得分",
    "易错",
    "来源",
)
REQUIRED_DOSSIER_FIELDS = (
    "type_id",
    "type_name",
    "confidence",
    "source_question_refs",
    "recognition_cues",
    "common_variants",
    "method_cards",
    "formula_cards",
    "pitfalls",
    "worked_example_candidates",
    "self_test_candidates",
    "insufficient_evidence_notes",
)
SOURCE_RE = re.compile(r"来源\s*[：:]")
PLACEHOLDER_RE = re.compile(r"\{\{[^}]+\}\}|TODO|TBD|待 AI|待整理|^\|\s*\|\s*\|", re.I | re.M)
LOW_QUALITY_PHRASE_RE = re.compile(
    r"答案以.*为准|调用对应方法卡|矩阵或公式|先圈出对象|不要急着代数展开|自测答案?以.*来源|同型变式通常只换|详见来源|见原题答案|复核时对照\s*paper-card|题目较长.*关键条件",
    re.I,
)
UNIVERSAL_SOLUTION_RE = re.compile(
    r"看到题干后先判入口|根据关键词确定本题属于本题型|使用本页核心方法中最匹配的一条|把题目给出的矩阵、向量或参数代入|按本页模板核算|同卷答案区核算",
    re.I,
)
GENERIC_SELF_TEST_ANSWER_RE = re.compile(
    r"答案\s*[：:].{0,80}(?:按本页模板|同卷答案区|核算最终数值|以来源为准|对照\s*paper-card|自行计算)",
    re.I | re.S,
)
HEADING_ONLY_PROBLEM_RE = re.compile(
    r"(?:\*\*)?题目(?:\*\*)?\s*[：:]\s*(?:\n\s*){0,2}#{1,6}\s*[一二三四五六七八九十\d]+[.、．][^\n]{0,40}(?:题|分|共|简答|计算)",
    re.I,
)
RAW_OCR_DUMP_LINE_RE = re.compile(r"(?:\*\*)?题目(?:\*\*)?\s*[：:].{240,}(?:解\s*[：:：]|答案\s*[：:：]|\\\\begin\{array\})")
GUIDE_ROUTE_MARKERS = ("我现在", "先读", "先看", "1 小时", "1天", "1 天", "3天", "3 天", "P0", "P1")
SELF_QUESTION_TITLE_RE = re.compile(r"^#{1,6}\s*\d+(?:\.\d+)*\s*为什么", re.M)
TEXTBOOK_GROUNDING_RE = re.compile(r"(?:课本|教材|讲义).{0,24}(?:§\s*\d+(?:\.\d+)+|图\s*\d+(?:\.\d+)+|题图\s*\d+(?:\.\d+)+|第\s*\d+\s*章)")
OVERBROAD_SECTION_RE = re.compile(r"(?:课本|教材|讲义).{0,16}§\s*\d+(?:\.\d+)?(?:\s|[，,、。；;]|$)")
FULL_PROBLEM_RE = re.compile(r"(?:\*\*)?题目(?:\*\*)?\s*[：:]")
WEAK_PROBLEM_RE = re.compile(r"题目摘录\s*[：:]|题目摘要\s*[：:]|题目\s*[：:].{0,30}(?:往年题|自测)\s*\d+")
SOLUTION_STEP_RE = re.compile(r"(?:完整解析|解析|第\s*\d+\s*步|先判|再写|代入|验算|检查)")
ANSWER_RE = re.compile(r"(?:自测.*答案|(?:\*\*)?答案(?:\*\*)?\s*[：:])", re.M)
QUESTION_REF_RE = re.compile(r"(?:第?\s*[一二三四五六七八九十\d]+\s*题|Q\d+|一、|二、|三、|四、|五、|六、|七、)")
QUESTION_REF_TOKEN_RE = re.compile(r"[\w.-]+\.json#[^\s,，;；)）\]}】、。]+")
FABRICATED_QUESTION_RE = re.compile(r"(自编题|模拟题|改编题|原创题)")
STANDARD_REQUIRED_MARKERS = (
    "目标读者",
    "没听过课",
    "没做过作业",
    "短时间速成",
    "完整题目",
    "完整解析",
    "课本",
    "往年卷",
    "例题",
    "自测",
    "样板",
)
CONFIDENCE_ALLOWED = {"high", "medium", "low", "uncertain", "needs-review"}
REPEAT_STATUS_ALLOWED = {
    "unknown-pending-cross-paper-analysis",
    "original-repeat",
    "close-variant",
    "same-type",
    "unique",
    "needs-review",
}
V0_REPEAT_STATUS_ALLOWED = {"unknown-pending-cross-paper-analysis", "needs-review"}
CROSS_PAPER_MARKERS = ("跨卷关系", "原题复现", "同型变式", "相似题", "复习优先级")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tripwire-only mechanical check for AI-written exam prep artifacts."
    )
    parser.add_argument("repo", help="Target learning vault root")
    parser.add_argument("--course", required=True, help="Course slug or path under courses/")
    parser.add_argument("--exam-scope", required=True, help="Exam scope label such as 期中 or 期末")
    parser.add_argument("--semester", default="", help="Optional semester slug when resolving course")
    parser.add_argument(
        "--stage",
        choices=("standard", "source-map", "gold-sample", "paper-v0", "synthesis", "type-dossier", "type-analysis-sample", "final"),
        default="final",
        help="Validation stage: standard, source-map, gold-sample, paper-v0, synthesis, type-dossier, type-analysis-sample, or final.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable result")
    parser.add_argument("--write-report", action="store_true", help="Write quality-report.json to state")
    return parser.parse_args()


def _issue(code: str, path: Path | str, message: str, *, severity: str = "error") -> dict[str, str]:
    return {"severity": severity, "code": code, "path": str(path), "message": message}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter_type(text: str) -> str:
    match = re.search(r"(?m)^type:\s*(.+)$", text)
    if not match:
        return ""
    return match.group(1).strip().strip('"\'')


def _has_heading(text: str, title: str) -> bool:
    return bool(re.search(rf"(?m)^#{{1,6}}\s+.*{re.escape(title)}", text))


def _has_inline_math_delimiter_space(text: str) -> bool:
    for line in text.splitlines():
        index = 0
        while index < len(line):
            start = line.find("$", index)
            if start == -1:
                break
            if (start > 0 and line[start - 1] == "\\") or line[start : start + 2] == "$$":
                index = start + 1
                continue
            end = start + 1
            while True:
                end = line.find("$", end)
                if end == -1:
                    return False
                if (end > 0 and line[end - 1] == "\\") or line[end : end + 2] == "$$":
                    end += 1
                    continue
                body = line[start + 1 : end]
                if body and (body[0].isspace() or body[-1].isspace()):
                    return True
                index = end + 1
                break
    return False


def _nonempty_md_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(item for item in path.glob("*.md") if item.name != "README.md" and item.is_file())


def _validate_paper_card(card_path: Path, manifest_sources: set[str], *, stage: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    try:
        card = load_json(card_path)
    except Exception as exc:
        return [_issue("paper-card-invalid-json", card_path, f"Cannot read paper-card JSON: {exc}")]
    if not isinstance(card, dict):
        return [_issue("paper-card-not-object", card_path, "paper-card must be a JSON object")]

    source = str(card.get("source") or "").replace("\\", "/")
    if not source:
        issues.append(_issue("paper-card-missing-source", card_path, "paper-card must record source"))
    elif source not in manifest_sources:
        issues.append(
            _issue(
                "paper-card-source-not-in-manifest",
                card_path,
                "paper-card source must match one manifest paper path",
            )
        )

    confidence = str(card.get("confidence") or "").strip()
    if confidence not in CONFIDENCE_ALLOWED:
        issues.append(
            _issue(
                "paper-card-invalid-confidence",
                card_path,
                "confidence must be high|medium|low|uncertain|needs-review",
            )
        )

    questions = card.get("questions")
    if not isinstance(questions, list) or not questions:
        issues.append(_issue("paper-card-missing-questions", card_path, "paper-card must contain questions[]"))
        return issues
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            issues.append(_issue("paper-card-question-not-object", card_path, f"questions[{index}] must be an object"))
            continue
        if not str(question.get("question_id") or question.get("id") or "").strip():
            issues.append(_issue("paper-card-question-missing-id", card_path, f"questions[{index}] missing question_id"))
        if not str(question.get("prompt_summary") or "").strip():
            issues.append(_issue("paper-card-question-missing-prompt-summary", card_path, f"questions[{index}] missing prompt_summary"))
        if not str(question.get("solution_summary") or "").strip():
            issues.append(_issue("paper-card-question-missing-solution-summary", card_path, f"questions[{index}] missing solution_summary"))
        if not str(question.get("initial_type") or question.get("type") or "").strip():
            issues.append(_issue("paper-card-question-missing-initial-type", card_path, f"questions[{index}] missing initial_type"))
        evidence_refs = question.get("evidence_refs") or question.get("evidence")
        if not evidence_refs:
            issues.append(_issue("paper-card-question-missing-evidence", card_path, f"questions[{index}] missing evidence_refs"))
        repeat_status = str(question.get("repeat_status") or "").strip()
        if repeat_status not in REPEAT_STATUS_ALLOWED:
            issues.append(
                _issue(
                    "paper-card-invalid-repeat-status",
                    card_path,
                    f"questions[{index}] repeat_status must be one of {', '.join(sorted(REPEAT_STATUS_ALLOWED))}",
                )
            )
        elif stage == "paper-v0" and repeat_status not in V0_REPEAT_STATUS_ALLOWED:
            issues.append(
                _issue(
                    "paper-card-premature-repeat-claim",
                    card_path,
                    "paper-v0 may only use unknown-pending-cross-paper-analysis or needs-review for repeat_status",
                )
            )
    return issues


def _validate_markdown(path: Path, *, required_type: str | None = None) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not path.exists():
        return [_issue("missing-file", path, "Required exam-prep artifact is missing")]
    text = _read(path)
    if required_type and _frontmatter_type(text) != required_type:
        issues.append(_issue("frontmatter-type", path, f"Expected frontmatter type {required_type!r}"))
    if PLACEHOLDER_RE.search(text):
        issues.append(_issue("placeholder-content", path, "File still contains placeholder or AI task text"))
    if markdown_table_pipe_issues(text):
        issues.append(_issue("markdown-table", path, "Markdown table columns appear broken"))
    for line in text.splitlines():
        stripped = line.strip()
        if "$$" not in stripped:
            continue
        if stripped != "$$" and (stripped.startswith("$$") or stripped.endswith("$$") or "$$" in stripped):
            issues.append(_issue("render-risk", path, "Display math delimiter $$ must be alone on its own line"))
            break
    if _has_inline_math_delimiter_space(text):
        issues.append(_issue("render-risk", path, "Inline math delimiters must be tight, e.g. $x$, not $ x $"))
    risks = diagnose_import_risks(text)
    blocking = [risk for risk in risks if str(risk.get("severity")) == "error"]
    if blocking:
        codes = ", ".join(sorted({str(risk.get("code")) for risk in blocking}))
        issues.append(_issue("render-risk", path, f"Obsidian/Markdown render risks: {codes}"))
    return issues


def _validate_quality_standard(path: Path) -> list[dict[str, str]]:
    issues = _validate_markdown(path, required_type="exam-prep-quality-standard")
    if not path.exists():
        return issues
    text = _read(path)
    for marker in STANDARD_REQUIRED_MARKERS:
        if marker not in text:
            issues.append(_issue("quality-standard-missing-rule", path, f"Quality standard must mention {marker!r}"))
    return issues


def _validate_source_map(path: Path, manifest_sources: set[str]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not path.exists():
        return [_issue("missing-source-map", path, "source-map.json is missing")]
    try:
        source_map = load_json(path)
    except Exception as exc:
        return [_issue("source-map-invalid-json", path, f"Cannot read source-map JSON: {exc}")]
    if not isinstance(source_map, dict):
        return [_issue("source-map-not-object", path, "source-map must be a JSON object")]
    if source_map.get("workflow") != WORKFLOW:
        issues.append(_issue("source-map-workflow", path, f"source-map workflow must be {WORKFLOW}"))
    for field in ("source_priority", "textbook_refs", "lecture_refs", "assignment_refs", "paper_refs", "answer_refs", "high_quality_examples"):
        if field not in source_map:
            issues.append(_issue("source-map-missing-field", path, f"source-map missing {field}"))
    paper_refs = {str(item).replace("\\", "/") for item in source_map.get("paper_refs") or []}
    if manifest_sources and not manifest_sources <= paper_refs:
        issues.append(_issue("source-map-missing-paper-ref", path, "source-map paper_refs must include all manifest paper paths"))
    if not any(str(item).strip() for item in source_map.get("textbook_refs") or []):
        issues.append(
            _issue(
                "source-map-empty-textbook-refs",
                path,
                "Textbook/lecture grounding sources should be recorded; mark gaps explicitly if unavailable",
                severity="warning",
            )
        )
    return issues


def _validate_type_analysis_learning_quality(path: Path, refs_by_type: dict[str, set[str]], *, strict_refs: bool) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not path.exists():
        return [_issue("missing-type-analysis-sample", path, "Gold sample needs at least one type-analysis page")]
    text = _read(path)
    if LOW_QUALITY_PHRASE_RE.search(text):
        issues.append(_issue("type-analysis-low-quality-phrase", path, "Type analysis contains placeholder or non-teaching phrases"))
    if SELF_QUESTION_TITLE_RE.search(text):
        issues.append(_issue("type-analysis-self-question-heading", path, "Avoid self-Q&A headings; write direct teaching sections"))
    if not TEXTBOOK_GROUNDING_RE.search(text):
        issues.append(
            _issue(
                "type-analysis-missing-textbook-grounding",
                path,
                "Concept explanations must cite a precise textbook/lecture section, figure, problem diagram, or chapter anchor",
            )
        )
    if OVERBROAD_SECTION_RE.search(text) and not TEXTBOOK_GROUNDING_RE.search(text):
        issues.append(_issue("type-analysis-overbroad-textbook-ref", path, "Textbook grounding is too broad; cite a precise subsection, figure, or problem diagram"))
    if "2 分钟" not in text and "下笔模板" not in text:
        issues.append(_issue("type-analysis-missing-action-template", path, "Type analysis must include a 2-minute writing/action template"))
    examples_text = _section_text(text, "例题", stop_titles=("自测题", "自测答案", "快速得分", "易错点", "来源校对"))
    self_test_text = _section_text(text, "自测题", stop_titles=("自测答案", "快速得分", "易错点", "来源校对"))
    answers_text = _section_text(text, "自测答案", stop_titles=("快速得分", "易错点", "来源校对"))
    if UNIVERSAL_SOLUTION_RE.search(examples_text):
        issues.append(
            _issue(
                "type-analysis-template-worked-solution",
                path,
                "Worked examples use generic reusable prose instead of responding to the exact problem",
            )
        )
    if GENERIC_SELF_TEST_ANSWER_RE.search(answers_text):
        issues.append(
            _issue(
                "type-analysis-template-self-test-answer",
                path,
                "Self-test answers must give concrete results or key steps, not generic template instructions",
            )
        )
        if len(GENERIC_SELF_TEST_ANSWER_RE.findall(answers_text)) > 1 or answers_text.count("按本页模板") > 1:
            issues.append(
                _issue(
                    "type-analysis-repeated-self-test-answer",
                    path,
                    "Multiple self-test answers reuse generic template instructions instead of concrete answers",
                )
            )
    if HEADING_ONLY_PROBLEM_RE.search(examples_text) or HEADING_ONLY_PROBLEM_RE.search(self_test_text):
        issues.append(
            _issue(
                "type-analysis-heading-only-problem",
                path,
                "Problem statements cannot be only a promoted heading or broad paper section title",
            )
        )
    if any(RAW_OCR_DUMP_LINE_RE.search(line) for line in examples_text.splitlines() + self_test_text.splitlines()):
        issues.append(
            _issue(
                "type-analysis-raw-ocr-dump",
                path,
                "Problem text appears to paste raw OCR with solution/answer glued in; rewrite it into a usable stem",
            )
        )
    solution_blocks = _normalized_blocks(
        re.compile(r"完整解析\s*[：:]\s*(.+?)(?=\n\s*(?:验算|举一反三|易错|###|##)|\Z)", re.S),
        examples_text,
    )
    answer_blocks = _normalized_blocks(
        re.compile(r"答案\s*[：:]\s*(.+?)(?=\n\s*(?:###|##)|\Z)", re.S),
        answers_text,
    )
    if _duplicate_blocks(solution_blocks):
        issues.append(
            _issue(
                "type-analysis-repeated-worked-solution",
                path,
                "Multiple worked examples reuse the same explanation block; each example needs problem-specific reasoning",
            )
        )
    if _duplicate_blocks(answer_blocks):
        issues.append(
            _issue(
                "type-analysis-repeated-self-test-answer",
                path,
                "Multiple self-test answers reuse the same answer block; each self-test needs its own concrete answer",
            )
        )
    if not FULL_PROBLEM_RE.search(examples_text) or WEAK_PROBLEM_RE.search(examples_text):
        issues.append(_issue("type-analysis-missing-full-worked-problem", path, "Worked examples must include full past-paper problem statements, not only source links or summaries"))
    if not FULL_PROBLEM_RE.search(self_test_text) or WEAK_PROBLEM_RE.search(self_test_text):
        issues.append(_issue("type-analysis-missing-full-self-test-problem", path, "Self-tests must include full past-paper problem statements, not only source links or summaries"))
    if not SOLUTION_STEP_RE.search(examples_text):
        issues.append(_issue("type-analysis-missing-full-solution", path, "Worked examples need full reasoning steps, not only final answers"))
    if not ANSWER_RE.search(answers_text):
        issues.append(_issue("type-analysis-missing-self-test-answer-content", path, "Self-tests need an answer section with concrete answers"))
    if "动作" not in text and "先判" not in text and "再列" not in text:
        issues.append(_issue("type-analysis-missing-action-sentence-style", path, "Solutions should use action sentence + formula + short note style"))
    if strict_refs:
        issues.extend(_validate_type_analysis(path, refs_by_type))
    return issues


def _validate_gold_sample(output_root: Path, refs_by_type: dict[str, set[str]]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    deep_dive_files = _nonempty_md_files(output_root / "试卷精析")
    type_files = _nonempty_md_files(output_root / "题型解析")
    if not deep_dive_files:
        issues.append(_issue("gold-sample-missing-paper-deep-dive", output_root / "试卷精析", "Create one representative paper deep-dive sample before bulk generation"))
    else:
        issues.extend(_validate_markdown(deep_dive_files[0], required_type="exam-paper-deep-dive"))
        text = _read(deep_dive_files[0])
        for marker in ("题号", "来源", "考点", "解法", "疑点"):
            if marker not in text:
                issues.append(_issue("gold-sample-paper-too-thin", deep_dive_files[0], f"Paper sample should include {marker}"))
    if not type_files:
        issues.append(_issue("gold-sample-missing-type-analysis", output_root / "题型解析", "Create one representative type-analysis sample before bulk generation"))
    else:
        issues.extend(_validate_markdown(type_files[0], required_type="exam-type-analysis"))
        issues.extend(_validate_type_analysis_learning_quality(type_files[0], refs_by_type, strict_refs=bool(refs_by_type)))
    return issues


def _validate_type_analysis(path: Path, refs_by_type: dict[str, set[str]]) -> list[dict[str, str]]:
    issues = _validate_markdown(path)
    text = _read(path) if path.exists() else ""
    type_id = _extract_frontmatter_field(text, "exam_type_id")
    quality = _extract_frontmatter_field(text, "quality")
    for marker in REQUIRED_TYPE_BLOCKS:
        if marker not in text:
            issues.append(_issue("type-analysis-missing-block", path, f"Missing teaching block containing {marker!r}"))
    if not SOURCE_RE.search(text) or not (QUESTION_REF_RE.search(text) or QUESTION_REF_TOKEN_RE.search(text)):
        issues.append(
            _issue(
                "type-analysis-missing-source-question",
                path,
                "Type analysis must cite real paper/question sources",
            )
        )
    if FABRICATED_QUESTION_RE.search(text):
        issues.append(_issue("type-analysis-fabricated-question", path, "Examples and self-tests must come from past papers, not fabricated/simulated questions"))
    if not type_id:
        issues.append(_issue("type-analysis-missing-type-id", path, "Frontmatter must contain exam_type_id matching a type dossier"))
        return issues
    allowed_refs = refs_by_type.get(type_id)
    if not allowed_refs:
        issues.append(_issue("type-analysis-missing-dossier", path, f"No type dossier refs found for exam_type_id {type_id!r}"))
        return issues

    refs = _extract_question_refs(text)
    if not refs:
        issues.append(_issue("type-analysis-missing-question-ref", path, "Use machine-readable paper-card refs such as 2024-final.json#一"))
    for ref in sorted(refs):
        if ref not in allowed_refs:
            issues.append(_issue("type-analysis-ref-not-in-dossier", path, f"Question ref is not in the matching type dossier: {ref}"))

    examples_text = _section_text(text, "例题", stop_titles=("自测题", "自测答案", "快速得分", "易错点", "来源校对"))
    self_test_text = _section_text(text, "自测题", stop_titles=("自测答案", "快速得分", "易错点", "来源校对"))
    answers_text = _section_text(text, "自测答案", stop_titles=("快速得分", "易错点", "来源校对"))
    example_refs = _extract_question_refs_list(examples_text)
    self_refs = _extract_question_refs_list(self_test_text)
    if not example_refs:
        issues.append(_issue("type-analysis-missing-worked-example-ref", path, "Worked examples must cite dossier-backed past-paper refs"))
    if not self_refs:
        issues.append(_issue("type-analysis-missing-self-test-ref", path, "Self-tests must cite dossier-backed past-paper refs"))
    if len(set(example_refs)) != len(example_refs):
        issues.append(_issue("type-analysis-duplicate-worked-example", path, "Worked examples repeat the same question ref"))
    if len(set(self_refs)) != len(self_refs):
        issues.append(_issue("type-analysis-duplicate-self-test", path, "Self-tests repeat the same question ref"))
    overlap = set(example_refs) & set(self_refs)
    if overlap:
        issues.append(
            _issue(
                "type-analysis-example-selftest-overlap",
                path,
                "The same past-paper question cannot be both worked example and self-test: " + ", ".join(sorted(overlap)),
            )
        )

    insufficient = quality == "needs-review" or _has_insufficient_evidence_note(text)
    if len(set(example_refs)) < 5 and not insufficient:
        issues.append(_issue("type-analysis-too-few-worked-examples", path, "Default quality target is at least 5 past-paper worked examples, unless evidence is insufficient"))
    if len(set(self_refs)) < 4 and not insufficient:
        issues.append(_issue("type-analysis-too-few-self-tests", path, "Default quality target is at least 4 past-paper self-tests, unless evidence is insufficient"))
    for marker in ("频率", "代表年份", "复习优先级"):
        if marker not in text:
            issues.append(_issue("type-analysis-missing-cross-paper-value", path, f"Opening section should mention {marker}"))
    if "原题复现" not in text and "同型变式" not in text:
        issues.append(_issue("type-analysis-missing-cross-paper-value", path, "Opening section should mention original repeats or same-type variants"))
    for marker in ("看到", "方法引用", "验算", "易错"):
        if marker not in examples_text:
            issues.append(_issue("type-analysis-worked-example-too-thin", path, f"Worked examples should include {marker} guidance"))
    if "变式" not in examples_text and "举一反三" not in examples_text and "训练目标" not in examples_text:
        issues.append(
            _issue(
                "type-analysis-worked-example-missing-transfer",
                path,
                "Worked examples should label the method/variant training target; AI judges whether the transfer quality is good",
                severity="warning",
            )
        )
    if "提示" not in self_test_text:
        issues.append(_issue("type-analysis-self-test-missing-hint", path, "Self-tests should include hints"))
    if "方法" not in self_test_text and "变式" not in self_test_text and "训练目标" not in self_test_text:
        issues.append(
            _issue(
                "type-analysis-self-test-missing-method-link",
                path,
                "Self-tests should label the method/variant training target; AI judges whether coverage is complete",
                severity="warning",
            )
        )
    if not answers_text:
        issues.append(_issue("type-analysis-missing-self-test-answers", path, "Self-test answers must be separated from self-test prompts"))
    issues.extend(_validate_type_analysis_learning_quality(path, refs_by_type, strict_refs=False))
    return issues


def _validate_taxonomy(taxonomy_path: Path, card_paths: list[Path]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not taxonomy_path.exists():
        return [_issue("missing-taxonomy", taxonomy_path, "taxonomy.json is missing")]
    taxonomy = load_json(taxonomy_path)
    if not isinstance(taxonomy, dict):
        return [_issue("taxonomy-not-object", taxonomy_path, "taxonomy.json must be an object")]
    if taxonomy.get("workflow") != WORKFLOW:
        issues.append(_issue("taxonomy-workflow", taxonomy_path, f"taxonomy workflow must be {WORKFLOW}"))
    types = taxonomy.get("types")
    if not isinstance(types, list) or not types:
        issues.append(_issue("taxonomy-empty", taxonomy_path, "AI must cluster paper-cards into at least one type"))
        return issues
    card_names = {path.name for path in card_paths}
    for index, item in enumerate(types, start=1):
        if not isinstance(item, dict):
            issues.append(_issue("taxonomy-type-not-object", taxonomy_path, f"types[{index}] must be an object"))
            continue
        for field in ("id", "name", "confidence"):
            if not str(item.get(field) or "").strip():
                issues.append(_issue("taxonomy-type-missing-field", taxonomy_path, f"types[{index}] missing {field}"))
        refs = item.get("source_refs") or item.get("representative_questions")
        if not refs:
            issues.append(
                _issue("taxonomy-type-missing-source-refs", taxonomy_path, f"types[{index}] must cite paper-card questions")
            )
            continue
        refs_text = json.dumps(refs, ensure_ascii=False)
        if card_names and not any(name in refs_text for name in card_names):
            issues.append(
                _issue(
                    "taxonomy-type-source-not-card",
                    taxonomy_path,
                    f"types[{index}] source_refs must mention a paper-card file",
                )
            )
    return issues


def _validate_manifest_paper_outputs(
    manifest: dict[str, Any],
    repo: Path,
    state: Path,
    output_root: Path,
    *,
    stage: str,
) -> tuple[list[dict[str, str]], list[Path]]:
    issues: list[dict[str, str]] = []
    card_paths: list[Path] = []
    papers = [item for item in manifest.get("papers", []) if isinstance(item, dict)]
    for item in papers:
        paper_id = str(item.get("id") or "").strip()
        card_rel = str(item.get("paper_card") or "")
        dive_rel = str(item.get("deep_dive") or "")
        card_path = (repo / card_rel).resolve() if card_rel else state / "paper-cards" / f"{paper_id}.json"
        dive_path = (repo / dive_rel).resolve() if dive_rel else output_root / "试卷精析" / f"{paper_id}.md"
        if not card_path.exists():
            issues.append(_issue("missing-paper-card", card_path, "Every manifest paper needs a paper-card JSON for this stage"))
        else:
            card_paths.append(card_path)
        if not dive_path.exists():
            issues.append(_issue("missing-paper-deep-dive", dive_path, "Every manifest paper needs a v0 paper deep dive"))
            continue
        issues.extend(_validate_markdown(dive_path, required_type="exam-paper-deep-dive"))
        if stage == "final":
            text = _read(dive_path)
            if not any(marker in text for marker in CROSS_PAPER_MARKERS):
                issues.append(
                    _issue(
                        "paper-deep-dive-missing-cross-paper-backfill",
                        dive_path,
                        "Final stage requires a cross-paper relationship/backfill section in each deep dive",
                    )
                )
    return issues, card_paths


def _card_ref_names(card_paths: list[Path]) -> set[str]:
    return {path.name for path in card_paths} | {path.stem for path in card_paths}


def _question_ref_index(card_paths: list[Path]) -> set[str]:
    refs: set[str] = set()
    for card_path in card_paths:
        try:
            card = load_json(card_path)
        except Exception:
            continue
        if not isinstance(card, dict):
            continue
        for question in card.get("questions") or []:
            if not isinstance(question, dict):
                continue
            question_id = str(question.get("question_id") or question.get("id") or "").strip()
            if not question_id:
                continue
            refs.add(f"{card_path.name}#{question_id}")
            refs.add(f"{card_path.stem}#{question_id}")
    return refs


def _extract_question_refs_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        return QUESTION_REF_TOKEN_RE.findall(value)
    if isinstance(value, list):
        refs: list[str] = []
        for item in value:
            refs.extend(_extract_question_refs_list(item))
        return refs
    if isinstance(value, dict):
        refs: list[str] = []
        for key in (
            "question_ref",
            "ref",
            "source_ref",
            "source_refs",
            "evidence_ref",
            "evidence_refs",
            "question_refs",
        ):
            refs.extend(_extract_question_refs_list(value.get(key)))
        return refs
    return []


def _extract_question_refs(value: Any) -> set[str]:
    return set(_extract_question_refs_list(value))


def _extract_frontmatter_field(text: str, field: str) -> str:
    match = re.search(rf"(?m)^{re.escape(field)}:\s*(.+)$", text)
    if not match:
        return ""
    return match.group(1).strip().strip('"\'')


def _section_text(text: str, title: str, *, stop_titles: tuple[str, ...] = ()) -> str:
    start = re.search(rf"(?m)^#{{1,6}}\s+.*{re.escape(title)}.*$", text)
    if not start:
        return ""
    tail = text[start.end() :]
    if stop_titles:
        stop_re = "|".join(re.escape(item) for item in stop_titles)
        stop = re.search(rf"(?m)^#{{1,6}}\s+.*(?:{stop_re}).*$", tail)
    else:
        stop = re.search(r"(?m)^#{1,6}\s+", tail)
    return tail[: stop.start()] if stop else tail


def _normalized_blocks(pattern: re.Pattern[str], text: str) -> list[str]:
    blocks: list[str] = []
    for match in pattern.finditer(text):
        block = re.sub(r"\s+", " ", match.group(1)).strip()
        if len(block) >= 60:
            blocks.append(block)
    return blocks


def _duplicate_blocks(blocks: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for block in blocks:
        if block in seen:
            duplicates.add(block)
        seen.add(block)
    return duplicates


def _has_insufficient_evidence_note(text: str) -> bool:
    return "证据不足" in text or "需人工补充" in text or "needs-review" in text


def _validate_type_dossiers(
    state: Path,
    output_root: Path,
    card_paths: list[Path],
    taxonomy_path: Path,
) -> tuple[list[dict[str, str]], dict[str, set[str]]]:
    issues: list[dict[str, str]] = []
    refs_by_type: dict[str, set[str]] = {}
    valid_refs = _question_ref_index(card_paths)
    dossier_dir = state / "type-dossiers"
    readable_dir = output_root / "题型备课卡"
    taxonomy_types: list[dict[str, Any]] = []
    if taxonomy_path.exists():
        try:
            taxonomy = load_json(taxonomy_path)
            taxonomy_types = [item for item in taxonomy.get("types") or [] if isinstance(item, dict)] if isinstance(taxonomy, dict) else []
        except Exception:
            taxonomy_types = []
    type_ids = [str(item.get("id") or "").strip() for item in taxonomy_types if str(item.get("id") or "").strip()]
    if not type_ids:
        if not any(dossier_dir.glob("*.json")) if dossier_dir.exists() else True:
            issues.append(_issue("missing-type-dossiers", dossier_dir, "Create type dossier JSONs after taxonomy"))
        return issues, refs_by_type

    for type_id in type_ids:
        path = dossier_dir / f"{type_id}.json"
        if not path.exists():
            issues.append(_issue("missing-type-dossier", path, f"Missing type dossier for {type_id}"))
            continue
        try:
            dossier = load_json(path)
        except Exception as exc:
            issues.append(_issue("type-dossier-invalid-json", path, f"Cannot read type dossier JSON: {exc}"))
            continue
        if not isinstance(dossier, dict):
            issues.append(_issue("type-dossier-not-object", path, "Type dossier must be a JSON object"))
            continue
        for field in REQUIRED_DOSSIER_FIELDS:
            value = dossier.get(field)
            if value in (None, "", [], {}):
                if field == "insufficient_evidence_notes" and str(dossier.get("quality") or "") != "needs-review":
                    continue
                issues.append(_issue("type-dossier-missing-field", path, f"Missing or empty dossier field: {field}"))
        if str(dossier.get("type_id") or "").strip() != type_id:
            issues.append(_issue("type-dossier-type-mismatch", path, f"type_id must match taxonomy id {type_id!r}"))
        if str(dossier.get("confidence") or "").strip() not in CONFIDENCE_ALLOWED:
            issues.append(_issue("type-dossier-invalid-confidence", path, "confidence must be high|medium|low|uncertain|needs-review"))

        source_refs = _extract_question_refs(dossier.get("source_question_refs"))
        worked_ref_list = _extract_question_refs_list(dossier.get("worked_example_candidates"))
        self_ref_list = _extract_question_refs_list(dossier.get("self_test_candidates"))
        worked_refs = set(worked_ref_list)
        self_refs = set(self_ref_list)
        all_refs = source_refs | worked_refs | self_refs
        refs_by_type[type_id] = all_refs
        for ref in sorted(all_refs):
            if valid_refs and ref not in valid_refs:
                issues.append(_issue("type-dossier-unknown-question-ref", path, f"Unknown paper-card question ref: {ref}"))
        overlap = worked_refs & self_refs
        if overlap:
            issues.append(
                _issue(
                    "type-dossier-example-selftest-overlap",
                    path,
                    "worked_example_candidates and self_test_candidates must be disjoint: " + ", ".join(sorted(overlap)),
                )
            )
        if len(worked_refs) != len(worked_ref_list):
            issues.append(_issue("type-dossier-duplicate-worked-example", path, "Duplicate worked example question refs"))
        if len(self_refs) != len(self_ref_list):
            issues.append(_issue("type-dossier-duplicate-self-test", path, "Duplicate self-test question refs"))
        if FABRICATED_QUESTION_RE.search(json.dumps(dossier, ensure_ascii=False)):
            issues.append(_issue("type-dossier-fabricated-question", path, "Dossier candidates must come from past papers, not fabricated/simulated questions"))
        readable = readable_dir / f"{type_id}.md"
        if not readable.exists():
            issues.append(_issue("missing-readable-type-dossier", readable, f"Missing readable 题型备课卡 for {type_id}"))
        else:
            issues.extend(_validate_markdown(readable))
    return issues, refs_by_type


def _validate_cross_paper_markdown(path: Path, card_paths: list[Path], message: str) -> list[dict[str, str]]:
    issues = _validate_markdown(path, required_type="exam-prep-analysis")
    if not path.exists():
        return issues
    text = _read(path)
    refs = _card_ref_names(card_paths)
    if refs and not any(ref in text for ref in refs):
        issues.append(_issue("analysis-missing-paper-card-ref", path, message))
    if ("原题" in text or "重复" in text or "相似" in text or "变式" in text) and not SOURCE_RE.search(text):
        issues.append(_issue("analysis-repeat-claim-missing-source", path, "Repeat/variant claims must cite source refs"))
    return issues


def _validate_guide(path: Path) -> list[dict[str, str]]:
    issues = _validate_markdown(path, required_type="exam-prep-guide")
    if not path.exists():
        return issues
    text = _read(path)
    if not any(marker in text for marker in GUIDE_ROUTE_MARKERS):
        issues.append(
            _issue(
                "guide-missing-start-route",
                path,
                "Entry page must tell the student what to open first, not only list artifacts",
            )
        )
    for marker in ("1 小时", "1 天", "3 天"):
        compact = marker.replace(" ", "")
        if marker not in text and compact not in text:
            issues.append(_issue("guide-missing-study-route", path, f"Entry page should include a {marker} route"))
    if ("文件" in text or "统计" in text or "产物" in text) and not any(marker in text for marker in ("先读", "第一步", "从这里开始")):
        issues.append(
            _issue(
                "guide-artifact-list-only",
                path,
                "Entry page appears to be an artifact list; it must explain how to study from the pack",
            )
        )
    return issues


def check(repo: Path, args: argparse.Namespace) -> dict[str, Any]:
    course_dir = resolve_course(repo, args.course, semester=args.semester)
    course_key = course_slug_of(course_dir, repo)
    scope = args.exam_scope.strip()
    exam_scope_key(scope)
    state = exam_prep_state_dir(repo, course_key, scope)
    output_root = reviews_dir(course_dir, scope)
    manifest_path = state / "manifest.json"
    taxonomy_path = state / "taxonomy.json"
    quality_standard_path = output_root / STANDARD_FILES["quality_standard"]
    source_map_path = state / STANDARD_FILES["source_map"]
    report_path = state / "quality-report.json"

    issues: list[dict[str, str]] = []
    if not manifest_path.exists():
        issues.append(_issue("missing-manifest", manifest_path, "Run exam_prep_build.py first"))
        manifest: dict[str, Any] = {}
    else:
        manifest = load_json(manifest_path)
        if manifest.get("workflow") != WORKFLOW:
            issues.append(_issue("manifest-workflow", manifest_path, f"manifest workflow must be {WORKFLOW}"))

    manifest_sources = {
        str(item.get("path") or "").replace("\\", "/")
        for item in manifest.get("papers", [])
        if isinstance(item, dict)
    }
    if args.stage in {"standard", "source-map", "gold-sample", "paper-v0", "synthesis", "type-dossier", "type-analysis-sample", "final"}:
        issues.extend(_validate_quality_standard(quality_standard_path))
    if args.stage in {"source-map", "gold-sample", "paper-v0", "synthesis", "type-dossier", "type-analysis-sample", "final"}:
        issues.extend(_validate_source_map(source_map_path, manifest_sources))

    card_dir = state / "paper-cards"
    needs_all_papers = args.stage in {"paper-v0", "synthesis", "type-dossier", "final"}
    manifest_output_issues, manifest_card_paths = ([], [])
    if needs_all_papers and manifest:
        manifest_output_issues, manifest_card_paths = _validate_manifest_paper_outputs(
            manifest,
            repo,
            state,
            output_root,
            stage=args.stage,
        )
        issues.extend(manifest_output_issues)
    discovered_card_paths = sorted(card_dir.glob("*.json")) if card_dir.exists() else []
    card_paths = sorted({*manifest_card_paths, *discovered_card_paths})
    if needs_all_papers and not card_paths:
        issues.append(_issue("missing-paper-cards", card_dir, "AI must create paper-card JSONs before taxonomy"))
    for card_path in card_paths:
        issues.extend(_validate_paper_card(card_path, manifest_sources, stage=args.stage))

    if args.stage in {"synthesis", "type-dossier", "type-analysis-sample", "final"}:
        issues.extend(_validate_taxonomy(taxonomy_path, card_paths))
    refs_by_type: dict[str, set[str]] = {}
    if args.stage in {"type-dossier", "type-analysis-sample", "final"}:
        dossier_issues, refs_by_type = _validate_type_dossiers(state, output_root, card_paths, taxonomy_path)
        issues.extend(dossier_issues)

    for dirname in ("试卷精析", "题型备课卡", "题型解析", "分析"):
        if not (output_root / dirname).is_dir():
            issues.append(_issue("missing-directory", output_root / dirname, "Required output directory is missing"))
    type_files = _nonempty_md_files(output_root / "题型解析")
    if args.stage == "gold-sample":
        issues.extend(_validate_gold_sample(output_root, refs_by_type))
    if args.stage == "type-analysis-sample":
        if not type_files:
            issues.append(_issue("missing-type-analysis-sample", output_root / "题型解析", "Write one type-analysis sample before expanding all pages"))
        else:
            issues.extend(_validate_type_analysis(type_files[0], refs_by_type))
    if args.stage == "final":
        if not type_files:
            issues.append(_issue("missing-type-analyses", output_root / "题型解析", "AI must write type analyses"))
        for path in type_files:
            issues.extend(_validate_type_analysis(path, refs_by_type))

    analysis_dir = output_root / "分析"
    if args.stage in {"synthesis", "final"}:
        for filename in ("01-题型频率统计.md", "02-跨年原题重复记录.md", "05-近年趋势与教考分离.md"):
            issues.extend(
                _validate_cross_paper_markdown(
                    analysis_dir / filename,
                    card_paths,
                    "Cross-paper analysis must cite paper-card/question refs",
                )
            )
    if args.stage == "final":
        for filename in CORE_ANALYSIS_FILES:
            if filename in {"01-题型频率统计.md", "02-跨年原题重复记录.md", "05-近年趋势与教考分离.md"}:
                continue
            issues.extend(_validate_markdown(analysis_dir / filename, required_type="exam-prep-analysis"))

    expected_types = {
        "guide": "exam-prep-guide",
        "formula_card": "formula-cheat-sheet",
        "answer_templates": "answer-template-quickref",
        "one_hour_checklist": "pre-exam-one-hour-checklist",
    }
    if args.stage == "final":
        for key, filename in PREP_PACK_FILES.items():
            if key == "guide":
                issues.extend(_validate_guide(output_root / filename))
            else:
                issues.extend(_validate_markdown(output_root / filename, required_type=expected_types[key]))

    ok = not any(issue["severity"] == "error" for issue in issues)
    error_codes = {issue["code"] for issue in issues if issue["severity"] == "error"}
    mechanical_codes = {"render-risk", "markdown-table", "placeholder-content"}
    source_markers = ("source", "ref", "card", "dossier", "taxonomy", "manifest")
    textbook_markers = ("textbook",)
    problem_markers = ("problem", "solution", "answer", "too-thin")
    example_markers = ("example", "self-test", "worked")
    payload = {
        "ok": ok,
        "tripwire_ok": ok,
        "tripwire_only": True,
        "reader_audit_required": True,
        "delivery_allowed_by_script": False,
        "schema_version": SCHEMA_VERSION,
        "workflow": WORKFLOW,
        "course": course_key,
        "exam_scope": scope,
        "stage": args.stage,
        "state_dir": str(state),
        "reviews_dir": str(output_root),
        "paper_cards": len(card_paths),
        "type_dossiers": len(refs_by_type),
        "type_analysis_files": len(type_files),
        "mechanical_ok": not (error_codes & mechanical_codes),
        "source_ok": not any(any(marker in code for marker in source_markers) for code in error_codes),
        "textbook_grounding_ok": not any(any(marker in code for marker in textbook_markers) for code in error_codes),
        "problem_completeness_ok": not any(any(marker in code for marker in problem_markers) for code in error_codes),
        "example_selftest_ok": not any(any(marker in code for marker in example_markers) for code in error_codes),
        "learnability_warnings": [
            issue
            for issue in issues
            if issue["severity"] == "warning" or issue["code"].startswith("type-analysis-low-quality")
        ],
        "issue_count": len(issues),
        "issues": [
            {**issue, "path": relative_posix(Path(issue["path"]), repo) if issue["path"] else issue["path"]}
            for issue in issues
        ],
        "next_action": (
            "Fix listed tripwire issues, then run a concrete reader audit before delivery; "
            "this script cannot certify readability, teaching quality, or math correctness."
        ),
    }
    if args.write_report:
        write_json(report_path, payload)
        payload["quality_report"] = str(report_path)
    return payload


def main() -> int:
    configure_stdout_utf8()
    args = parse_args()
    repo = Path(args.repo).resolve()
    payload = check(repo, args)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        status = "OK" if payload["ok"] else "NEEDS WORK"
        print(f"{status} {payload['workflow']} {payload['course']} {payload['exam_scope']}")
        for issue in payload["issues"][:20]:
            print(f"- [{issue['code']}] {issue['path']}: {issue['message']}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
