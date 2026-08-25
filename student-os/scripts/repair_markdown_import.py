#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from import_governance import diagnose_import_risks, is_verified, mark_auto_repaired, risk_summary_lines


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


# MinerU v1 Agent tends to emit these LaTeX/OCR artefacts on legacy CJK PDFs.
# We conservatively unwrap or remove the safe ones and report the rest.


def _is_mineru_agent_v1(text: str) -> bool:
    """Return True if the markdown frontmatter says this came from MinerU v1 Agent."""
    match = re.search(r"^import_method:\s*(.+)$", text, re.MULTILINE)
    if match:
        return match.group(1).strip() == "mineru-agent-v1"
    return False


def _clean_dot_noise(text: str) -> tuple[str, int]:
    """Unwrap \\dot{...} when it wraps a single digit, operator, or Greek command.

    Real math accents like ``\\dot{x}`` (time derivative) are preserved.
    """
    simple = re.compile(r"[0-9=+\-<>]")
    greek = (
        "lambda", "alpha", "beta", "gamma", "delta", "epsilon", "theta",
        "Lambda", "Gamma", "Delta", "Alpha", "Beta",
    )
    pattern = re.compile(r"\\dot\s*\{((?:[^{}]|\{[^{}]*\})*?)\}")
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        inner = match.group(1).strip().lstrip("\\")
        if simple.fullmatch(inner) or inner in greek:
            count += 1
            return match.group(1).strip()
        return match.group(0)

    return pattern.sub(repl, text), count


def _clean_mathrm_noise(text: str) -> tuple[str, int]:
    """Remove \\mathrm{...} when it only carries whitespace, tildes, or \\tiny markup."""
    pattern = re.compile(r"\\mathrm\s*\{((?:[^{}]|\{[^{}]*\})*?)\}")
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        inner = match.group(1)
        cleaned = re.sub(r"\\tiny|\s|~", "", inner)
        if cleaned == "":
            count += 1
            return ""
        # Punctuation-only residue like "~.~" -> "."
        if re.fullmatch(r"[.,;:!?\\-]+", cleaned):
            count += 1
            return cleaned
        return match.group(0)

    return pattern.sub(repl, text), count


def _clean_empty_overset_stackrel(text: str) -> tuple[str, int]:
    """Simplify \\overset/\\stackrel with empty or dot-only decorations."""
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        decoration = match.group(1).strip()
        base = match.group(2).strip()
        if base == "":
            count += 1
            return decoration
        if decoration == "" or decoration == r"\cdot" or decoration == r"\cdot ":
            count += 1
            return base
        return match.group(0)

    for cmd in ("overset", "stackrel"):
        text = re.sub(rf"\\{cmd}\s*\{{((?:[^{{}}]|\{{[^{{}}]*\}})*?)\}}\s*\{{((?:[^{{}}]|\{{[^{{}}]*\}})*?)\}}", repl, text)
    return text, count


