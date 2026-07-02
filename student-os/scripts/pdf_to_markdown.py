#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pdfplumber


def render_frontmatter(source_file: str, import_method: str, repair_status: str, derived_from_import: str) -> str:
    return "\n".join(
        [
            "---",
            "type: pdf-import-note",
            "course:",
            "status: active",
            "created:",
            "updated:",
            "tags: [import, pdf]",
            f"source_file: {source_file}",
            f"import_method: {import_method}",
            f"repair_status: {repair_status}",
            f"derived_from_import: {derived_from_import}",
            "---",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert PDF content into a markdown import draft.")
    parser.add_argument("pdf", help="Path to the PDF file")
    parser.add_argument("--output", required=True, help="Output markdown path")
    parser.add_argument("--mode", choices=["auto", "generic", "mineru-style"], default="auto")
    parser.add_argument("--page-range", help="Optional page range start-end, 1-based")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    page_start = 1
    page_end = None
    if args.page_range and "-" in args.page_range:
        start_s, end_s = args.page_range.split("-", 1)
        page_start = max(1, int(start_s))
        page_end = int(end_s)

    mode = args.mode
    if mode == "auto":
        mode = "mineru-style"

    body_lines = [
        render_frontmatter(str(pdf_path), mode, "raw", ""),
        f"# PDF Import - {pdf_path.stem}",
        "",
        "## Source",
        "",
        f"- Source file: {pdf_path}",
        f"- Import method: {mode}",
        "- Repair status: raw",
        "",
        "## Imported Content",
        "",
    ]

    with pdfplumber.open(str(pdf_path)) as pdf:
        page_total = len(pdf.pages)
        last_page = page_end or page_total
        for page_number in range(page_start, min(last_page, page_total) + 1):
            page = pdf.pages[page_number - 1]
            text = page.extract_text() or ""
            body_lines.extend(
                [
                    f"## Page {page_number}",
                    "",
                    text.strip() if text.strip() else "[No extractable text found on this page.]",
                    "",
                ]
            )

    output_path.write_text("\n".join(body_lines), encoding="utf-8")
    print(json.dumps({"output": str(output_path), "mode": mode}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
