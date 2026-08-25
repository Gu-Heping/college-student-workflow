#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


AUTO_REPAIRED = "auto-repaired"
LEGACY_REPAIRED = "repaired"
UNVERIFIED = "unverified"
VERIFIED = "verified"
NEEDS_HUMAN_REVIEW = "needs-human-review"


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def read_frontmatter(text: str) -> tuple[dict[str, str], int, int] | None:
    normalized = text.lstrip("\ufeff")
    offset = len(text) - len(normalized)
    match = re.match(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", normalized, flags=re.S)
    if not match:
        return None
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.lstrip() != line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("\"'")
    return data, offset, offset + match.end()


def frontmatter_value(text: str, key: str) -> str:
    parsed = read_frontmatter(text)
    if parsed is None:
        return ""
    data, _start, _end = parsed
    return data.get(key, "").strip()


def verify_status(text: str) -> str:
    return frontmatter_value(text, "verify_status").lower()


def is_verified(text: str) -> bool:
    return verify_status(text) == VERIFIED


def ensure_field(text: str, key: str, value: str) -> str:
    replacement = f"{key}: {value}"
    pattern = re.compile(rf"(?m)^{re.escape(key)}:\s*.*$")
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    parsed = read_frontmatter(text)
    if parsed is None:
        return text
    _data, _start, end = parsed
    insert_at = text.rfind("---", 0, end)
    if insert_at == -1:
        return text
    return text[:insert_at] + replacement + "\n" + text[insert_at:]


def mark_auto_repaired(text: str, *, needs_review: bool) -> str:
    text = re.sub(r"(?m)^repair_status:\s*(?:raw|repaired)?\s*$", f"repair_status: {AUTO_REPAIRED}", text, count=1)
    text = re.sub(r"(?m)^- Repair status:\s*(?:raw|repaired)?\s*$", f"- Repair status: {AUTO_REPAIRED}", text, count=1)
    text = ensure_field(text, "verify_status", UNVERIFIED)
    if needs_review:
        text = ensure_field(text, "repair_risk", NEEDS_HUMAN_REVIEW)
    return text


def diagnose_import_risks(text: str) -> list[dict[str, object]]:
    risks: list[dict[str, object]] = []

    checks: list[tuple[str, str, int]] = [
        ("latex-nonumber", r"\\nonumber\b", 0),
        ("latex-binom-fragment", r"\\binom\b", 0),
        ("mojibake-replacement-char", "�", 0),
        ("unicode-escape", r"\\u[0-9a-fA-F]{4}", 0),
        ("question-heading-promoted", r"(?m)^##\s+[一二三四五六七八九十]+[\.、]", 0),
    ]
    for code, pattern, flags in checks:
        count = len(re.findall(pattern, text, flags))
        if count:
            risks.append({"code": code, "count": count})

    left_count = len(re.findall(r"\\left\b", text))
    right_count = len(re.findall(r"\\right\b", text))
    if left_count != right_count:
        risks.append({"code": "latex-left-right-unbalanced", "left": left_count, "right": right_count})

    inline_dollars = len(re.findall(r"(?<!\\)\$", text))
    if inline_dollars % 2 == 1:
        risks.append({"code": "math-dollar-unbalanced", "count": inline_dollars})

    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    if len(text) > 2000 and cjk_count == 0 and re.search(r"import_method:\s*(?:mineru|pdf|pymupdf)", text):
        risks.append({"code": "low-cjk-density", "cjk": cjk_count})

    return risks


def risk_summary_lines(risks: list[dict[str, object]]) -> list[str]:
    if not risks:
        return []
    lines = ["Manual review risk items:"]
    for risk in risks:
        detail = ", ".join(f"{key}={value}" for key, value in risk.items() if key != "code")
        lines.append(f"{risk['code']}" + (f" ({detail})" if detail else ""))
    return lines


def repair_status_for_summary_exists(summary_path: Path | None) -> str:
    return AUTO_REPAIRED if summary_path is not None else ""
