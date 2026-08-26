#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from import_governance import repair_status_for_summary_exists


COURSE_MARKERS = {"notes", "homework", "reviews", "labs", "references"}
IMPORT_METHOD_RE = re.compile(r"(?im)^(?:-\s*)?Import method:\s*(\S+)\s*$")
PDF_MD_SUFFIX = ".pdf.md"
RAW_MD_SUFFIX = ".raw.md"


def configure_stdout_utf8() -> None:
    stream = getattr(sys, "stdout", None)
    if stream is None or not hasattr(stream, "reconfigure"):
        return
    if (stream.encoding or "").lower() == "utf-8":
        return
    stream.reconfigure(encoding="utf-8")


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def has_frontmatter(text: str) -> bool:
    normalized = text.lstrip("\ufeff")
    if not normalized.startswith("---"):
        return False
    # Require a second closing --- after the opening line.
    match = re.match(r"^---\r?\n.*?\r?\n---(?:\r?\n|$)", normalized, flags=re.S)
    return match is not None


def display_path(path: Path, root: Path) -> str:
    resolved = path.resolve()
    root_resolved = root.resolve()
    try:
        return resolved.relative_to(root_resolved).as_posix()
    except ValueError:
        try:
            return resolved.relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            return path.name


def infer_course_from_path(path: Path) -> str:
    parts = list(path.parts)
    try:
        idx = parts.index("courses")
    except ValueError:
        return ""
    remaining = parts[idx + 1 :]
    if len(remaining) >= 2 and remaining[1] in COURSE_MARKERS:
        return remaining[0]
    if len(remaining) >= 3 and remaining[2] in COURSE_MARKERS:
        return remaining[1]
    return ""


def infer_source_file(path: Path) -> str:
    name = path.name
    if name.endswith(PDF_MD_SUFFIX):
        return name[: -len(".md")]
    if name.endswith(RAW_MD_SUFFIX):
        # e.g. handout.pdf.raw.md -> handout.pdf when possible
        without_raw = name[: -len(RAW_MD_SUFFIX)]
        if without_raw.endswith(".pdf") or "." in without_raw:
            return without_raw
        return without_raw
    return path.stem


def is_pdf_md(path: Path) -> bool:
    return path.name.lower().endswith(PDF_MD_SUFFIX)


def is_raw_md(path: Path) -> bool:
    return path.name.lower().endswith(RAW_MD_SUFFIX)


def find_repair_summary(path: Path) -> Path | None:
    parent = path.parent
    stem = path.stem  # for foo.pdf.md -> foo.pdf
    candidates = [
        parent / f"{stem}-repair-summary.md",
        parent / f"{path.name}-repair-summary.md",
    ]
    if is_pdf_md(path):
        pdf_stem = path.name[: -len(PDF_MD_SUFFIX)]
        candidates.append(parent / f"{pdf_stem}-repair-summary.md")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def find_raw_sibling(path: Path) -> Path | None:
    if not is_pdf_md(path):
        return None
    # foo.pdf.md -> foo.pdf.raw.md
    candidate = path.with_name(f"{path.stem}.raw.md")
    if candidate.is_file():
        return candidate
    return None


def infer_import_method(text: str, path: Path) -> str:
    match = IMPORT_METHOD_RE.search(text)
    if match:
        value = match.group(1).strip().strip("`\"'")
        if value:
            return value
    if find_raw_sibling(path) is not None or find_repair_summary(path) is not None:
        return "materials-convert"
    return "unknown"


def note_type_and_tags(path: Path) -> tuple[str, str]:
    if is_pdf_md(path):
        return "pdf-import-note", "[import, pdf]"
    return "imported-reference", "[import, reference]"


def build_frontmatter(
    path: Path,
    *,
    course: str,
    status: str,
    body: str,
    display_root: Path,
) -> str:
    note_type, tags = note_type_and_tags(path)
    source_file = infer_source_file(path)
    import_method = infer_import_method(body, path)
    repair_status = repair_status_for_summary_exists(find_repair_summary(path))
    derived = ""
    raw_sibling = find_raw_sibling(path)
    if raw_sibling is not None:
        derived = display_path(raw_sibling, display_root)
    course_value = course or infer_course_from_path(path)
    lines = [
        "---",
        f"type: {note_type}",
        f"course: {yaml_string(course_value) if course_value else ''}",
        f"status: {status}",
        "created:",
        "updated:",
        f"tags: {tags}",
        f"source_file: {yaml_string(source_file)}",
        f"import_method: {import_method}",
        f"repair_status: {repair_status}",
        "verify_status: unverified",
        f"derived_from_import: {yaml_string(derived) if derived else ''}",
        "---",
        "",
    ]
    return "\n".join(lines)


