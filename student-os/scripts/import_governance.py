#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import string
from pathlib import Path


AUTO_REPAIRED = "auto-repaired"
LEGACY_REPAIRED = "repaired"
UNVERIFIED = "unverified"
VERIFIED = "verified"
NEEDS_HUMAN_REVIEW = "needs-human-review"


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] in {"'", '"'}:
        quote = value[0]
        end = value.find(quote, 1)
        if end != -1:
            return value[1:end]
    return re.split(r"\s+#", value, maxsplit=1)[0].strip().strip("\"'")


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
        data[key.strip()] = yaml_scalar(value)
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
    parsed = read_frontmatter(text)
    if parsed is None:
        prefix = f"---\n{replacement}\n---\n"
        if text.startswith("\ufeff"):
            return "\ufeff" + prefix + text.lstrip("\ufeff")
        return prefix + ("\n" if text and not text.startswith("\n") else "") + text
    _data, start, end = parsed
    insert_at = text.rfind("---", start, end)
    if insert_at == -1:
        return text
    frontmatter = text[start:insert_at]
    pattern = re.compile(rf"(?m)^{re.escape(key)}:[^\S\r\n]*[^\r\n]*$")
    if pattern.search(frontmatter):
        return text[:start] + pattern.sub(replacement, frontmatter, count=1) + text[insert_at:]
    insert_at = text.rfind("---", 0, end)
    if insert_at == -1:
        return text
    return text[:insert_at] + replacement + "\n" + text[insert_at:]


def remove_field(text: str, key: str) -> str:
    parsed = read_frontmatter(text)
    if parsed is None:
        return text
    _data, start, end = parsed
    insert_at = text.rfind("---", start, end)
    if insert_at == -1:
        return text
    frontmatter = text[start:insert_at]
    pattern = re.compile(rf"(?m)^{re.escape(key)}:[^\S\r\n]*[^\r\n]*(?:\r?\n)?")
    return text[:start] + pattern.sub("", frontmatter, count=1) + text[insert_at:]


def mark_auto_repaired(text: str, *, needs_review: bool) -> str:
    text = ensure_field(text, "repair_status", AUTO_REPAIRED)
    parsed = read_frontmatter(text)
    if parsed is not None:
        _data, _start, end = parsed
        next_section = re.search(r"(?m)^##\s+", text[end:])
        managed_end = end + next_section.start() if next_section else len(text)
        managed_prefix = text[end:managed_end]
        managed_prefix = re.sub(
            r"(?m)^- Repair status:[^\S\r\n]*(?:raw|repaired)?[^\S\r\n]*$",
            f"- Repair status: {AUTO_REPAIRED}",
            managed_prefix,
            count=1,
        )
        text = text[:end] + managed_prefix + text[managed_end:]
    text = ensure_field(text, "verify_status", UNVERIFIED)
    if needs_review:
        text = ensure_field(text, "repair_risk", NEEDS_HUMAN_REVIEW)
    elif frontmatter_value(text, "repair_risk") == NEEDS_HUMAN_REVIEW:
        text = remove_field(text, "repair_risk")
    return text


def expects_cjk_text(text: str) -> bool:
    for key in ("language", "source_language", "document_language", "ocr_language", "import_language"):
        value = frontmatter_value(text, key).lower()
        if value in {"ch", "cn", "zh", "zh-cn", "zh_hans", "zh-hans", "cjk", "中文"}:
            return True
    return False


