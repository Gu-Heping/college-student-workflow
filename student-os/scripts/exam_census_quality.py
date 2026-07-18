#!/usr/bin/env python3
"""Shared quality contracts for exam-census Phase A–E."""
from __future__ import annotations

import re
from typing import Any

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

QUALITY_CHECK_LABELS = {
    "badge": "有 badge / 元信息区（频率/分值/难度/来源）",
    "quick_lookup": "有「一眼先记住」速查表",
    "symbols": "有术语/符号解释",
    "pitfalls": "有最容易混的 N 件事",
    "decision_tree": "有方法选择流程/决策树",
    "formulas": "有最少必须记住的公式",
    "worked_examples": "有 2 道以上例题（含方法引用）",
    "self_tests": "有 2 道以上自测题",
    "entry_layer": "零基础入口四问齐全",
    "required_sections": "必含区块齐全",
}


def extract_headings(text: str) -> list[str]:
    headings: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if match:
            headings.append(match.group(1).strip())
    return headings


def heading_blob(text: str) -> str:
    return "\n".join(extract_headings(text))


def missing_required_sections(text: str) -> list[str]:
    blob = heading_blob(text) + "\n" + text
    missing: list[str] = []
    for label in REQUIRED_SECTION_HEADINGS:
        if label not in blob:
            missing.append(label)
    return missing


def missing_entry_layer(text: str) -> list[str]:
    missing: list[str] = []
    for marker in ENTRY_LAYER_MARKERS:
        if marker not in text:
            missing.append(marker)
    return missing


def count_examples(text: str) -> int:
    return len(re.findall(r"(?m)^###\s*例题", text)) + len(re.findall(r"(?m)^###\s*Example", text, re.I))


def count_self_tests(text: str) -> int:
    return len(re.findall(r"(?m)^###\s*自测", text)) + len(re.findall(r"(?m)^###\s*Self[- ]?test", text, re.I))


def structural_review(path_label: str, text: str) -> dict[str, Any]:
    missing_sections = missing_required_sections(text)
    missing_entry = missing_entry_layer(text)
    example_count = count_examples(text)
    self_test_count = count_self_tests(text)
    checks = {
        "required_sections": {
            "pass": not missing_sections,
            "issues": [f"missing section: {item}" for item in missing_sections],
        },
        "entry_layer": {
            "pass": not missing_entry,
            "issues": [f"missing entry marker: {item}" for item in missing_entry],
        },
        "worked_examples": {
            "pass": example_count >= 2,
            "issues": [] if example_count >= 2 else [f"need >=2 worked examples, found {example_count}"],
        },
        "self_tests": {
            "pass": self_test_count >= 2,
            "issues": [] if self_test_count >= 2 else [f"need >=2 self-tests, found {self_test_count}"],
        },
        "badge": {
            "pass": ("考试频率" in text) or ("元信息" in text) or ("> **" in text and "难度" in text),
            "issues": [] if (("考试频率" in text) or ("> **" in text and "难度" in text)) else ["missing badge block"],
        },
        "quick_lookup": {
            "pass": "一眼先记住" in text,
            "issues": [] if "一眼先记住" in text else ["missing 一眼先记住 table"],
        },
        "symbols": {
            "pass": ("符号" in text) or ("术语" in text),
            "issues": [] if (("符号" in text) or ("术语" in text)) else ["missing symbol/term table"],
        },
        "pitfalls": {
            "pass": ("最容易混" in text) or ("Common Pitfalls" in text),
            "issues": [] if (("最容易混" in text) or ("Common Pitfalls" in text)) else ["missing pitfalls block"],
        },
        "decision_tree": {
            "pass": ("方法选择" in text) or ("决策" in text) or ("├" in text),
            "issues": [] if (("方法选择" in text) or ("决策" in text) or ("├" in text)) else ["missing decision tree"],
        },
        "formulas": {
            "pass": ("最少必须记住的公式" in text) or ("本篇最少" in text),
            "issues": []
            if (("最少必须记住的公式" in text) or ("本篇最少" in text))
            else ["missing must-remember formulas"],
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