def _clean_texttt_garbled(text: str) -> tuple[str, int]:
    """Replace MinerU's garbled Chinese placeholders with a visible placeholder."""
    count = 0

    def repl(_match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return "□"

    text = re.sub(r"\\texttt\s*\{\s*\\textbf\s*\{\s*#\s*\}\s*:?\s*\}", repl, text)
    # ``\sharp`` in text mode (outside math) is almost always a mis-read Chinese char.
    text = re.sub(r"(?<!\\)\\sharp(?!\w)", repl, text)
    return text, count


def _collapse_isolated_dollar_fragments(text: str) -> tuple[str, int]:
    """Collapse runs of isolated single-line $$...$$ blocks that only contain fragments."""
    fragment_line = re.compile(r"^\$\$\s*(.+?)\s*\$\$")
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    run: list[str] = []
    blank_buffer: list[str] = []
    count = 0

    def flush_run() -> None:
        nonlocal run, count
        if len(run) >= 3:
            contents = " ".join(
                fragment_line.match(line).group(1).strip() for line in run  # type: ignore[union-attr]
            )
            result.append(f"$${contents}$$\n")
            count += len(run) + len(blank_buffer) - 1
        else:
            result.extend(blank_buffer)
            result.extend(run)
        run.clear()
        blank_buffer.clear()

    for line in lines:
        if fragment_line.match(line):
            run.append(line)
        elif line.strip() == "":
            blank_buffer.append(line)
        else:
            flush_run()
            result.extend(blank_buffer)
            result.append(line)
            blank_buffer.clear()
    flush_run()
    return "".join(result), count


def _score_remaining_noise(text: str) -> dict[str, int]:
    """Count noise patterns that we do not yet auto-fix but want to report."""
    return {
        "binom_fragments": len(re.findall(r"\\binom\b", text)),
        "dot_noise": len(re.findall(r"\\dot\s*\{", text)),
        "sharp_noise": len(re.findall(r"(?<!\\)\\sharp(?!\w)", text)),
        "mathrm_noise": len(re.findall(r"\\mathrm\s*\{[~\s\\tiny]*[.,;:!?]?[~\s\\tiny]*\}", text)),
        "overset_stackrel_noise": len(re.findall(r"\\(?:overset|stackrel)\s*\{\s*\\?\w*\s*\}\s*\{", text)),
        "isolated_dollars": len(re.findall(r"(?m)^\$\$\s*\\?\w+\s*\$$", text)),
    }


def repair_mineru_v1_noise(text: str) -> tuple[str, list[str]]:
    """Targeted cleanup for MinerU v1 Agent OCR/LaTeX noise.

    Returns the repaired text and a list of human-readable summary lines.
    """
    summary: list[str] = []
    original = text

    text, dot_count = _clean_dot_noise(text)
    if dot_count:
        summary.append(f"Removed {dot_count} \\dot{{}} noise wrappers.")

    text, mathrm_count = _clean_mathrm_noise(text)
    if mathrm_count:
        summary.append(f"Removed {mathrm_count} \\mathrm{{}} noise wrappers.")

    text, overset_count = _clean_empty_overset_stackrel(text)
    if overset_count:
        summary.append(f"Simplified {overset_count} empty \\overset{{}}/\\stackrel{{}} wrappers.")

    text, texttt_count = _clean_texttt_garbled(text)
    if texttt_count:
        summary.append(f"Replaced {texttt_count} garbled Chinese placeholder with □.")

    text, dollar_count = _collapse_isolated_dollar_fragments(text)
    if dollar_count:
        summary.append(f"Collapsed {dollar_count} isolated $$ fragments.")

    if text == original and not summary:
        summary.append("No MinerU v1 noise repairs were applied.")

    # Report remaining unfixable noise so users know manual review is needed.
    noise_score = _score_remaining_noise(text)
    total_noise = sum(noise_score.values())
    if total_noise:
        summary.append(
            f"Detected {total_noise} remaining noise signatures "
            f"(\\binom: {noise_score['binom_fragments']}, "
            f"\\dot: {noise_score['dot_noise']}, "
            f"\\sharp: {noise_score['sharp_noise']}, "
            f"\\mathrm: {noise_score['mathrm_noise']}, "
            f"\\overset/\\stackrel: {noise_score['overset_stackrel_noise']}, "
            f"isolated $$: {noise_score['isolated_dollars']}). "
            "Manual review recommended."
        )

    return text, summary


def repair_text(text: str) -> tuple[str, list[str]]:
    summary: list[str] = []
    original = text

    if _is_mineru_agent_v1(text):
        text, mineru_summary = repair_mineru_v1_noise(text)
        summary.extend(mineru_summary)

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
    parser.add_argument(
        "--include-verified",
        action="store_true",
        help="Allow repairing files already marked verify_status: verified.",
    )
    args = parser.parse_args()

    input_path = Path(args.input_md).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    source_text = input_path.read_text(encoding="utf-8")
    if is_verified(source_text) and not args.include_verified:
        payload = {
            "output": str(output_path),
            "repairs": [],
            "risk_items": [],
            "skipped": True,
            "reason": "verify-status-verified",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    repaired, summary = repair_text(source_text)
    risks = diagnose_import_risks(repaired)
    summary.extend(risk_summary_lines(risks))
    repaired = mark_auto_repaired(repaired, needs_review=bool(risks))
    if args.derived_from:
        derived_line = f"derived_from_import: {yaml_string(str(Path(args.derived_from).resolve()))}"
        # Use a callable replacement so Windows paths with JSON \\uXXXX escapes are not
        # reinterpreted as re.sub template escapes (re.error: bad escape \\u).
        repaired = re.sub(r"(?m)^derived_from_import:\s*$", lambda _: derived_line, repaired, count=1)
        repaired = repaired.replace('derived_from_import: ""', derived_line, 1)
    output_path.write_text(repaired, encoding="utf-8", newline="\n")

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
        summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8", newline="\n")

    print(json.dumps({"output": str(output_path), "repairs": summary, "risk_items": risks}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
