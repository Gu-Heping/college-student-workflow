#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import math
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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


@dataclass(frozen=True)
class ConversionPlan:
    kind: str
    import_method: str


@dataclass
class ConversionContext:
    method: str
    course: str | None
    overwrite: bool
    repair: bool
    repair_only: bool
    api_token: str | None
    api_model: str
    language: str
    ocr: bool | None
    formula: bool | None
    table: bool | None
    pages: str | None
    timeout: int
    auto_split: bool = True
    chunk_size: int = 200
    merge: bool = True
    force_strategy: str | None = None
    ocr_explicit: bool | None = None
    mineru_client: Any | None = None


DEFAULT_PDF_CHUNK_SIZE = 200
MINERU_MAX_PAGES = 200


def _resolve_max_file_bytes() -> int:
    # Allow tests (and advanced users) to lower MinerU's 200MB size cap so the
    # size-driven split path can be exercised without huge fixtures.
    override = os.environ.get("STUDENT_OS_MINERU_MAX_FILE_BYTES")
    if override:
        try:
            value = int(override)
        except ValueError:
            value = 0
        if value > 0:
            return value
    return 200 * 1024 * 1024


MINERU_MAX_FILE_BYTES = _resolve_max_file_bytes()


def yaml_string(value: str) -> str:
    return json.dumps(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-convert course materials into markdown sidecars or mirrored outputs."
    )
    parser.add_argument("source", help="Source file or directory to convert")
    parser.add_argument("--course", help="Optional course name to write into generated metadata")
    parser.add_argument(
        "--output-root",
        help="Optional destination root. When omitted, outputs are written beside the source files as <name>.<ext>.md.",
    )
    parser.add_argument(
        "--pattern",
        action="append",
        help="Optional glob pattern(s) relative to the source root, for example **/*.pdf",
    )
    parser.add_argument(
        "--method",
        choices=["auto", "local", "api"],
        default="auto",
        help=(
            "Conversion strategy. auto probes each file and picks MinerU API, PyMuPDF, pandoc, "
            "or local converters; local/api force a global backend."
        ),
    )
    parser.add_argument(
        "--probe-only",
        action="store_true",
        help="Probe each input and print strategy recommendations as JSON without writing sidecars.",
    )
    parser.add_argument(
        "--force-strategy",
        choices=[
            "ocr",
            "mineru-api",
            "pymupdf",
            "pandoc",
            "python-pptx",
            "xlsx-to-md",
            "docx-to-md",
            "pdf-to-md",
            "image-index",
            "legacy-office-index",
            "binary-index",
        ],
        help="Override automatic probing and force one conversion strategy for every input.",
    )
    repair_group = parser.add_mutually_exclusive_group()
    repair_group.add_argument(
        "--repair",
        action="store_true",
        help="Run conservative markdown repair after conversion for generated markdown outputs.",
    )
    repair_group.add_argument(
        "--repair-only",
        action="store_true",
        help="Only repair existing markdown files instead of converting source documents.",
    )
    parser.add_argument(
        "--api-token",
        help="Optional MinerU precision API token. Defaults to MINERU_TOKEN / MINERU_API_TOKEN from the environment or a skill/cwd .env file.",
    )
    parser.add_argument(
        "--api-model",
        choices=["vlm", "pipeline"],
        default="vlm",
        help="MinerU precision API model for --method api. Official docs recommend vlm for higher fidelity.",
    )
    parser.add_argument("--language", default="ch", help="Document language code forwarded to MinerU when applicable.")
    parser.add_argument("--ocr", dest="ocr", action="store_true", help="Force OCR on when supported by the selected backend.")
    parser.add_argument("--no-ocr", dest="ocr", action="store_false", help="Force OCR off when supported by the selected backend.")
    parser.add_argument("--formula", dest="formula", action="store_true", help="Enable formula recognition for MinerU API runs.")
    parser.add_argument("--no-formula", dest="formula", action="store_false", help="Disable formula recognition for MinerU API runs.")
    parser.add_argument("--table", dest="table", action="store_true", help="Enable table recognition for MinerU API runs.")
    parser.add_argument("--no-table", dest="table", action="store_false", help="Disable table recognition for MinerU API runs.")
    parser.add_argument("--pages", help="Optional PDF page range such as 1-10 or 1-5,8.")
    parser.add_argument("--timeout", type=int, default=300, help="Maximum seconds to wait for MinerU API completion per file.")
    parser.add_argument(
        "--no-auto-split",
        action="store_true",
        help="Disable automatic PDF splitting for MinerU API runs. Oversized PDFs will error instead of being chunked.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_PDF_CHUNK_SIZE,
        help=f"PDF page chunk size for MinerU API auto-split (default {DEFAULT_PDF_CHUNK_SIZE}; MinerU v4 limit is {MINERU_MAX_PAGES}).",
    )
    parser.add_argument(
        "--merge",
        dest="merge",
        action="store_true",
        default=True,
        help="After auto-splitting a PDF, merge chunk markdown into one sidecar (default).",
    )
    parser.add_argument(
        "--no-merge",
        dest="merge",
        action="store_false",
        help="Keep auto-split PDF chunk markdown as separate sidecars instead of merging.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing markdown sidecars instead of skipping them",
    )
    parser.set_defaults(ocr=None, formula=None, table=None)
    return parser.parse_args()


