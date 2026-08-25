#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


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
            f"source_file: {yaml_string(source_file)}",
            f"import_method: {import_method}",
            f"repair_status: {repair_status}",
            "verify_status: unverified",
            f"derived_from_import: {yaml_string(derived_from_import)}",
            "---",
            "",
        ]
    )


def load_pdfplumber():
    try:
        import pdfplumber
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency 'pdfplumber'. Install the packages from requirements.txt before running this script."
        ) from exc
    return pdfplumber


def run_repair(input_path: Path, output_path: Path) -> dict[str, object]:
    script_path = Path(__file__).with_name("repair_markdown_import.py")
    summary_path = output_path.with_name(f"{output_path.stem}-repair-summary.md")
    command = [
        sys.executable,
        str(script_path),
        str(input_path),
        "--output",
        str(output_path),
        "--summary-path",
        str(summary_path),
        "--derived-from",
        str(input_path),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(completed.stdout)
    payload["summary_path"] = str(summary_path)
    return payload


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

    pdfplumber = load_pdfplumber()

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
            image_count = len(page.images)
            image_lines: list[str] = []
            if image_count:
                image_lines.extend(
                    [
                        f"- Image placeholders: {image_count} image(s) detected on this page.",
                        *[f"- [Image {index} placeholder retained from source PDF]" for index in range(1, image_count + 1)],
                        "",
                    ]
                )
            body_lines.extend(
                [
                    f"## Page {page_number}",
                    "",
                    *image_lines,
                    text.strip() if text.strip() else "[No extractable text found on this page.]",
                    "",
                ]
            )

    raw_output_path = output_path
    final_output_path = output_path
    result: dict[str, object] = {"mode": mode}

    if mode == "mineru-style":
        if output_path.parent.name == "raw":
            final_output_path = output_path.parent.parent / "repaired" / output_path.name
        elif output_path.parent.name != "repaired":
            raw_output_path = output_path.with_name(f"{output_path.stem}.raw{output_path.suffix}")
        if final_output_path == raw_output_path:
            raw_output_path = final_output_path.with_name(f"{final_output_path.stem}.raw{final_output_path.suffix}")
        raw_output_path.parent.mkdir(parents=True, exist_ok=True)
        final_output_path.parent.mkdir(parents=True, exist_ok=True)
        raw_output_path.write_text("\n".join(body_lines), encoding="utf-8", newline="\n")
        repair_payload = run_repair(raw_output_path, final_output_path)
        result.update(
            {
                "raw_output": str(raw_output_path),
                "output": str(final_output_path),
                "repair_summary": repair_payload["summary_path"],
                "repairs": repair_payload["repairs"],
            }
        )
    else:
        final_output_path.write_text("\n".join(body_lines), encoding="utf-8", newline="\n")
        result["output"] = str(final_output_path)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