def _brace_group_span(text: str, start: int) -> tuple[int, int] | None:
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{" and (index == 0 or text[index - 1] != "\\"):
            depth += 1
        elif char == "}" and (index == 0 or text[index - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return start, index + 1
    return None


def count_malformed_binom(text: str) -> int:
    count = 0
    for match in re.finditer(r"\\binom\b", text):
        cursor = match.end()
        ok = True
        for _ in range(2):
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
            span = _brace_group_span(text, cursor)
            if span is None:
                ok = False
                break
            body = text[span[0] + 1 : span[1] - 1].strip()
            if not body:
                ok = False
                break
            cursor = span[1]
        if not ok:
            count += 1
    return count


def _strip_markdown_code(text: str) -> str:
    lines = text.splitlines(keepends=True)
    kept: list[str] = []
    fence_char = ""
    fence_len = 0
    for line in lines:
        if fence_char:
            close = re.match(r"^[ \t]{0,3}([`~]{3,})[ \t]*$", line.rstrip("\r\n"))
            if close and close.group(1)[0] == fence_char and len(close.group(1)) >= fence_len:
                fence_char = ""
                fence_len = 0
            continue
        open_match = re.match(r"^[ \t]{0,3}([`~]{3,})", line)
        if open_match:
            fence = open_match.group(1)
            fence_char = fence[0]
            fence_len = len(fence)
            continue
        kept.append(line)
    text = "".join(kept)
    return re.sub(r"(?s)(`+).*?\1", "", text)


def _has_later_unescaped_dollar(text: str, start: int) -> bool:
    for index in range(start, len(text)):
        if text[index] == "$" and (index == 0 or text[index - 1] != "\\"):
            return True
        if text[index] == "\n":
            return False
    return False


def _looks_like_currency_before_next_dollar(span: str) -> bool:
    return bool(re.match(r"^\d[\d,]*(?:\.\d+)?(?:[.,;:]\s*|\s+)$", span))


def _looks_like_standalone_currency_after_dollar(text: str, start: int) -> bool:
    line = text[start:].split("\n", 1)[0]
    return bool(re.match(r"^\d[\d,]*(?:\.\d+)?(?:[.,;:]|$|\s)", line))


def count_likely_math_dollars(text: str) -> int:
    text = _strip_markdown_code(text)
    count = 0
    punctuation = set(string.punctuation) - {"$"}
    dollar_indexes = [
        index
        for index, char in enumerate(text)
        if char == "$" and (index == 0 or text[index - 1] != "\\")
    ]
    paired_indexes: set[int] = set()
    for offset, index in enumerate(dollar_indexes[:-1]):
        if index in paired_indexes:
            continue
        next_index = dollar_indexes[offset + 1]
        if "\n" in text[index + 1 : next_index]:
            continue
        span = text[index + 1 : next_index]
        if _looks_like_currency_before_next_dollar(span) or re.match(r"^\d[\d,]*(?:\.\d+)?\s+[A-Za-z]", span):
            continue
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if next_char and not next_char.isspace() and (next_char not in punctuation or next_char == "\\"):
            paired_indexes.add(index)
            paired_indexes.add(next_index)
            count += 2

    for index, char in enumerate(text):
        if char != "$" or (index > 0 and text[index - 1] == "\\"):
            continue
        if index in paired_indexes:
            continue
        previous_char = text[index - 1] if index > 0 else ""
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if (
            next_char.isdigit()
            and not _has_later_unescaped_dollar(text, index + 1)
            and _looks_like_standalone_currency_after_dollar(text, index + 1)
        ):
            continue
        if next_char.isdigit() and _looks_like_standalone_currency_after_dollar(text, index + 1):
            continue
        if next_char and not next_char.isspace() and (next_char not in punctuation or next_char == "\\"):
            count += 1
        elif previous_char and not previous_char.isspace():
            count += 1
    return count


def count_orphan_latex_nonumber(text: str) -> int:
    count = 0
    for line in _strip_markdown_code(text).splitlines():
        stripped = line.strip()
        if not re.search(r"\\nonumber\b", stripped):
            continue
        without_token = re.sub(r"\\nonumber\b", "", stripped).strip()
        without_token = without_token.strip(r"\;,. ")
        if not without_token:
            count += 1
    return count


def imported_content_text(text: str) -> str:
    marker = re.search(r"(?m)^## Imported Content\s*$", text)
    if marker:
        return text[marker.end() :]
    parsed = read_frontmatter(text)
    if parsed is None:
        return text
    _data, _start, end = parsed
    return text[end:]


def diagnose_import_risks(text: str) -> list[dict[str, object]]:
    risks: list[dict[str, object]] = []
    diagnostic_text = _strip_markdown_code(text)

    checks: list[tuple[str, str, int]] = [
        ("mojibake-replacement-char", "�", 0),
        ("unicode-escape", r"\\u[0-9a-fA-F]{4}", 0),
    ]
    for code, pattern, flags in checks:
        count = len(re.findall(pattern, text, flags))
        if count:
            risks.append({"code": code, "count": count})

    nonumber_count = count_orphan_latex_nonumber(diagnostic_text)
    if nonumber_count:
        risks.append({"code": "latex-nonumber", "count": nonumber_count})

    binom_count = count_malformed_binom(diagnostic_text)
    if binom_count:
        risks.append({"code": "latex-binom-fragment", "count": binom_count})

    left_count = len(re.findall(r"\\left\b", diagnostic_text))
    right_count = len(re.findall(r"\\right\b", diagnostic_text))
    if left_count != right_count:
        risks.append({"code": "latex-left-right-unbalanced", "left": left_count, "right": right_count})

    inline_dollars = count_likely_math_dollars(text)
    if inline_dollars % 2 == 1:
        risks.append({"code": "math-dollar-unbalanced", "count": inline_dollars})

    imported_body = imported_content_text(text)
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", imported_body))
    if (
        expects_cjk_text(text)
        and len(imported_body) > 2000
        and cjk_count == 0
        and re.search(r"import_method:\s*(?:mineru|pdf|pymupdf)", text)
    ):
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
