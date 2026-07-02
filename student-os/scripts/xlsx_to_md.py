#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from openpyxl import load_workbook


def stringify(value: object) -> str:
    return "" if value is None else str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert an XLSX workbook into a markdown table summary.")
    parser.add_argument("xlsx", help="Path to the XLSX file")
    parser.add_argument("--output", required=True, help="Output markdown path")
    parser.add_argument("--max-rows", type=int, default=12, help="Maximum rows per sheet to render")
    args = parser.parse_args()

    xlsx_path = Path(args.xlsx).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    wb = load_workbook(filename=str(xlsx_path), data_only=True)
    lines = [
        "---",
        "type: imported-table-summary",
        "course:",
        "status: active",
        "created:",
        "updated:",
        "tags: [import, table]",
        f"source_file: {xlsx_path}",
        "import_method: xlsx-to-md",
        "repair_status:",
        "derived_from_import:",
        "---",
        "",
        f"# Imported Table Summary - {xlsx_path.stem}",
        "",
        "## Source",
        "",
        f"- Source file: {xlsx_path}",
        "- Import method: xlsx-to-md",
        "",
        "## Tables",
        "",
    ]

    for ws in wb.worksheets:
        lines.extend([f"## Sheet: {ws.title}", ""])
        rows = list(ws.iter_rows(values_only=True))[: args.max_rows]
        if not rows:
            lines.extend(["- Empty sheet", ""])
            continue
        header = [stringify(v) for v in rows[0]]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for row in rows[1:]:
            values = [stringify(v) for v in row[: len(header)]]
            lines.append("| " + " | ".join(values) + " |")
        if ws.max_row > args.max_rows:
            lines.extend(["", f"- Truncated after {args.max_rows} rows.", ""])
        else:
            lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"output": str(output_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
