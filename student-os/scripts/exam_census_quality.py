#!/usr/bin/env python3
"""Shared quality contracts for exam-census Phase A–E."""
from __future__ import annotations

import re
from typing import Any

from exam_census_utils import markdown_table_pipe_issues

# Required top-level sections in filled type-analysis pages (content standard v2).
REQUIRED_SECTION_HEADINGS = [
    "元信息",
    "真卷对应题号",
    "考前速记",
    "本页最佳使用指引",
    "知识讲解",
    "例题精讲",
    "自测题",
    "来源校对说明",
]

# Zero-foundation entry layer must answer these four questions.
ENTRY_LAYER_MARKERS = [
    "这类题考试到底在考什么",
    "30秒认题",
    "2分钟下笔模板",
    "不会做时先写什么拿步骤分",
]

MIN_WORKED_EXAMPLES = 5
MIN_SELF_TESTS = 4

# Canonical short frontmatter for 题型解析 pages (Issue #51).
REQUIRED_TYPE_ANALYSIS_FRONTMATTER = [
    "type",
    "course",
    "exam_scope",
    "exam_type_id",
    "exam_type_name",
    "rank",
    "paper_count",
    "must_know",
    "quality",
    "status",
]

PLACEHOLDER_PATTERNS = (
    re.compile(r"\{\{[^}]+\}\}"),
    re.compile(r"_\(fill by review-coach\)_"),
    re.compile(r"(?i)\bTODO\b"),
    re.compile(r"(?i)\bTBD\b"),
)

ENGLISH_RESIDUE_PATTERNS = (
    (re.compile(r"Seeded from"), "English residue: Seeded from"),
    (re.compile(r"(?m)^\|\s*Paper\s*\|\s*Reliability\s*\|"), "English table header: Paper | Reliability"),
    (re.compile(r"(?m)^\|\s*Paper\s*\|\s*Difficulty\s*\|"), "English table header: Paper | Difficulty"),
    (re.compile(r"(?m)^\|\s*Paper\s*\|\s*Format\s*\|"), "English table header: Paper | Format"),
    (re.compile(r"(?m)^\|\s*[^|\n]*\|\s*unspecified\s*\|"), "English value: unspecified"),
    (re.compile(r"(?m)^#{1,6}\s+Common Pitfalls\b"), "English heading: Common Pitfalls"),
)

ALLOWED_TYPE_ANALYSIS_FRONTMATTER = set(REQUIRED_TYPE_ANALYSIS_FRONTMATTER) | {"source_summary"}

TEACHING_REASON_RE = re.compile(r"(为什么|原因|因此|所以|验算|易错)")
SOURCE_LINE_RE = re.compile(r"来源\s*[：:]")
VAGUE_SOURCE_RE = re.compile(r"来源\s*[：:]\s*(真题|待补|待补充|TBD|TODO)?\s*$", re.I | re.M)
FABRICATED_RE = re.compile(r"(自编题|模拟题)")
BLOCKQUOTE_TABLE_RE = re.compile(r"(?m)^>\s*\|")
DETAILS_BLOCK_RE = re.compile(r"(?is)<details\b[^>]*>.*?</details>")
DISPLAY_MATH_RE = re.compile(r"\$\$")

QUALITY_CHECK_LABELS = {
    "badge": "有 badge / 元信息区（频率/分值/难度/来源）",
    "quick_lookup": "有「一眼先记住」速查表",
    "symbols": "有术语/符号解释",
    "pitfalls": "有最容易混的 N 件事",
    "decision_tree": "有方法选择流程/决策树",
    "formulas": "有最少必须记住的公式",
    "worked_examples": f"有 ≥{MIN_WORKED_EXAMPLES} 道例题（含来源、方法引用与实质解析）",
    "self_tests": f"有 ≥{MIN_SELF_TESTS} 道自测题（含来源、题目与答案）",
    "entry_layer": "零基础入口四问齐全且非空",
    "required_sections": "必含区块齐全",
    "method_reference": f"例题解析含 ≥{MIN_WORKED_EXAMPLES} 处【方法引用】",
    "verification_steps": "含验证相关步骤/小节",
    "no_placeholders": "无未替换模板占位符",
    "frontmatter_shape": "题型解析 frontmatter 精简且字段齐全",
    "markdown_tables": "Markdown 表格列数未被裸 | 破坏",
    "chinese_user_facing": "面向用户文档无英文残留",
    "source_grounding": "例题/自测题均有真题来源，避免 AI 编造",
    "render_safe_markdown": "Markdown/LaTeX 在 Obsidian/GitHub 中可渲染",
    "teaching_scaffolding": "有步骤原因、选择逻辑、易错对比和验算",
}

