#!/usr/bin/env python3
"""Extract a version section from CHANGELOG.md for GitHub Releases."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHANGELOG = ROOT / "CHANGELOG.md"
VERSION_HEADING_RE = re.compile(r"^## \[([^\]]+)\](?:\s+-\s+.+)?\s*$")


def normalize_version(raw: str) -> str:
    text = raw.strip()
    if text.lower().startswith("v") and len(text) > 1 and text[1].isdigit():
        return text[1:]
    return text


def extract_release_notes(changelog_text: str, version: str) -> str:
    normalized = normalize_version(version)
    if normalized.lower() == "unreleased":
        raise ValueError(
            "Refusing to extract [Unreleased] as release notes. "
            "Promote it to a dated ## [x.y.z] section first."
        )

    lines = changelog_text.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        match = VERSION_HEADING_RE.match(line)
        if not match:
            continue
        heading_version = match.group(1).strip()
        if heading_version.lower() == "unreleased":
            continue
        if normalize_version(heading_version) == normalized:
            start = index + 1
            break

    if start is None:
        raise ValueError(
            f"No CHANGELOG section found for version {normalized!r}. "
            f"Expected a heading like '## [{normalized}] - YYYY-MM-DD'."
        )

    end = len(lines)
    for index in range(start, len(lines)):
        match = VERSION_HEADING_RE.match(lines[index])
        if match:
            end = index
            break

    body = "\n".join(lines[start:end]).strip()
    if not body:
        raise ValueError(f"CHANGELOG section for version {normalized!r} is empty.")
    return body + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract release notes for a version from CHANGELOG.md."
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Version to extract, with or without a leading 'v' (e.g. 0.7.0 or v0.7.0).",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to write the extracted release notes markdown.",
    )
    parser.add_argument(
        "--changelog",
        type=Path,
        default=DEFAULT_CHANGELOG,
        help=f"Path to CHANGELOG.md (default: {DEFAULT_CHANGELOG}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    changelog_path: Path = args.changelog

    if not changelog_path.is_file():
        print(f"error: changelog not found: {changelog_path}", file=sys.stderr)
        return 1

    try:
        text = changelog_path.read_text(encoding="utf-8")
        notes = extract_release_notes(text, args.version)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: failed to read changelog: {exc}", file=sys.stderr)
        return 1

    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(notes, encoding="utf-8", newline="\n")
    except OSError as exc:
        print(f"error: failed to write output: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote release notes for {normalize_version(args.version)} to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