def collect_targets(root: Path, *, include_raw: bool) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        raise FileNotFoundError(f"Path not found: {root}")
    targets: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        # Skip binaries / non-text by suffix only; we only touch markdown sidecars.
        lower = path.name.lower()
        if lower.endswith(PDF_MD_SUFFIX):
            targets.append(path)
            continue
        if include_raw and lower.endswith(RAW_MD_SUFFIX):
            targets.append(path)
    return targets


def process_file(
    path: Path,
    *,
    apply: bool,
    course: str,
    status: str,
    display_root: Path,
) -> dict[str, object]:
    rel = display_path(path, display_root)
    result: dict[str, object] = {"path": rel, "action": "skip", "reason": ""}
    try:
        if not path.is_file():
            result["action"] = "error"
            result["reason"] = "not-a-file"
            return result
        # Reject obviously non-text names (safety); only .md sidecars should reach here.
        if path.suffix.lower() != ".md":
            result["action"] = "skipped_unsupported"
            result["reason"] = "unsupported-suffix"
            return result
        text = path.read_text(encoding="utf-8")
        if has_frontmatter(text):
            result["action"] = "skipped_existing_frontmatter"
            result["reason"] = "has-frontmatter"
            return result
        frontmatter = build_frontmatter(
            path,
            course=course,
            status=status,
            body=text,
            display_root=display_root,
        )
        if apply:
            # Preserve body text; only prepend frontmatter (UTF-8, LF newlines).
            new_text = frontmatter + text.lstrip("\ufeff")
            path.write_text(new_text, encoding="utf-8", newline="\n")
            result["action"] = "updated"
        else:
            result["action"] = "would_update"
        result["source_file"] = infer_source_file(path)
        result["repair_status"] = repair_status_for_summary_exists(find_repair_summary(path))
        result["verify_status"] = "unverified"
        return result
    except UnicodeDecodeError as exc:
        result["action"] = "error"
        result["reason"] = f"utf8-decode-failed: {exc}"
        return result
    except OSError as exc:
        result["action"] = "error"
        result["reason"] = str(exc)
        return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Batch-prepend YAML frontmatter for .pdf.md sidecars that lack it. "
            "Default is dry-run; pass --apply to write. Never overwrites existing frontmatter."
        )
    )
    parser.add_argument("path", help="File or directory to scan")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview planned updates without writing (default when --apply is omitted).",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Write missing frontmatter. Without this flag, files are not modified.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=True,
        help="Emit JSON summary (default).",
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Also process *.raw.md files (type: imported-reference).",
    )
    parser.add_argument("--course", default="", help="Optional course name to write into metadata")
    parser.add_argument("--status", default="active", help="Frontmatter status (default: active)")
    return parser.parse_args(argv)


def build_summary(results: list[dict[str, object]]) -> dict[str, object]:
    would_update = [str(item["path"]) for item in results if item["action"] == "would_update"]
    updated = [str(item["path"]) for item in results if item["action"] == "updated"]
    skipped_existing = [
        str(item["path"]) for item in results if item["action"] == "skipped_existing_frontmatter"
    ]
    skipped_unsupported = [
        str(item["path"]) for item in results if item["action"] == "skipped_unsupported"
    ]
    errors = [
        {"path": str(item["path"]), "reason": str(item.get("reason", ""))}
        for item in results
        if item["action"] == "error"
    ]
    return {
        "scanned": len(results),
        "would_update": would_update,
        "updated": updated,
        "skipped_existing_frontmatter": skipped_existing,
        "skipped_unsupported": skipped_unsupported,
        "errors": errors,
        "apply": any(item["action"] == "updated" for item in results),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    configure_stdout_utf8()
    args = parse_args(argv)
    target = Path(args.path)
    if not target.exists():
        raise SystemExit(f"Path not found: {target}")

    display_root = target if target.is_dir() else target.parent
    apply = bool(args.apply)
    try:
        files = collect_targets(target, include_raw=args.include_raw)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    results: list[dict[str, object]] = []
    for path in files:
        if target.is_file() and not (is_pdf_md(path) or (args.include_raw and is_raw_md(path))):
            results.append(
                {
                    "path": display_path(path, display_root),
                    "action": "skipped_unsupported",
                    "reason": "unsupported-sidecar",
                }
            )
            continue
        results.append(
            process_file(
                path,
                apply=apply,
                course=args.course or "",
                status=args.status,
                display_root=display_root,
            )
        )

    summary = build_summary(results)
    summary["apply"] = apply
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
