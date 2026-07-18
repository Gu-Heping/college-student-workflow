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
)

QUALITY_CHECK_LABELS = {
    "badge": "有 badge / 元信息区（频率/分值/难度/来源）",
    "quick_lookup": "有「一眼先记住」速查表",
    "symbols": "有术语/符号解释",
    "pitfalls": "有最容易混的 N 件事",
    "decision_tree": "有方法选择流程/决策树",
    "formulas": "有最少必须记住的公式",
    "worked_examples": "有 2 道以上例题（含方法引用与实质解析）",
    "self_tests": "有 2 道以上自测题（含答案）",
    "entry_layer": "零基础入口四问齐全且非空",
    "required_sections": "必含区块齐全",
    "method_reference": "例题解析含【方法引用】",
    "verification_steps": "含验证相关步骤/小节",
    "no_placeholders": "无未替换模板占位符",
    "frontmatter_shape": "题型解析 frontmatter 精简且字段齐全",
    "markdown_tables": "Markdown 表格列数未被裸 | 破坏",
    "chinese_user_facing": "面向用户文档无英文残留",
}


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


def count_filled_examples(text: str) -> int:
    blocks = re.split(r"(?m)^###\s*(?:例题|Example)\b", text)[1:]
    filled = 0
    for block in blocks:
        has_prompt = ("题目" in block and has_substance(block.split("题目", 1)[-1][:400], min_chars=6)) or has_substance(
            block[:500], min_chars=40
        )
        has_solution = ("解析" in block and has_substance(block.split("解析", 1)[-1][:600], min_chars=12)) or (
            "Solution" in block and has_substance(block.split("Solution", 1)[-1][:600], min_chars=12)
        )
        has_method_ref = bool(re.search(r"【方法引用】\s*\S+", block)) and "步骤 _" not in block
        if has_prompt and has_solution and has_method_ref:
            filled += 1
    return filled


def count_filled_self_tests(text: str) -> int:
    blocks = re.split(r"(?m)^###\s*(?:自测|Self[- ]?test)\b", text, flags=re.I)[1:]
    filled = 0
    for block in blocks:
        has_answer = ("答案" in block and has_substance(block.split("答案", 1)[-1][:500], min_chars=6)) or (
            "Answer" in block and has_substance(block.split("Answer", 1)[-1][:500], min_chars=6)
        )
        if has_answer and has_substance(block[:400], min_chars=20):
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

    quick_body = section_body_after(text, "一眼先记住")
    symbol_body = section_body_after(text, "符号") + "\n" + section_body_after(text, "术语")
    pitfall_body = (
        section_body_after(text, "最容易混")
        or section_body_after(text, "Common Pitfalls")
        or section_body_after(text, "易错点")
    )
    formula_body = section_body_after(text, "最少必须记住的公式") or section_body_after(text, "本篇最少")
    decision_body = section_body_after(text, "方法选择") or section_body_after(text, "决策")
    if "├" in text and not decision_body:
        idx = text.find("├")
        decision_body = text[idx : idx + 160]
    decision_ok = (("├" in text) or ("方法选择" in text) or ("决策" in text)) and has_substance(
        decision_body, min_chars=6
    )
    badge_ok = ("考试频率" in text and has_substance(section_body_after(text, "元信息") or text.split("考试频率", 1)[-1][:200], min_chars=6)) or (
        "> **" in text and "难度" in text and "{{" not in text.split("考试频率", 1)[-1][:80]
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
            "pass": example_count >= 2,
            "issues": []
            if example_count >= 2
            else [f"need >=2 filled worked examples with method refs, found {example_count}"],
        },
        "self_tests": {
            "pass": self_test_count >= 2,
            "issues": []
            if self_test_count >= 2
            else [f"need >=2 filled self-tests with answers, found {self_test_count}"],
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
            "pass": (("最容易混" in text) or ("Common Pitfalls" in text) or ("易错点" in text))
            and has_substance(pitfall_body, min_chars=8),
            "issues": []
            if (
                (("最容易混" in text) or ("Common Pitfalls" in text) or ("易错点" in text))
                and has_substance(pitfall_body, min_chars=8)
            )
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
            "pass": method_ref_count >= 2,
            "issues": []
            if method_ref_count >= 2
            else [f"need >=2 【方法引用】entries with content, found {method_ref_count}"],
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
    }
    failed = [name for name, payload in checks.items() if not payload["pass"]]
    verdict = "pass" if not failed else "needs-revision"
    return {
        "file": path_label,
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
        "verdict": verdict,
        "checks": checks,
        "failed_checks": failed,
    }