FILL_QUEUE_INSTRUCTIONS = [
    "Fill this page to content-standard v2 (see references/exam-census-quality.md).",
    "题型解析面向中文学生：正文与表格中文优先；表格中行列式写 $\\lvert A\\rvert$，勿裸写 |A|。",
    "frontmatter 只保留短元数据（含 quality），不要写入 source_artifacts 长路径数组或 generated_fingerprint。",
    "输出必须像辅导老师讲义，不是知识清单。每个关键步骤都要说明为什么这么做；必须包含方法选择逻辑、易错对比、验算方式、不会做时的步骤分策略。",
    "所有例题和自测题必须来自 manifest/annotations 中命中该题型的 source_papers。禁止自行编造题目。每道题必须标注来源，格式为：来源：YYYY-YYYY 第X学期 第X题；如果 annotations 缺题号，写“来源：<试卷名>，题号待人工校对”。",
    f"默认要求至少 {MIN_WORKED_EXAMPLES} 道例题 + {MIN_SELF_TESTS} 道自测题。若该题型命中的真题实例少于 {MIN_WORKED_EXAMPLES + MIN_SELF_TESTS} 个，则尽量覆盖全部实例；不足部分不得编造，必须写“证据不足，需人工补充”，并设置 quality: needs-review。",
    "统一标题层级。例题统一用“### 例题 N（来源：...）”；自测统一用“### 自测 N（来源：...）”。不要使用引用块内表格。不要在 <details> 中使用 $$ 块级公式；更推荐不用 <details>，答案直接写在正文。",
    "从 annotations / 原文 sidecar 中查题号，不要猜。fill-queue 的 source_instances 若已有 exam_label / question_id，优先使用。",
    "Answer the zero-foundation entry four questions before deeper theory.",
    "Assign every annotated past-paper instance of this type to 例题精讲 or 自测题.",
]


def extract_frontmatter_block(text: str) -> str:
    if not text.startswith("---"):
        return ""
    match = re.match(r"^---\r?\n(.*?)\r?\n---\s*(?:\r?\n|$)", text, flags=re.S)
    if not match:
        return ""
    return match.group(1)


def frontmatter_field_names(frontmatter: str) -> set[str]:
    names: set[str] = set()
    for line in frontmatter.splitlines():
        match = re.match(r"^([A-Za-z_][\w]*)\s*:", line)
        if match:
            names.add(match.group(1))
    return names


def frontmatter_shape_issues(text: str) -> list[str]:
    issues: list[str] = []
    block = extract_frontmatter_block(text)
    if not block:
        return ["missing YAML frontmatter"]
    if re.search(r"(?m)^source_artifacts:\s*\[", block):
        issues.append("frontmatter still has bulky source_artifacts array")
    if re.search(r"(?m)^generated_fingerprint:\s*", block):
        issues.append("frontmatter still has machine-only generated_fingerprint")
    present = frontmatter_field_names(block)
    missing = [name for name in REQUIRED_TYPE_ANALYSIS_FRONTMATTER if name not in present]
    if missing:
        issues.append("missing required frontmatter fields: " + ", ".join(missing))
    extras = sorted(name for name in present if name not in ALLOWED_TYPE_ANALYSIS_FRONTMATTER)
    if extras:
        issues.append("unexpected frontmatter fields: " + ", ".join(extras))
    return issues


def english_residue_issues(text: str) -> list[str]:
    return [label for pattern, label in ENGLISH_RESIDUE_PATTERNS if pattern.search(text)]


def extract_headings(text: str) -> list[str]:
    return [
        match.group(1).strip()
        for line in text.splitlines()
        if (match := re.match(r"^#{1,6}\s+(.+?)\s*$", line))
    ]


def heading_blob(text: str) -> str:
    return "\n".join(extract_headings(text))


def missing_required_sections(text: str) -> list[str]:
    blob = heading_blob(text) + "\n" + text
    return [label for label in REQUIRED_SECTION_HEADINGS if label not in blob]


def missing_entry_layer(text: str) -> list[str]:
    return [marker for marker in ENTRY_LAYER_MARKERS if marker not in text]


