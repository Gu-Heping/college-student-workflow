#!/usr/bin/env python3
from __future__ import annotations

import os


PDF_SUFFIXES = {".pdf"}
DOCX_SUFFIXES = {".docx"}
PPTX_SUFFIXES = {".pptx"}
XLSX_SUFFIXES = {".xlsx"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
LEGACY_WORD_SUFFIXES = {".doc"}
LEGACY_PPT_SUFFIXES = {".ppt"}
LEGACY_XLS_SUFFIXES = {".xls"}
LEGACY_OFFICE_SUFFIXES = LEGACY_WORD_SUFFIXES | LEGACY_PPT_SUFFIXES | LEGACY_XLS_SUFFIXES
BINARY_INDEX_SUFFIXES = {".bit", ".ms14", ".vhd"}
TEXT_SKIP_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".csv",
    ".json",
    ".md",
    ".py",
    ".rs",
    ".sh",
    ".tex",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
API_SUPPORTED_SUFFIXES = (
    PDF_SUFFIXES
    | DOCX_SUFFIXES
    | PPTX_SUFFIXES
    | XLSX_SUFFIXES
    | IMAGE_SUFFIXES
    | LEGACY_OFFICE_SUFFIXES
)


def _env_positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


MINERU_AGENT_MAX_FILE_BYTES = _env_positive_int("STUDENT_OS_MINERU_AGENT_MAX_FILE_BYTES", 10 * 1024 * 1024)