def relpath(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def discover_inputs(source: Path, patterns: list[str] | None) -> tuple[Path, list[Path]]:
    if source.is_file():
        return source.parent, [source]

    root = source
    files = [candidate for candidate in root.rglob("*") if candidate.is_file()]
    if not patterns:
        return root, sorted(files)

    selected: list[Path] = []
    for candidate in files:
        relative = relpath(candidate, root)
        if any(fnmatch.fnmatch(relative, pattern) for pattern in patterns):
            selected.append(candidate)
    return root, sorted(selected)


def is_repair_summary(path: Path) -> bool:
    return path.name.endswith("-repair-summary.md")


def is_repairable_markdown(path: Path) -> bool:
    return path.suffix.lower() == ".md" and not is_repair_summary(path)


def build_output_path(source_file: Path, source_root: Path, output_root: Path | None) -> Path:
    if output_root is None:
        return source_file.with_name(f"{source_file.name}.md")
    relative = source_file.relative_to(source_root)
    return output_root / relative.parent / f"{source_file.name}.md"


def resolve_api_token(cli_token: str | None) -> str | None:
    from token_loader import load_token

    return load_token(cli_token)


def should_resolve_api_token(
    method: str,
    repair_only: bool,
    *,
    probe_only: bool = False,
    force_strategy: str | None = None,
) -> bool:
    # Local-only and repair-only paths never need MinerU credentials; skip .env reads
    # so an unreadable cwd .env cannot abort those workflows.
    if repair_only:
        return False
    if force_strategy in {"ocr", "mineru-api"}:
        return True
    if probe_only:
        return True
    return method in {"auto", "api"}


def choose_local_plan(path: Path) -> ConversionPlan | None:
    suffix = path.suffix.lower()
    if suffix in PDF_SUFFIXES:
        return ConversionPlan(kind="pdf", import_method="pdf-to-md")
    if suffix in DOCX_SUFFIXES:
        return ConversionPlan(kind="docx", import_method="docx-to-md")
    if suffix in PPTX_SUFFIXES:
        return ConversionPlan(kind="pptx", import_method="pptx-to-md")
    if suffix in XLSX_SUFFIXES:
        return ConversionPlan(kind="xlsx", import_method="xlsx-to-md")
    if suffix in IMAGE_SUFFIXES:
        return ConversionPlan(kind="image-index", import_method="image-index")
    if suffix in LEGACY_OFFICE_SUFFIXES:
        return ConversionPlan(kind="legacy-office-index", import_method="legacy-office-index")
    if suffix in BINARY_INDEX_SUFFIXES:
        return ConversionPlan(kind="binary-index", import_method="binary-index")
    if suffix in TEXT_SKIP_SUFFIXES:
        return None
    return ConversionPlan(kind="binary-index", import_method="binary-index")


def choose_method(path: Path, ctx: ConversionContext) -> str:
    suffix = path.suffix.lower()
    if ctx.method == "local":
        return "local"
    if ctx.method == "api":
        if suffix not in API_SUPPORTED_SUFFIXES:
            return "local"
        return "api"
    if ctx.api_token and suffix in API_SUPPORTED_SUFFIXES:
        return "api"
    return "local"


def run_script(script_name: str, *args: str) -> dict[str, Any]:
    script_path = Path(__file__).with_name(script_name)
    completed = subprocess.run(
        [sys.executable, "-B", str(script_path), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


def run_repair(input_path: Path, output_path: Path, *, derived_from: Path | None) -> dict[str, Any]:
    args = [
        "repair_markdown_import.py",
        str(input_path),
        "--output",
        str(output_path),
        "--summary-path",
        str(output_path.with_name(f"{output_path.stem}-repair-summary.md")),
    ]
    if derived_from is not None:
        args.extend(["--derived-from", str(derived_from)])
    payload = run_script(*args)
    payload["summary_path"] = str(output_path.with_name(f"{output_path.stem}-repair-summary.md"))
    return payload


def apply_course_metadata(output_path: Path, course: str | None) -> None:
    if not course:
        return
    text = output_path.read_text(encoding="utf-8")
    updated = text.replace("course:\n", f"course: {yaml_string(course)}\n", 1)
    if updated != text:
        output_path.write_text(updated, encoding="utf-8", newline="\n")


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def output_metadata(source_file: Path) -> tuple[str, str, str, str]:
    suffix = source_file.suffix.lower()
    if suffix in PDF_SUFFIXES:
        return "pdf-import-note", "[import, pdf]", f"# PDF Import - {source_file.stem}", "pdf-import-note"
    if suffix in PPTX_SUFFIXES | LEGACY_PPT_SUFFIXES:
        return "slide-summary", "[import, slides]", f"# Slide Summary - {source_file.stem}", "slide-summary"
    if suffix in XLSX_SUFFIXES | LEGACY_XLS_SUFFIXES:
        return "imported-table-summary", "[import, table]", f"# Imported Table Summary - {source_file.stem}", "imported-table-summary"
    return "imported-reference", "[import, reference]", f"# Imported Reference - {source_file.stem}", "imported-reference"


def wrap_mineru_markdown(
    *,
    source_file: Path,
    markdown_body: str,
    import_method: str,
    course: str | None,
    derived_from_import: str | None = None,
) -> str:
    note_type, tags, title, _ = output_metadata(source_file)
    lines = [
        "---",
        f"type: {note_type}",
        f"course: {yaml_string(course) if course else ''}",
        "status: active",
        "created:",
        "updated:",
        f"tags: {tags}",
        f"source_file: {yaml_string(str(source_file))}",
        f"import_method: {import_method}",
        "repair_status:",
        f"derived_from_import: {yaml_string(derived_from_import) if derived_from_import else ''}",
        "---",
        "",
        title,
        "",
        "## Source",
        "",
        f"- Source file: {source_file}",
        f"- Import method: {import_method}",
        "",
        "## Imported Content",
        "",
        markdown_body.strip(),
        "",
    ]
    return "\n".join(lines)


def write_index_note(
    *,
    source_file: Path,
    output_path: Path,
    import_method: str,
    course: str | None,
    summary_lines: list[str],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = wrap_mineru_markdown(
        source_file=source_file,
        markdown_body="\n".join(summary_lines),
        import_method=import_method,
        course=course,
    )
    write_markdown(output_path, markdown)


def repair_generated_markdown(output_path: Path, *, in_place: bool = False) -> dict[str, Any]:
    if in_place:
        return run_repair(output_path, output_path, derived_from=output_path)
    raw_output_path = output_path.with_name(f"{output_path.stem}.raw{output_path.suffix}")
    if raw_output_path.exists():
        raw_output_path.unlink()
    output_path.replace(raw_output_path)
    return run_repair(raw_output_path, output_path, derived_from=raw_output_path)


def load_mineru_client() -> Any:
    try:
        from mineru import MinerU
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency 'mineru-open-sdk'. Install the packages from requirements.txt before using --method api."
        ) from exc
    return MinerU


def get_mineru_client(ctx: ConversionContext) -> Any:
    if ctx.mineru_client is not None:
        return ctx.mineru_client
    if not ctx.api_token:
        raise SystemExit(
            "MinerU API mode requires a token via --api-token, MINERU_TOKEN / MINERU_API_TOKEN, "
            "or a .env file in the skill root / current working directory."
        )
    MinerU = load_mineru_client()
    ctx.mineru_client = MinerU(ctx.api_token)
    return ctx.mineru_client


def save_mineru_images(output_path: Path, images: list[Any], *, prefix: str | None = None) -> dict[str, str]:
    """
    Persist MinerU images beside ``output_path`` under an ``images`` directory.

    When ``prefix`` is provided (used for split PDF chunks), each image is stored
    under a unique ``<prefix>-<name>`` filename and the returned mapping can be
    used to rewrite markdown references so later chunks do not overwrite earlier
    chunk images that happen to share a name such as ``image1.png``.
    """
    if not images:
        return {}
    image_dir = output_path.parent / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    renamed: dict[str, str] = {}
    for image in images:
        target_name = f"{prefix}-{image.name}" if prefix else image.name
        (image_dir / target_name).write_bytes(image.data)
        if target_name != image.name:
            renamed[image.name] = target_name
    return renamed


def rewrite_image_references(markdown: str, renamed: dict[str, str]) -> str:
    for original_name, new_name in renamed.items():
        markdown = markdown.replace(original_name, new_name)
    return markdown


def effective_chunk_pages(page_count: int, file_size: int, chunk_size: int) -> int:
    """
    Compute the per-chunk page count for MinerU auto-split.

    Caps the request at MinerU's hard page limit and, when the file is over the
    byte cap, shrinks chunks page-proportionally so each part has a chance of
    landing under the size limit.
    """
    pages = min(chunk_size, MINERU_MAX_PAGES)
    if file_size > MINERU_MAX_FILE_BYTES and page_count > 1:
        parts_needed = math.ceil(file_size / MINERU_MAX_FILE_BYTES)
        size_pages = max(1, page_count // parts_needed)
        pages = min(pages, size_pages)
    return max(1, pages)


def load_pdf_tools() -> tuple[Any, Any]:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency 'pypdf'. Install the packages from requirements.txt before splitting large PDFs."
        ) from exc
    return PdfReader, PdfWriter


def get_pdf_page_count(path: Path) -> int:
    PdfReader, _ = load_pdf_tools()
    return len(PdfReader(str(path)).pages)


def split_pdf(filepath: Path, chunk_size: int, work_dir: Path) -> list[dict[str, Any]]:
    if chunk_size <= 0:
        raise ValueError("--chunk-size must be a positive integer")
    PdfReader, PdfWriter = load_pdf_tools()
    reader = PdfReader(str(filepath))
    total_pages = len(reader.pages)
    chunks: list[dict[str, Any]] = []
    part_index = 1
    for start in range(0, total_pages, chunk_size):
        end = min(start + chunk_size, total_pages)
        writer = PdfWriter()
        for page_index in range(start, end):
            writer.add_page(reader.pages[page_index])
        part_path = work_dir / f"{filepath.name}.part{part_index}.pdf"
        with part_path.open("wb") as handle:
            writer.write(handle)
        chunks.append(
            {
                "path": part_path,
                "part_index": part_index,
                "start_page": start + 1,
                "end_page": end,
            }
        )
        part_index += 1
    return chunks


def merge_md_files(parts: list[dict[str, Any]]) -> str:
    ranges = ", ".join(f"pages {part['start_page']}-{part['end_page']}" for part in parts)
    header = f"<!-- MERGED from {len(parts)} parts: {ranges} -->"
    bodies = [str(part["markdown"]).strip() for part in parts if str(part.get("markdown", "")).strip()]
    return header + "\n\n" + "\n\n".join(bodies)


def extract_mineru_markdown(source_file: Path, ctx: ConversionContext, *, pages: str | None = None) -> Any:
    client = get_mineru_client(ctx)
    result = client.extract(
        str(source_file),
        model=ctx.api_model,
        ocr=ctx.ocr,
        formula=ctx.formula,
        table=ctx.table,
        language=ctx.language,
        pages=pages if source_file.suffix.lower() in PDF_SUFFIXES else None,
        timeout=ctx.timeout,
    )
    if not result.markdown:
        error = result.error or "MinerU API returned no markdown output."
        raise RuntimeError(error)
    return result


def part_output_path(output_path: Path, part_index: int) -> Path:
    return output_path.with_name(f"{output_path.stem}.part{part_index}{output_path.suffix}")


def convert_with_mineru_chunked(
    source_file: Path,
    output_path: Path,
    ctx: ConversionContext,
    page_count: int,
    chunk_pages: int,
    file_size: int,
) -> dict[str, Any]:
    if not ctx.auto_split:
        raise RuntimeError(
            f"PDF has {page_count} pages which exceeds --chunk-size {ctx.chunk_size} "
            f"(effective {chunk_pages} pages/chunk). "
            "Re-run without --no-auto-split, lower --chunk-size, or pass --pages."
        )
    if file_size > MINERU_MAX_FILE_BYTES and page_count <= 1:
        raise RuntimeError(
            f"PDF exceeds MinerU's {MINERU_MAX_FILE_BYTES // (1024 * 1024)}MB size limit "
            "and has too few pages to split by page count."
        )

    # Guard against clobbering existing per-chunk sidecars before we do any work.
    if not ctx.merge and not ctx.overwrite:
        expected_parts = math.ceil(page_count / chunk_pages)
        for index in range(1, expected_parts + 1):
            candidate = part_output_path(output_path, index)
            if candidate.exists():
                return {
                    "status": "skipped",
                    "source": str(source_file),
                    "output": str(candidate),
                    "reason": "output-exists",
                }

    work_dir = output_path.parent / f".{output_path.stem}.split-tmp"
    if work_dir.exists():
        for stale in work_dir.glob("*"):
            if stale.is_file():
                stale.unlink()
    else:
        work_dir.mkdir(parents=True, exist_ok=True)

    chunks = split_pdf(source_file, chunk_pages, work_dir)
    part_results: list[dict[str, Any]] = []
    part_outputs: list[str] = []
    part_repairs: list[dict[str, Any]] = []
    try:
        for chunk in chunks:
            result = extract_mineru_markdown(chunk["path"], ctx, pages=None)
            renamed = save_mineru_images(
                output_path,
                list(getattr(result, "images", []) or []),
                prefix=f"part{chunk['part_index']}",
            )
            part_markdown = rewrite_image_references(str(result.markdown), renamed)
            part_payload = {
                **chunk,
                "markdown": part_markdown,
            }
            part_results.append(part_payload)
            if not ctx.merge:
                part_output = part_output_path(output_path, chunk["part_index"])
                write_markdown(
                    part_output,
                    wrap_mineru_markdown(
                        source_file=source_file,
                        markdown_body=(
                            f"<!-- PART {chunk['part_index']}: pages {chunk['start_page']}-{chunk['end_page']} -->\n\n"
                            + part_markdown
                        ),
                        import_method=f"mineru-api:{ctx.api_model}",
                        course=ctx.course,
                    ),
                )
                part_outputs.append(str(part_output))
                if ctx.repair:
                    repair_payload = repair_generated_markdown(part_output)
                    part_repairs.append(
                        {
                            "part_index": chunk["part_index"],
                            "output": str(part_output),
                            "raw_output": str(part_output.with_name(f"{part_output.stem}.raw{part_output.suffix}")),
                            "repair_summary": repair_payload["summary_path"],
                            "repairs": repair_payload["repairs"],
                        }
                    )
        if ctx.merge:
            merged_body = merge_md_files(part_results)
            write_markdown(
                output_path,
                wrap_mineru_markdown(
                    source_file=source_file,
                    markdown_body=merged_body,
                    import_method=f"mineru-api:{ctx.api_model}",
                    course=ctx.course,
                ),
            )
            final_output = str(output_path)
        else:
            final_output = part_outputs[0] if part_outputs else str(output_path)
    finally:
        for chunk in chunks:
            part_path = Path(chunk["path"])
            if part_path.exists():
                part_path.unlink()
        if work_dir.exists():
            try:
                work_dir.rmdir()
            except OSError:
                pass

    payload: dict[str, Any] = {
        "status": "converted",
        "source": str(source_file),
        "output": final_output,
        "kind": "mineru-api",
        "import_method": f"mineru-api:{ctx.api_model}",
        "split": {
            "enabled": True,
            "page_count": page_count,
            "chunk_size": chunk_pages,
            "requested_chunk_size": ctx.chunk_size,
            "part_count": len(part_results),
            "merged": ctx.merge,
            "parts": [
                {
                    "part_index": part["part_index"],
                    "start_page": part["start_page"],
                    "end_page": part["end_page"],
                }
                for part in part_results
            ],
        },
    }
    if part_outputs:
        payload["part_outputs"] = part_outputs
    if ctx.repair and ctx.merge:
        repair_payload = repair_generated_markdown(output_path)
        payload["raw_output"] = str(output_path.with_name(f"{output_path.stem}.raw{output_path.suffix}"))
        payload["repair_summary"] = repair_payload["summary_path"]
        payload["repairs"] = repair_payload["repairs"]
    if part_repairs:
        payload["part_repairs"] = part_repairs
    return payload


def convert_with_mineru(source_file: Path, output_path: Path, ctx: ConversionContext) -> dict[str, Any]:
    if source_file.suffix.lower() in PDF_SUFFIXES and not ctx.pages:
        try:
            page_count = get_pdf_page_count(source_file)
        except SystemExit:
            raise
        except Exception as exc:  # malformed/encrypted PDF probe should not abort the batch
            raise RuntimeError(f"Failed to read PDF for page-count probe: {exc}") from exc
        file_size = source_file.stat().st_size
        chunk_pages = effective_chunk_pages(page_count, file_size, ctx.chunk_size)
        needs_split = page_count > chunk_pages or file_size > MINERU_MAX_FILE_BYTES
        if needs_split:
            return convert_with_mineru_chunked(source_file, output_path, ctx, page_count, chunk_pages, file_size)

    result = extract_mineru_markdown(source_file, ctx, pages=ctx.pages)
    save_mineru_images(output_path, list(getattr(result, "images", []) or []))
    write_markdown(
        output_path,
        wrap_mineru_markdown(
            source_file=source_file,
            markdown_body=result.markdown,
            import_method=f"mineru-api:{ctx.api_model}",
            course=ctx.course,
        ),
    )
    payload = {
        "status": "converted",
        "source": str(source_file),
        "output": str(output_path),
        "kind": "mineru-api",
        "import_method": f"mineru-api:{ctx.api_model}",
    }
    if ctx.repair:
        repair_payload = repair_generated_markdown(output_path)
        payload["raw_output"] = str(output_path.with_name(f"{output_path.stem}.raw{output_path.suffix}"))
        payload["repair_summary"] = repair_payload["summary_path"]
        payload["repairs"] = repair_payload["repairs"]
    return payload


def convert_with_pymupdf(source_file: Path, output_path: Path, ctx: ConversionContext) -> dict[str, Any]:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency 'pymupdf'. Install the packages from requirements.txt before using the pymupdf strategy."
        ) from exc

    document = fitz.open(str(source_file))
    try:
        page_blocks: list[str] = []
        for page_index, page in enumerate(document, start=1):
            text = page.get_text("text") or ""
            page_blocks.extend(
                [
                    f"## Page {page_index}",
                    "",
                    text.strip() if text.strip() else "[No extractable text found on this page.]",
                    "",
                ]
            )
    finally:
        document.close()

    write_markdown(
        output_path,
        wrap_mineru_markdown(
            source_file=source_file,
            markdown_body="\n".join(page_blocks).strip(),
            import_method="pymupdf",
            course=ctx.course,
        ),
    )
    payload: dict[str, Any] = {
        "status": "converted",
        "source": str(source_file),
        "output": str(output_path),
        "kind": "pdf",
        "import_method": "pymupdf",
    }
    if ctx.repair:
        repair_payload = repair_generated_markdown(output_path)
        payload["raw_output"] = str(output_path.with_name(f"{output_path.stem}.raw{output_path.suffix}"))
        payload["repair_summary"] = repair_payload["summary_path"]
        payload["repairs"] = repair_payload["repairs"]
    return payload


def convert_with_pandoc(source_file: Path, output_path: Path, ctx: ConversionContext) -> dict[str, Any]:
    if shutil.which("pandoc") is None:
        payload = run_script("docx_to_md.py", str(source_file), "--output", str(output_path))
        apply_course_metadata(Path(payload["output"]), ctx.course)
        result = {
            "status": "converted",
            "source": str(source_file),
            "output": payload["output"],
            "kind": "docx",
            "import_method": "docx-to-md",
            "pandoc_fallback": True,
        }
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            ["pandoc", str(source_file), "-t", "gfm", "-o", str(output_path)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        body = output_path.read_text(encoding="utf-8")
        write_markdown(
            output_path,
            wrap_mineru_markdown(
                source_file=source_file,
                markdown_body=body,
                import_method="pandoc",
                course=ctx.course,
            ),
        )
        result = {
            "status": "converted",
            "source": str(source_file),
            "output": str(output_path),
            "kind": "docx",
            "import_method": "pandoc",
            "pandoc_stderr": (completed.stderr or "").strip(),
        }

    if ctx.repair:
        repair_payload = repair_generated_markdown(Path(result["output"]))
        result["raw_output"] = str(Path(result["output"]).with_name(f"{Path(result['output']).stem}.raw{Path(result['output']).suffix}"))
        result["repair_summary"] = repair_payload["summary_path"]
        result["repairs"] = repair_payload["repairs"]
    return result


def effective_ocr(ctx: ConversionContext, probe: dict[str, Any]) -> bool | None:
    if ctx.ocr_explicit is not None:
        return ctx.ocr_explicit
    if probe.get("needs_ocr"):
        return True
    return ctx.ocr


def convert_with_tool(
    *,
    source_file: Path,
    output_path: Path,
    ctx: ConversionContext,
    probe: dict[str, Any],
) -> dict[str, Any]:
    tool = probe["tool"]
    if tool == "skip":
        return {
            "status": "skipped",
            "source": str(source_file),
            "reason": "already-text-friendly",
            "probe": probe,
        }
    if tool == "mineru-api":
        if not ctx.api_token:
            return {
                "status": "skipped",
                "source": str(source_file),
                "reason": "mineru-token-required",
                "probe": probe,
            }
        ocr_value = effective_ocr(ctx, probe)
        previous = ctx.ocr
        ctx.ocr = ocr_value
        try:
            payload = convert_with_mineru(source_file, output_path, ctx)
        finally:
            ctx.ocr = previous
        payload["probe"] = probe
        payload["ocr"] = ocr_value
        return payload
    if tool == "pymupdf":
        payload = convert_with_pymupdf(source_file, output_path, ctx)
        payload["probe"] = probe
        return payload
    if tool == "pandoc":
        payload = convert_with_pandoc(source_file, output_path, ctx)
        payload["probe"] = probe
        return payload
    if tool == "docx-to-md":
        plan = ConversionPlan(kind="docx", import_method="docx-to-md")
        payload = convert_with_local_plan(source_file, output_path, plan, ctx)
        payload["probe"] = probe
        return payload
    if tool == "python-pptx":
        plan = ConversionPlan(kind="pptx", import_method="pptx-to-md")
        payload = convert_with_local_plan(source_file, output_path, plan, ctx)
        payload["probe"] = probe
        return payload
    if tool == "xlsx-to-md":
        plan = ConversionPlan(kind="xlsx", import_method="xlsx-to-md")
        payload = convert_with_local_plan(source_file, output_path, plan, ctx)
        payload["probe"] = probe
        return payload
    if tool == "pdf-to-md":
        plan = ConversionPlan(kind="pdf", import_method="pdf-to-md")
        payload = convert_with_local_plan(source_file, output_path, plan, ctx)
        payload["probe"] = probe
        return payload
    if tool == "image-index":
        plan = ConversionPlan(kind="image-index", import_method="image-index")
        payload = convert_with_local_plan(source_file, output_path, plan, ctx)
        payload["probe"] = probe
        return payload
    if tool == "legacy-office-index":
        plan = ConversionPlan(kind="legacy-office-index", import_method="legacy-office-index")
        payload = convert_with_local_plan(source_file, output_path, plan, ctx)
        payload["probe"] = probe
        return payload
    if tool == "binary-index":
        plan = ConversionPlan(kind="binary-index", import_method="binary-index")
        payload = convert_with_local_plan(source_file, output_path, plan, ctx)
        payload["probe"] = probe
        return payload
    raise RuntimeError(f"Unsupported conversion tool: {tool}")


def convert_with_local_plan(
    source_file: Path,
    output_path: Path,
    plan: ConversionPlan,
    ctx: ConversionContext,
) -> dict[str, Any]:
    if plan.kind == "pdf":
        payload = run_script("pdf_to_markdown.py", str(source_file), "--output", str(output_path), "--mode", "mineru-style")
        apply_course_metadata(Path(payload["output"]), ctx.course)
        return {
            "status": "converted",
            "source": str(source_file),
            "output": payload["output"],
            "raw_output": payload.get("raw_output"),
            "repair_summary": payload.get("repair_summary"),
            "kind": plan.kind,
            "import_method": plan.import_method,
        }

    if plan.kind == "docx":
        payload = run_script("docx_to_md.py", str(source_file), "--output", str(output_path))
        apply_course_metadata(Path(payload["output"]), ctx.course)
        result = {
            "status": "converted",
            "source": str(source_file),
            "output": payload["output"],
            "kind": plan.kind,
            "import_method": plan.import_method,
        }
        if ctx.repair:
            repair_payload = repair_generated_markdown(Path(payload["output"]))
            result["raw_output"] = str(Path(payload["output"]).with_name(f"{Path(payload['output']).stem}.raw{Path(payload['output']).suffix}"))
            result["repair_summary"] = repair_payload["summary_path"]
            result["repairs"] = repair_payload["repairs"]
        return result

    if plan.kind == "pptx":
        payload = run_script("pptx_to_md.py", str(source_file), "--output", str(output_path))
        apply_course_metadata(Path(payload["output"]), ctx.course)
        result = {
            "status": "converted",
            "source": str(source_file),
            "output": payload["output"],
            "kind": plan.kind,
            "import_method": plan.import_method,
        }
        if ctx.repair:
            repair_payload = repair_generated_markdown(Path(payload["output"]))
            result["raw_output"] = str(Path(payload["output"]).with_name(f"{Path(payload['output']).stem}.raw{Path(payload['output']).suffix}"))
            result["repair_summary"] = repair_payload["summary_path"]
            result["repairs"] = repair_payload["repairs"]
        return result

    if plan.kind == "xlsx":
        payload = run_script("xlsx_to_md.py", str(source_file), "--output", str(output_path))
        apply_course_metadata(Path(payload["output"]), ctx.course)
        result = {
            "status": "converted",
            "source": str(source_file),
            "output": payload["output"],
            "kind": plan.kind,
            "import_method": plan.import_method,
        }
        if ctx.repair:
            repair_payload = repair_generated_markdown(Path(payload["output"]))
            result["raw_output"] = str(Path(payload["output"]).with_name(f"{Path(payload['output']).stem}.raw{Path(payload['output']).suffix}"))
            result["repair_summary"] = repair_payload["summary_path"]
            result["repairs"] = repair_payload["repairs"]
        return result

    if plan.kind == "image-index":
        write_index_note(
            source_file=source_file,
            output_path=output_path,
            import_method=plan.import_method,
            course=ctx.course,
            summary_lines=[
                "- OCR is not bundled in the local workflow yet.",
                "- This sidecar preserves a searchable pointer to the image until a richer OCR pass is added.",
            ],
        )
    elif plan.kind == "legacy-office-index":
        write_index_note(
            source_file=source_file,
            output_path=output_path,
            import_method=plan.import_method,
            course=ctx.course,
            summary_lines=[
                "- Legacy Office binary detected.",
                "- Convert this file to DOCX, PPTX, or XLSX first if you need local text extraction.",
                "- MinerU API mode can parse legacy Office files directly when a token is configured.",
            ],
        )
    else:
        write_index_note(
            source_file=source_file,
            output_path=output_path,
            import_method=plan.import_method,
            course=ctx.course,
            summary_lines=[
                "- Binary or tool-specific source detected.",
                "- Kept as an indexed placeholder so the material remains discoverable in markdown-first workflows.",
            ],
        )

    return {
        "status": "converted",
        "source": str(source_file),
        "output": str(output_path),
        "kind": plan.kind,
        "import_method": plan.import_method,
    }


def convert_one(
    *,
    source_file: Path,
    source_root: Path,
    output_root: Path | None,
    ctx: ConversionContext,
) -> dict[str, Any]:
    from probe_materials import resolve_probe

    output_path = build_output_path(source_file, source_root, output_root)
    probe = resolve_probe(
        source_file,
        method=ctx.method,
        force_strategy=ctx.force_strategy,
        has_api_token=bool(ctx.api_token),
    )
    if probe.get("tool") == "skip":
        return {
            "status": "skipped",
            "source": str(source_file),
            "reason": "already-text-friendly",
            "probe": probe,
        }
    if output_path.exists() and not ctx.overwrite:
        return {
            "status": "skipped",
            "source": str(source_file),
            "output": str(output_path),
            "reason": "output-exists",
            "probe": probe,
        }
    return convert_with_tool(
        source_file=source_file,
        output_path=output_path,
        ctx=ctx,
        probe=probe,
    )


def repair_one_markdown(path: Path, *, overwrite: bool) -> dict[str, Any]:
    if not is_repairable_markdown(path):
        return {
            "status": "skipped",
            "source": str(path),
            "reason": "not-repairable-markdown",
        }
    summary_path = path.with_name(f"{path.stem}-repair-summary.md")
    if summary_path.exists() and not overwrite:
        return {
            "status": "skipped",
            "source": str(path),
            "output": str(path),
            "reason": "repair-summary-exists",
        }
    payload = repair_generated_markdown(path, in_place=True)
    return {
        "status": "converted",
        "source": str(path),
        "output": str(path),
        "kind": "repair-only",
        "import_method": "repair-markdown-import",
        "repair_summary": payload["summary_path"],
        "repairs": payload["repairs"],
    }


def main() -> int:
    from probe_materials import resolve_probe

    args = parse_args()
    source = Path(args.source).resolve()
    if not source.exists():
        raise SystemExit(f"Source path does not exist: {source}")

    if args.chunk_size <= 0:
        raise SystemExit("--chunk-size must be a positive integer")
    if args.probe_only and args.repair_only:
        raise SystemExit("--probe-only cannot be combined with --repair-only")

    ctx = ConversionContext(
        method=args.method,
        course=args.course,
        overwrite=args.overwrite,
        repair=args.repair,
        repair_only=args.repair_only,
        api_token=resolve_api_token(args.api_token)
        if should_resolve_api_token(
            args.method,
            args.repair_only,
            probe_only=args.probe_only,
            force_strategy=args.force_strategy,
        )
        else None,
        api_model=args.api_model,
        language=args.language,
        ocr=args.ocr,
        formula=args.formula,
        table=args.table,
        pages=args.pages,
        timeout=args.timeout,
        auto_split=not args.no_auto_split,
        chunk_size=args.chunk_size,
        merge=args.merge,
        force_strategy=args.force_strategy,
        ocr_explicit=args.ocr,
    )
    output_root = Path(args.output_root).resolve() if args.output_root else None
    source_root, inputs = discover_inputs(source, args.pattern)
    converted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    if args.probe_only:
        probes = [
            resolve_probe(
                source_file,
                method=ctx.method,
                force_strategy=ctx.force_strategy,
                has_api_token=bool(ctx.api_token),
            )
            for source_file in inputs
        ]
        result = {
            "source": str(source),
            "source_root": str(source_root),
            "requested_method": args.method,
            "force_strategy": args.force_strategy,
            "probe_only": True,
            "has_api_token": bool(ctx.api_token),
            "probes": probes,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if ctx.repair_only:
        for source_file in inputs:
            try:
                payload = repair_one_markdown(source_file, overwrite=ctx.overwrite)
            except (subprocess.CalledProcessError, RuntimeError) as exc:
                message = (getattr(exc, "stderr", None) or getattr(exc, "stdout", None) or str(exc)).strip()
                errors.append({"source": str(source_file), "error": message})
                continue
            if payload["status"] == "converted":
                converted.append(payload)
            else:
                skipped.append(payload)
        result = {
            "source": str(source),
            "source_root": str(source_root),
            "requested_method": args.method,
            "applied_method": "repair-only",
            "converted": converted,
            "skipped": skipped,
            "errors": errors,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if not errors else 1

    for source_file in inputs:
        try:
            payload = convert_one(
                source_file=source_file,
                source_root=source_root,
                output_root=output_root,
                ctx=ctx,
            )
        except (subprocess.CalledProcessError, RuntimeError, SystemExit) as exc:
            message = (getattr(exc, "stderr", None) or getattr(exc, "stdout", None) or str(exc)).strip()
            errors.append({"source": str(source_file), "error": message})
            continue
        if payload["status"] == "converted":
            converted.append(payload)
        else:
            skipped.append(payload)

    api_like = any(
        str(item.get("import_method", "")).startswith("mineru-api:") for item in converted
    )
    result = {
        "source": str(source),
        "source_root": str(source_root),
        "requested_method": args.method,
        "force_strategy": args.force_strategy,
        "applied_method": "api" if api_like else "local",
        "converted": converted,
        "skipped": skipped,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