def strip_markup(text: str) -> str:
    cleaned = re.sub(r"(?m)^#{1,6}\s+.*$", " ", text)
    cleaned = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cleaned)
    cleaned = re.sub(r"[|>`*_#\-\[\]()]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def has_substance(text: str, *, min_chars: int = 8) -> bool:
    body = strip_markup(text)
    if not body or len(body) < min_chars:
        return False
    if all(char in "|:- " for char in body):
        return False
    if PLACEHOLDER_PATTERNS[0].search(body):
        return False
    return True


def section_body_after(text: str, marker: str) -> str:
    """Return text after the first heading/line containing marker until the next same-or-higher heading."""
    lines = text.splitlines()
    start = None
    start_level = 2
    for index, line in enumerate(lines):
        if marker in line:
            heading = re.match(r"^(#{1,6})\s+", line)
            start = index + 1
            start_level = len(heading.group(1)) if heading else 2
            break
    if start is None:
        return ""
    collected: list[str] = []
    for line in lines[start:]:
        heading = re.match(r"^(#{1,6})\s+", line)
        if heading and len(heading.group(1)) <= start_level:
            break
        collected.append(line)
    return "\n".join(collected)


def _split_example_blocks(text: str) -> list[str]:
    return re.split(r"(?m)^###\s*(?:例题|Example)\b", text)[1:]


def _split_self_test_blocks(text: str) -> list[str]:
    return re.split(r"(?m)^###\s*(?:自测|Self[- ]?test)\b", text, flags=re.I)[1:]


def _concrete_source_value(value: str) -> bool:
    cleaned = value.strip().strip("*").strip()
    if not cleaned:
        return False
    if cleaned in {"真题", "待补", "待补充", "TBD", "TODO"}:
        return False
    if "YYYY" in cleaned or "第X学期" in cleaned or "第X题" in cleaned:
        return False
    # Require at least a paper/year cue, or explicit 题号待人工校对 with a paper name.
    if "题号待人工校对" in cleaned and len(cleaned) >= 6:
        return True
    if re.search(r"\d{4}", cleaned):
        return True
    if re.search(r"(期中|期末|学期|试卷|第\s*\d+\s*题)", cleaned):
        return True
    return len(cleaned) >= 4


def _block_has_source(block: str) -> bool:
    heading_line = block.splitlines()[0] if block.strip() else ""
    paren = re.search(r"（来源：([^）]*)）", heading_line)
    if paren and _concrete_source_value(paren.group(1)):
        return True
    for match in SOURCE_LINE_RE.finditer(block):
        # Take the rest of the line as the source value.
        line_end = block.find("\n", match.end())
        tail = block[match.end() : line_end if line_end >= 0 else None]
        if _concrete_source_value(tail):
            return True
    return False


def _example_has_prompt(block: str) -> bool:
    for marker in ("题目原文", "题目：", "题目"):
        if marker in block and has_substance(block.split(marker, 1)[-1][:400], min_chars=6):
            return True
    return has_substance(block[:500], min_chars=40)


def _example_has_solution(block: str) -> bool:
    for marker in ("完整解析", "解析", "Solution"):
        if marker in block and has_substance(block.split(marker, 1)[-1][:600], min_chars=12):
            return True
    return False


def _example_has_method_ref(block: str) -> bool:
    return bool(re.search(r"【方法引用】\s*\S+", block)) and "步骤 _" not in block and "步骤 X" not in block


def _example_has_teaching(block: str) -> bool:
    return bool(TEACHING_REASON_RE.search(block))


def count_filled_examples(text: str) -> int:
    filled = 0
    for block in _split_example_blocks(text):
        if (
            _block_has_source(block)
            and _example_has_prompt(block)
            and _example_has_solution(block)
            and _example_has_method_ref(block)
            and _example_has_teaching(block)
        ):
            filled += 1
    return filled


def _self_test_has_prompt(block: str) -> bool:
    for marker in ("**题目**", "题目：", "题目"):
        if marker in block and has_substance(block.split(marker, 1)[-1][:400], min_chars=6):
            return True
    return has_substance(block[:400], min_chars=20)


def _self_test_has_answer(block: str) -> bool:
    for marker in ("答案与解析", "答案", "Answer"):
        if marker in block and has_substance(block.split(marker, 1)[-1][:500], min_chars=6):
            return True
    return False


def count_filled_self_tests(text: str) -> int:
    filled = 0
    for block in _split_self_test_blocks(text):
        if _block_has_source(block) and _self_test_has_prompt(block) and _self_test_has_answer(block):
            filled += 1
    return filled


def unresolved_placeholders(text: str) -> list[str]:
    issues: list[str] = []
    if PLACEHOLDER_PATTERNS[0].search(text):
        issues.append("unresolved {{template}} placeholders")
    if PLACEHOLDER_PATTERNS[1].search(text):
        issues.append("unresolved _(fill by review-coach)_ markers")
    return issues


def entry_layer_issues(text: str) -> list[str]:
    issues: list[str] = []
    for marker in ENTRY_LAYER_MARKERS:
        if marker not in text:
            issues.append(f"missing entry marker: {marker}")
            continue
        body = section_body_after(text, marker)
        if not has_substance(body, min_chars=6):
            issues.append(f"empty entry block: {marker}")
    return issues


def source_grounding_issues(text: str) -> list[str]:
    issues: list[str] = []
    example_blocks = _split_example_blocks(text)
    self_test_blocks = _split_self_test_blocks(text)
    if not example_blocks and not self_test_blocks:
        return ["no worked examples or self-tests to ground"]

    for index, block in enumerate(example_blocks, start=1):
        if not _block_has_source(block):
            issues.append(f"例题 {index} missing concrete 来源")
        elif VAGUE_SOURCE_RE.search(block):
            issues.append(f"例题 {index} has vague 来源 label")
        if FABRICATED_RE.search(block) and "改编" not in block and "原题" not in block:
            issues.append(f"例题 {index} looks fabricated without adaptation basis")

    for index, block in enumerate(self_test_blocks, start=1):
        if not _block_has_source(block):
            issues.append(f"自测 {index} missing concrete 来源")
        elif VAGUE_SOURCE_RE.search(block):
            issues.append(f"自测 {index} has vague 来源 label")
        if FABRICATED_RE.search(block) and "改编" not in block and "原题" not in block:
            issues.append(f"自测 {index} looks fabricated without adaptation basis")

    return issues


def render_safe_markdown_issues(text: str) -> list[str]:
    issues: list[str] = []
    if BLOCKQUOTE_TABLE_RE.search(text):
        issues.append("blockquote contains Markdown table rows (> | ... |)")
    for block in DETAILS_BLOCK_RE.findall(text):
        if DISPLAY_MATH_RE.search(block):
            issues.append("<details> contains display math $$ ... $$")
            break
    return issues


def teaching_scaffolding_issues(text: str) -> list[str]:
    issues: list[str] = []
    has_decision = ("方法选择树" in text) or ("决策流程" in text) or ("├" in text) or ("方法选择" in text)
    if not has_decision:
        issues.append("missing 方法选择树 / 决策流程")
    if not TEACHING_REASON_RE.search(text) and "为什么这么做" not in text:
        issues.append("missing why/reason teaching explanations")
    if not re.search(r"(易错点|错法|正法|最容易混)", text):
        issues.append("missing 易错点 / 错法 vs 正法")
    if not re.search(r"(验算|校验|验证|检查方式)", text):
        issues.append("missing 验算 / 检查方式")
    if "不会做时先写什么拿步骤分" not in text:
        issues.append("missing 不会做时先写什么拿步骤分")
    return issues


def structural_review(path_label: str, text: str) -> dict[str, Any]:
    missing_sections = missing_required_sections(text)
    entry_issues = entry_layer_issues(text)
    example_count = count_filled_examples(text)
    self_test_count = count_filled_self_tests(text)
    placeholder_issues = unresolved_placeholders(text)
    method_ref_count = len(re.findall(r"【方法引用】\s*\S+", text))
    has_verification = bool(re.search(r"(验证|校验|验算|verify)", text, re.I)) and has_substance(
        "\n".join(line for line in text.splitlines() if re.search(r"(验证|校验|验算|verify)", line, re.I)),
        min_chars=4,
    )
    fm_issues = frontmatter_shape_issues(text)
    table_issues = markdown_table_pipe_issues(text)
    residue_issues = english_residue_issues(text)
    source_issues = source_grounding_issues(text)
    render_issues = render_safe_markdown_issues(text)
    teaching_issues = teaching_scaffolding_issues(text)

    quick_body = section_body_after(text, "一眼先记住")
    symbol_body = section_body_after(text, "符号") + "\n" + section_body_after(text, "术语")
    pitfall_body = section_body_after(text, "最容易混") or section_body_after(text, "易错点")
    formula_body = section_body_after(text, "最少必须记住的公式") or section_body_after(text, "本篇最少")
    decision_body = section_body_after(text, "方法选择") or section_body_after(text, "决策")
    if "├" in text and not decision_body:
        idx = text.find("├")
        decision_body = text[idx : idx + 160]
    decision_ok = (("├" in text) or ("方法选择" in text) or ("决策" in text)) and has_substance(
        decision_body, min_chars=6
    )
    meta_body = section_body_after(text, "元信息") or text
    badge_ok = (
        (("频率" in meta_body) or ("考试频率" in text))
        and ("难度" in meta_body or "难度" in text)
        and has_substance(meta_body[:240], min_chars=6)
        and "{{" not in meta_body[:120]
    )

    checks = {
        "required_sections": {
            "pass": not missing_sections,
            "issues": [f"missing section: {item}" for item in missing_sections],
        },
        "entry_layer": {
            "pass": not entry_issues,
            "issues": entry_issues,
        },
        "worked_examples": {
            "pass": example_count >= MIN_WORKED_EXAMPLES,
            "issues": []
            if example_count >= MIN_WORKED_EXAMPLES
            else [
                f"need >={MIN_WORKED_EXAMPLES} filled worked examples with source/method refs/teaching, found {example_count}"
            ],
        },
        "self_tests": {
            "pass": self_test_count >= MIN_SELF_TESTS,
            "issues": []
            if self_test_count >= MIN_SELF_TESTS
            else [
                f"need >={MIN_SELF_TESTS} filled self-tests with source/prompt/answer, found {self_test_count}"
            ],
        },
        "badge": {
            "pass": badge_ok,
            "issues": [] if badge_ok else ["missing filled badge block"],
        },
        "quick_lookup": {
            "pass": "一眼先记住" in text and has_substance(quick_body, min_chars=6),
            "issues": []
            if ("一眼先记住" in text and has_substance(quick_body, min_chars=6))
            else ["missing filled 一眼先记住 table"],
        },
        "symbols": {
            "pass": (("符号" in text) or ("术语" in text)) and has_substance(symbol_body, min_chars=6),
            "issues": []
            if ((("符号" in text) or ("术语" in text)) and has_substance(symbol_body, min_chars=6))
            else ["missing filled symbol/term table"],
        },
        "pitfalls": {
            "pass": (("最容易混" in text) or ("易错点" in text)) and has_substance(pitfall_body, min_chars=8),
            "issues": []
            if ((("最容易混" in text) or ("易错点" in text)) and has_substance(pitfall_body, min_chars=8))
            else ["missing filled pitfalls block"],
        },
        "decision_tree": {
            "pass": decision_ok,
            "issues": [] if decision_ok else ["missing filled decision tree"],
        },
        "formulas": {
            "pass": (("最少必须记住的公式" in text) or ("本篇最少" in text)) and has_substance(formula_body, min_chars=8),
            "issues": []
            if ((("最少必须记住的公式" in text) or ("本篇最少" in text)) and has_substance(formula_body, min_chars=8))
            else ["missing filled must-remember formulas"],
        },
        "method_reference": {
            "pass": method_ref_count >= MIN_WORKED_EXAMPLES,
            "issues": []
            if method_ref_count >= MIN_WORKED_EXAMPLES
            else [f"need >={MIN_WORKED_EXAMPLES} 【方法引用】entries with content, found {method_ref_count}"],
        },
        "verification_steps": {
            "pass": has_verification,
            "issues": [] if has_verification else ["missing verification/校验 steps"],
        },
        "no_placeholders": {
            "pass": not placeholder_issues,
            "issues": placeholder_issues,
        },
        "frontmatter_shape": {
            "pass": not fm_issues,
            "issues": fm_issues,
        },
        "markdown_tables": {
            "pass": not table_issues,
            "issues": table_issues,
        },
        "chinese_user_facing": {
            "pass": not residue_issues,
            "issues": residue_issues,
        },
        "source_grounding": {
            "pass": not source_issues,
            "issues": source_issues,
        },
        "render_safe_markdown": {
            "pass": not render_issues,
            "issues": render_issues,
        },
        "teaching_scaffolding": {
            "pass": not teaching_issues,
            "issues": teaching_issues,
        },
    }
    failed = [name for name, payload in checks.items() if not payload["pass"]]
    verdict = "pass" if not failed else "needs-revision"
    return {
        "file": path_label,
        "kind": "type-analysis",
        "verdict": verdict,
        "checks": checks,
        "failed_checks": failed,
    }


def analysis_report_review(path_label: str, text: str) -> dict[str, Any]:
    """Lighter gate for analysis/*.md user-facing reports (Issue #51)."""
    table_issues = markdown_table_pipe_issues(text)
    residue_issues = english_residue_issues(text)
    checks = {
        "markdown_tables": {
            "pass": not table_issues,
            "issues": table_issues,
        },
        "chinese_user_facing": {
            "pass": not residue_issues,
            "issues": residue_issues,
        },
    }
    failed = [name for name, payload in checks.items() if not payload["pass"]]
    verdict = "pass" if not failed else "needs-revision"
    return {
        "file": path_label,
        "kind": "analysis-report",
        "verdict": verdict,
        "checks": checks,
        "failed_checks": failed,
    }
