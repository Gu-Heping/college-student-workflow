#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def yaml_string(value: str) -> str:
    return json.dumps(value)


def repair_text(text: str) -> tuple[str, list[str]]:
    summary: list[str] = []
    original = text

    new_text = re.sub(r"(?m)^[ \t]*Page \d+[ \t]*$", "", text)
    if new_text != text:
        summary.append("Removed isolated page labels.")
        text = new_text

    new_text = re.sub(r"(?m)^(#+)(\S)", r"\1 \2", text)
    if new_text != text:
        summary.append("Normalized heading spacing.")
        text = new_text

    new_text = re.sub(r"(?m)^((?:#\s+){2,})(.+)$", lambda m: "#" * m.group(1).count("#") + " " + m.group(2), text)
    if new_text != text:
        summary.append("Collapsed broken heading markers.")
        text = new_text

    new_text = re.sub(r"(?m)^(#+ .+?)\s*(?:\.{2,}\s*\d+|\s{2,}\d+)$", r"\1", text)
    if new_text != text:
        summary.append("Trimmed heading dot leaders or page-number residue.")
        text = new_text

    new_text = re.sub(r"\n{3,}", "\n\n", text)
    if new_text != text:
        summary.append("Collapsed repeated blank lines.")
        text = new_text

    new_text = re.sub(r"(?m)^[-*]\s{2,}", "- ", text)
    if new_text != text:
        summary.append("Normalized bullet spacing.")
        text = new_text

    if text == original and not summary:
        summary.append("No conservative repairs were applied.")
    return text, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Conservatively repair imported markdown from PDF conversion.")
    parser.add_argument("input_md", help="Input markdown path")
    parser.add_argument("--output", required=True, help="Output markdown path")
    parser.add_argument("--summary-path", help="Optional path for a markdown repair summary")
    parser.add_argument("--derived-from", help="Optional raw import path to write into derived_from_import")
    args = parser.parse_args()

    input_path = Path(args.input_md).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    repaired, summary = repair_text(input_path.read_text(encoding="utf-8"))
    repaired = repaired.replace("repair_status: raw", "repair_status: repaired", 1)
    repaired = repaired.replace("- Repair status: raw", "- Repair status: repaired", 1)
    repaired = re.sub(r"(?m)^repair_status:\s*$", "repair_status: repaired", repaired, count=1)
    repaired = re.sub(r"(?m)^- Repair status:\s*$", "- Repair status: repaired", repaired, count=1)
    if args.derived_from:
        derived_line = f"derived_from_import: {yaml_string(str(Path(args.derived_from).resolve()))}"
        repaired = re.sub(r"(?m)^derived_from_import:\s*$", derived_line, repaired, count=1)
        repaired = repaired.replace('derived_from_import: ""', derived_line, 1)
    output_path.write_text(repaired, encoding="utf-8")

    if args.summary_path:
        summary_path = Path(args.summary_path).resolve()
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_lines = [
            "# Repair Summary",
            "",
            f"- Source: {input_path}",
            f"- Output: {output_path}",
            "",
            "## Changes",
            "",
        ]
        summary_lines.extend(f"- {item}" for item in summary)
        summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(json.dumps({"output": str(output_path), "repairs": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
