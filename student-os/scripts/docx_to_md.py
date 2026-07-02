#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from docx import Document


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a DOCX file into a markdown reference draft.")
    parser.add_argument("docx", help="Path to the DOCX file")
    parser.add_argument("--output", required=True, help="Output markdown path")
    args = parser.parse_args()

    docx_path = Path(args.docx).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document(str(docx_path))
    lines = [
        "---",
        "type: imported-reference",
        "course:",
        "status: active",
        "created:",
        "updated:",
        "tags: [import, reference]",
        f"source_file: {docx_path}",
        "import_method: docx-to-md",
        "repair_status:",
        "derived_from_import:",
        "---",
        "",
        f"# Imported Reference - {docx_path.stem}",
        "",
        "## Source",
        "",
        f"- Source file: {docx_path}",
        "- Import method: docx-to-md",
        "",
        "## Imported Content",
        "",
    ]

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            lines.extend([text, ""])

    for table_index, table in enumerate(doc.tables, start=1):
        lines.extend([f"## Table {table_index}", ""])
        rows = [[cell.text.strip().replace("\n", " ") for cell in row.cells] for row in table.rows]
        if rows:
            header = rows[0]
            lines.append("| " + " | ".join(header) + " |")
            lines.append("| " + " | ".join(["---"] * len(header)) + " |")
            for row in rows[1:]:
                lines.append("| " + " | ".join(row) + " |")
            lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"output": str(output_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
