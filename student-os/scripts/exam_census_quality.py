#!/usr/bin/env python3
"""Shared quality contracts for exam-census Phase A–E."""
from __future__ import annotations

import re
from typing import Any

from exam_census_utils import markdown_table_pipe_issues

# Required top-level sections in filled type-analysis pages (content standard v3).
REQUIRED_SECTION_HEADINGS = [
    "元信息",
    "真卷对应题号",
    "考前速记",
    "核心概念",
    "核心方法",
    "零基础先看这里",
    "例题精讲",
    "自测题",
    "自测答案",
    "快速得分技巧",
    "易错点与检查清单",
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
MIN_DIFFICULTY_STARRED_EXAMPLES = 3

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

TEACHING_REASON_RE = re.compile(
    r"(为什么这么做|先做什么，为什么|为什么|验算|易错点对比|错法|正法)"
)
METHOD_REF_RE = re.compile(r"(?m)【方法引用】[^\S\r\n]*\S+")
SOURCE_LINE_RE = re.compile(r"来源\s*[：:]")
VAGUE_SOURCE_RE = re.compile(r"来源\s*[：:]\s*(真题|待补|待补充|TBD|TODO)?\s*$", re.I | re.M)
FABRICATED_RE = re.compile(r"(自编题|模拟题)")
BLOCKQUOTE_TABLE_RE = re.compile(r"(?m)^>\s*\|")
DETAILS_BLOCK_RE = re.compile(r"(?is)<details\b[^>]*>.*?</details>")
DISPLAY_MATH_RE = re.compile(r"\$\$")
EVIDENCE_SHORT_MARKER = "证据不足，需人工补充"

QUALITY_CHECK_LABELS = {
    "badge": "有 badge / 元信息区（频率/分值/难度/来源）",
    "quick_lookup": "有「一眼先记住」速查表",
    "symbols": "有术语/符号解释",
    "pitfalls": "有最容易混的 N 件事或易错清单",
    "decision_tree": "有 ASCII 方法选择决策树（含 ├）",
    "formulas": "有关键公式表",
    "worked_examples": f"有 ≥{MIN_WORKED_EXAMPLES} 道例题（含来源、方法引用与实质解析）",
    "self_tests": f"有 ≥{MIN_SELF_TESTS} 道自测题（含来源、题目；答案在独立章）",
    "entry_layer": "零基础入口四问齐全且非空",
    "required_sections": "必含区块齐全（content standard v3）",
    "method_reference": f"例题解析含 ≥{MIN_WORKED_EXAMPLES} 处【方法引用】",
    "verification_steps": "含验证相关步骤/小节",
    "no_placeholders": "无未替换模板占位符",
    "frontmatter_shape": "题型解析 frontmatter 精简且字段齐全",
    "markdown_tables": "Markdown 表格列数未被裸 | 破坏",
    "chinese_user_facing": "面向用户文档无英文残留",
    "source_grounding": "例题/自测题均有真题来源，避免 AI 编造",
    "render_safe_markdown": "Markdown/LaTeX 在 Obsidian/GitHub 中可渲染",
    "teaching_scaffolding": "有步骤原因、选择逻辑、易错对比和验算",
    "concept_explanation": "有核心概念（定义或对比）",
    "core_methods": "有核心方法（适用场景/步骤）",
    "scoring_strategy": "有快速得分技巧（按时间分档）",
    "error_comparison": "有易错点对比表（错误/正确/原因）",
    "difficulty_stars": f"至少 {MIN_DIFFICULTY_STARRED_EXAMPLES} 道例题标注难度星级",
    "self_test_answer_separation": "自测题与自测答案分章（先试后看）",
    "fill_in_answer_template": "有填空式答题模板占位符",
}

FILL_QUEUE_INSTRUCTIONS = [
    "Fill this page to content-standard v3 (see references/exam-census-quality.md).",
    "题型解析面向中文学生：表格为主、段落为辅；表格中行列式写 $\\lvert A\\rvert$，勿裸写 |A|。",
    "frontmatter 只保留短元数据（含 quality），不要写入 source_artifacts 长路径数组或 generated_fingerprint。",
    "输出必须像辅导老师讲义，不是知识清单。每个关键步骤都要说明为什么这么做；必须包含方法选择逻辑、易错对比、验算方式、不会做时的步骤分策略。",
    "考前速记必须含 ASCII 方法选择决策树（使用 ├─ / └─），以及关键公式表。",
    "必须填写「核心概念」（定义 + 易混对比表）与「核心方法」（适用场景→步骤→关键技巧 + 选择速查）。",
    "2分钟下笔模板与答题骨架优先使用填空式占位符，如 [表达式]、[值]、[答案]。",
    "所有例题和自测题必须来自 manifest/annotations 中命中该题型的 source_papers。禁止自行编造题目。每道题必须标注来源，格式为：来源：YYYY-YYYY 第X学期 第X题；如果 annotations 缺题号，写“来源：<试卷名>，题号待人工校对”。",
    f"默认要求至少 {MIN_WORKED_EXAMPLES} 道例题 + {MIN_SELF_TESTS} 道自测题。若该题型命中的真题实例少于 {MIN_WORKED_EXAMPLES + MIN_SELF_TESTS} 个，则尽量覆盖全部实例；不足部分不得编造，必须写“证据不足，需人工补充”，并设置 quality: needs-review。",
    "例题按难度递增，标题或正文标注难度星级（⭐…⭐⭐⭐⭐⭐）。",
    "统一标题层级。例题统一用“### 例题 N（来源：... · 难度：⭐...）”；自测统一用“### 自测 N（来源：...）”。自测题区只放题目与提示；答案写在独立章节「## 自测答案」。",
    "「快速得分技巧」按时间充裕/紧张/几乎不够/完全不会分档；「易错点与检查清单」使用表格列：易错点 | 错误做法 | 正确做法 | 原因。",
    "不要使用引用块内表格。不要在 <details> 中使用 $$ 块级公式；不要用 <details> 藏答案。",
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


def section_body_after_heading(text: str, heading_substr: str) -> str:
    """Like section_body_after, but only matches AT{1,6} headings containing heading_substr."""
    lines = text.splitlines()
    start = None
    start_level = 2
    for index, line in enumerate(lines):
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading and heading_substr in heading.group(2):
            start = index + 1
            start_level = len(heading.group(1))
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


def _questions_section(text: str) -> str:
    """Body of ## 自测题 until the next same-level heading (通常是 ## 自测答案)."""
    return section_body_after_heading(text, "自测题")


def _answers_section(text: str) -> str:
    return section_body_after_heading(text, "自测答案")


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
    if "步骤 _" in block or "步骤 X" in block:
        return False
    return bool(METHOD_REF_RE.search(block))


def count_method_references(text: str) -> int:
    return len(METHOD_REF_RE.findall(text))


def _example_has_teaching(block: str) -> bool:
    return bool(TEACHING_REASON_RE.search(block))


def frontmatter_quality_value(text: str) -> str:
    block = extract_frontmatter_block(text)
    if not block:
        return ""
    match = re.search(r"(?m)^quality:\s*(.+)$", block)
    if not match:
        return ""
    raw = match.group(1).strip()
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1].strip()
    return raw


def is_evidence_short_page(text: str) -> bool:
    """True when the page documents insufficient evidence and asks for human review."""
    return frontmatter_quality_value(text) == "needs-review" and EVIDENCE_SHORT_MARKER in text


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
    for marker in ("答案与解析", "**答案**", "答案：", "答案:", "Answer:", "Answer："):
        if marker in block and has_substance(block.split(marker, 1)[-1][:500], min_chars=6):
            return True
    # Broader fallback for legacy English headings.
    if "Answer" in block and has_substance(block.split("Answer", 1)[-1][:500], min_chars=6):
        return True
    return False


_SELF_TEST_Q_HEADING_RE = re.compile(
    r"(?m)^###\s*(?:自测|Self[- ]?test)\s+(\d+)(?!\s*答案)\b[^\n]*",
    re.I,
)
_SELF_TEST_A_HEADING_RE = re.compile(r"(?m)^###\s*自测\s+(\d+)\s*答案\b[^\n]*")
FILL_IN_PLACEHOLDER_RE = re.compile(
    r"\[(?:表达式|值|答案|结论|中间量|步骤[0-9一二三四五六七八九十]*|占位符)\]"
)
INLINE_ANSWER_MARKER_RE = re.compile(
    r"(答案与解析|(?m)^\s*\*\*?答案\*\*?\s*[：:]|(?m)^\s*答案\s*[：:]|Answer\s*[：:])"
)


def _numbered_heading_blocks(section: str, heading_re: re.Pattern[str]) -> list[tuple[str, str]]:
    matches = list(heading_re.finditer(section))
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        blocks.append((match.group(1), section[start:end]))
    return blocks


def _split_self_test_blocks(text: str) -> list[str]:
    """Question blocks only（排除 ### 自测 N 答案）."""
    section = _questions_section(text) or text
    return [body for _, body in _numbered_heading_blocks(section, _SELF_TEST_Q_HEADING_RE)]


def _split_self_test_answer_blocks(text: str) -> list[str]:
    section = _answers_section(text)
    if not section.strip():
        return []
    return [body for _, body in _numbered_heading_blocks(section, _SELF_TEST_A_HEADING_RE)]


def count_filled_self_tests(text: str) -> int:
    question_blocks = _numbered_heading_blocks(_questions_section(text) or text, _SELF_TEST_Q_HEADING_RE)
    answer_map = {
        number: body
        for number, body in _numbered_heading_blocks(_answers_section(text), _SELF_TEST_A_HEADING_RE)
    }
    has_answer_section = bool(re.search(r"(?m)^#{1,6}\s+自测答案\b", text))
    filled = 0
    for number, block in question_blocks:
        if not (_block_has_source(block) and _self_test_has_prompt(block)):
            continue
        paired = answer_map.get(number, "")
        if _self_test_has_answer(paired):
            filled += 1
            continue
        # Legacy inline answers only when there is no dedicated 自测答案 section.
        if not has_answer_section and _self_test_has_answer(block):
            filled += 1
    return filled


def count_starred_examples(text: str) -> int:
    starred = 0
    for block in _split_example_blocks(text):
        heading = block.splitlines()[0] if block.strip() else ""
        blob = heading + "\n" + "\n".join(block.splitlines()[:12])
        if re.search(r"⭐{2,}|难度\s*[：:].*⭐", blob):
            starred += 1
        elif re.search(r"(?m)^\*\*难度\*\*\s*[：:].*⭐", blob):
            starred += 1
    return starred


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
    if not re.search(r"(易错点|错法|正法|最容易混|错误做法)", text):
        issues.append("missing 易错点 / 错法 vs 正法")
    if not re.search(r"(验算|校验|验证|检查方式)", text):
        issues.append("missing 验算 / 检查方式")
    if "不会做时先写什么拿步骤分" not in text:
        issues.append("missing 不会做时先写什么拿步骤分")
    return issues


def concept_explanation_issues(text: str) -> list[str]:
    if not re.search(r"(?m)^#{1,6}\s+核心概念\b", text):
        return ["missing 核心概念 section"]
    body = section_body_after_heading(text, "核心概念")
    if not has_substance(body, min_chars=8):
        return ["empty 核心概念 section"]
    if not (("定义" in body) or ("对比" in body) or ("|" in body)):
        return ["核心概念 missing 定义/对比 content"]
    return []


def core_methods_issues(text: str) -> list[str]:
    if not re.search(r"(?m)^#{1,6}\s+核心方法\b", text):
        return ["missing 核心方法 section"]
    body = section_body_after_heading(text, "核心方法")
    if not has_substance(body, min_chars=8):
        return ["empty 核心方法 section"]
    if "适用场景" not in body and "方法选择" not in body:
        return ["核心方法 missing 适用场景 / 方法选择 cues"]
    return []


def _filled_table_data_rows(body: str, *, min_nonempty_cells: int = 2) -> list[list[str]]:
    """Return non-separator, non-header-ish markdown table data rows with enough filled cells."""
    rows: list[list[str]] = []
    header_tokens = {
        "时间情况",
        "策略",
        "大约可省",
        "易错点",
        "错误做法",
        "正确做法",
        "原因",
        "项目",
        "内容",
    }
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if re.match(r"^\|?\s*:?-{3,}", stripped.replace("|", " ").strip()) or re.search(
            r"^\|(\s*:?-{3,}\s*\|)+\s*$", stripped
        ):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells:
            continue
        if cells[0] in header_tokens:
            continue
        nonempty = [cell for cell in cells if cell]
        if len(nonempty) >= min_nonempty_cells:
            rows.append(cells)
    return rows


def scoring_strategy_issues(text: str) -> list[str]:
    if not re.search(r"(?m)^#{1,6}\s+快速得分技巧\b", text):
        return ["missing 快速得分技巧 section"]
    body = section_body_after_heading(text, "快速得分技巧")
    if not re.search(r"(时间充裕|时间紧张|几乎不够|完全不会|时间不够)", body):
        return ["快速得分技巧 missing time-tier cues"]
    filled_rows = _filled_table_data_rows(body, min_nonempty_cells=2)
    strategy_filled = 0
    for cells in filled_rows:
        # Expect: 时间情况 | 策略 | 大约可省
        strategy = cells[1].strip() if len(cells) > 1 else ""
        if strategy and strategy not in {"策略", "---"}:
            strategy_filled += 1
    if strategy_filled < 2:
        return ["快速得分技巧 needs >=2 filled strategy rows beyond time-tier labels"]
    return []


def error_comparison_issues(text: str) -> list[str]:
    checklist = section_body_after_heading(text, "易错点与检查清单") or section_body_after_heading(
        text, "易错点"
    )
    blob = checklist or ""
    if not blob.strip():
        return ["missing 易错点与检查清单 section"]
    if not (("错误做法" in blob) and ("正确做法" in blob) and ("原因" in blob)):
        return ["missing page-level 错误做法 / 正确做法 / 原因 comparison table"]
    filled_rows = _filled_table_data_rows(blob, min_nonempty_cells=3)
    concrete = 0
    for cells in filled_rows:
        if len(cells) >= 4 and all(cells[i].strip() for i in range(4)):
            concrete += 1
        elif len([c for c in cells if c.strip()]) >= 3:
            concrete += 1
    if concrete < 1:
        return ["易错点与检查清单 needs >=1 filled wrong/right/reason data row"]
    return []


def difficulty_stars_issues(text: str, *, min_needed: int = MIN_DIFFICULTY_STARRED_EXAMPLES) -> list[str]:
    starred = count_starred_examples(text)
    if starred >= min_needed:
        return []
    return [f"need >={min_needed} worked examples with difficulty stars, found {starred}"]


def self_test_answer_separation_issues(text: str) -> list[str]:
    issues: list[str] = []
    if not re.search(r"(?m)^#{1,6}\s+自测答案\b", text):
        issues.append("missing ## 自测答案 section")
    questions = _questions_section(text)
    for match in INLINE_ANSWER_MARKER_RE.finditer(questions):
        after = questions[match.end() : match.end() + 400]
        if has_substance(after, min_chars=6):
            issues.append("自测题 section still contains inline answers; move answers to 自测答案")
            break
    return issues


def fill_in_answer_template_issues(text: str) -> list[str]:
    # Prefer the dedicated template section; fall back to whole page.
    body = section_body_after_heading(text, "填空式答题模板") or section_body_after_heading(
        text, "2分钟下笔模板"
    )
    haystack = body if body.strip() else text
    if FILL_IN_PLACEHOLDER_RE.search(haystack):
        return []
    return ["missing fill-in answer template placeholders like [表达式] / [答案]"]


def structural_review(path_label: str, text: str) -> dict[str, Any]:
    missing_sections = missing_required_sections(text)
    entry_issues = entry_layer_issues(text)
    example_count = count_filled_examples(text)
    self_test_count = count_filled_self_tests(text)
    placeholder_issues = unresolved_placeholders(text)
    method_ref_count = count_method_references(text)
    evidence_short = is_evidence_short_page(text)
    min_examples = 1 if evidence_short else MIN_WORKED_EXAMPLES
    min_self_tests = 1 if evidence_short else MIN_SELF_TESTS
    min_method_refs = 1 if evidence_short else MIN_WORKED_EXAMPLES
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
    concept_issues = concept_explanation_issues(text)
    methods_issues = core_methods_issues(text)
    scoring_issues = scoring_strategy_issues(text)
    error_issues = error_comparison_issues(text)
    star_needed = 1 if evidence_short else MIN_DIFFICULTY_STARRED_EXAMPLES
    star_issues = difficulty_stars_issues(text, min_needed=star_needed)
    separation_issues = self_test_answer_separation_issues(text)
    fill_in_issues = fill_in_answer_template_issues(text)

    quick_body = section_body_after(text, "一眼先记住")
    symbol_body = section_body_after(text, "符号") + "\n" + section_body_after(text, "术语")
    pitfall_body = (
        section_body_after(text, "易错点与检查清单")
        or section_body_after(text, "最容易混")
        or section_body_after(text, "易错点")
    )
    formula_body = (
        section_body_after(text, "关键公式表")
        or section_body_after(text, "最少必须记住的公式")
        or section_body_after(text, "本篇最少")
    )
    decision_body = section_body_after(text, "方法选择") or section_body_after(text, "决策")
    if "├" in text and not decision_body:
        idx = text.find("├")
        decision_body = text[idx : idx + 160]
    decision_ok = ("├" in text) and has_substance(decision_body, min_chars=6)
    meta_body = section_body_after(text, "元信息") or text
    badge_ok = (
        (("频率" in meta_body) or ("考试频率" in text))
        and ("难度" in meta_body or "难度" in text)
        and has_substance(meta_body[:240], min_chars=6)
        and "{{" not in meta_body[:120]
    )

    def _count_issue(kind: str, needed: int, found: int) -> list[str]:
        if found >= needed:
            return []
        suffix = " (evidence-short / needs-review path)" if evidence_short else ""
        return [f"need >={needed} filled {kind}, found {found}{suffix}"]

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
            "pass": example_count >= min_examples,
            "issues": _count_issue(
                "worked examples with source/method refs/teaching",
                min_examples,
                example_count,
            ),
        },
        "self_tests": {
            "pass": self_test_count >= min_self_tests,
            "issues": _count_issue(
                "self-tests with source/prompt/answer",
                min_self_tests,
                self_test_count,
            ),
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
            "issues": [] if decision_ok else ["missing ASCII decision tree with ├"],
        },
        "formulas": {
            "pass": (
                ("关键公式表" in text) or ("最少必须记住的公式" in text) or ("本篇最少" in text)
            )
            and has_substance(formula_body, min_chars=8),
            "issues": []
            if (
                (("关键公式表" in text) or ("最少必须记住的公式" in text) or ("本篇最少" in text))
                and has_substance(formula_body, min_chars=8)
            )
            else ["missing filled key formulas table"],
        },
        "method_reference": {
            "pass": method_ref_count >= min_method_refs,
            "issues": _count_issue("【方法引用】entries with content", min_method_refs, method_ref_count),
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
        "concept_explanation": {
            "pass": not concept_issues,
            "issues": concept_issues,
        },
        "core_methods": {
            "pass": not methods_issues,
            "issues": methods_issues,
        },
        "scoring_strategy": {
            "pass": not scoring_issues,
            "issues": scoring_issues,
        },
        "error_comparison": {
            "pass": not error_issues,
            "issues": error_issues,
        },
        "difficulty_stars": {
            "pass": not star_issues,
            "issues": star_issues,
        },
        "self_test_answer_separation": {
            "pass": not separation_issues,
            "issues": separation_issues,
        },
        "fill_in_answer_template": {
            "pass": not fill_in_issues,
            "issues": fill_in_issues,
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
