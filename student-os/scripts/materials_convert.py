#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PDF_SUFFIXES = {".pdf"}
DOCX_SUFFIXES = {".docx"}
PPTX_SUFFIXES = {".pptx"}
XLSX_SUFFIXES = {".xlsx"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
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
    api_token: str | None
    api_model: str
    language: str
    ocr: bool | None
    formula: bool | None
    table: bool | None
    pages: str | None
    timeout: int
    mineru_client: Any | None = None


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
        help="Conversion strategy. auto prefers the official MinerU API when a token is available, otherwise falls back to local converters.",
    )
    parser.add_argument("--api-token", help="Optional MinerU precision API token. Defaults to MINERU_TOKEN or MINERU_API_TOKEN.")
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


def build_output_path(source_file: Path, source_root: Path, output_root: Path | None) -> Path:
    if output_root is None:
        return source_file.with_name(f"{source_file.name}.md")
    relative = source_file.relative_to(source_root)
    return output_root / relative.parent / f"{source_file.name}.md"


def resolve_api_token(cli_token: str | None) -> str | None:
    return cli_token or os.environ.get("MINERU_TOKEN") or os.environ.get("MINERU_API_TOKEN")


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
        raise SystemExit("MinerU API mode requires a token via --api-token, MINERU_TOKEN, or MINERU_API_TOKEN.")
    MinerU = load_mineru_client()
    ctx.mineru_client = MinerU(ctx.api_token)
    return ctx.mineru_client


def save_mineru_images(output_path: Path, images: list[Any]) -> None:
    if not images:
        return
    image_dir = output_path.parent / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    for image in images:
        (image_dir / image.name).write_bytes(image.data)


def convert_with_mineru(source_file: Path, output_path: Path, ctx: ConversionContext) -> dict[str, Any]:
    client = get_mineru_client(ctx)
    result = client.extract(
        str(source_file),
        model=ctx.api_model,
        ocr=ctx.ocr,
        formula=ctx.formula,
        table=ctx.table,
        language=ctx.language,
        pages=ctx.pages if source_file.suffix.lower() in PDF_SUFFIXES else None,
        timeout=ctx.timeout,
    )
    if not result.markdown:
        error = result.error or "MinerU API returned no markdown output."
        raise RuntimeError(error)
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
    return {
        "status": "converted",
        "source": str(source_file),
        "output": str(output_path),
        "kind": "mineru-api",
        "import_method": f"mineru-api:{ctx.api_model}",
    }


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
        return {
            "status": "converted",
            "source": str(source_file),
            "output": payload["output"],
            "kind": plan.kind,
            "import_method": plan.import_method,
        }

    if plan.kind == "pptx":
        payload = run_script("pptx_to_md.py", str(source_file), "--output", str(output_path))
        apply_course_metadata(Path(payload["output"]), ctx.course)
        return {
            "status": "converted",
            "source": str(source_file),
            "output": payload["output"],
            "kind": plan.kind,
            "import_method": plan.import_method,
        }

    if plan.kind == "xlsx":
        payload = run_script("xlsx_to_md.py", str(source_file), "--output", str(output_path))
        apply_course_metadata(Path(payload["output"]), ctx.course)
        return {
            "status": "converted",
            "source": str(source_file),
            "output": payload["output"],
            "kind": plan.kind,
            "import_method": plan.import_method,
        }

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
    output_path = build_output_path(source_file, source_root, output_root)
    plan = choose_local_plan(source_file)
    if plan is None:
        return {
            "status": "skipped",
            "source": str(source_file),
            "reason": "already-text-friendly",
        }
    if output_path.exists() and not ctx.overwrite:
        return {
            "status": "skipped",
            "source": str(source_file),
            "output": str(output_path),
            "reason": "output-exists",
        }

    selected_method = choose_method(source_file, ctx)
    if selected_method == "api":
        return convert_with_mineru(source_file, output_path, ctx)
    return convert_with_local_plan(source_file, output_path, plan, ctx)


def main() -> int:
    args = parse_args()
    source = Path(args.source).resolve()
    if not source.exists():
        raise SystemExit(f"Source path does not exist: {source}")

    ctx = ConversionContext(
        method=args.method,
        course=args.course,
        overwrite=args.overwrite,
        api_token=resolve_api_token(args.api_token),
        api_model=args.api_model,
        language=args.language,
        ocr=args.ocr,
        formula=args.formula,
        table=args.table,
        pages=args.pages,
        timeout=args.timeout,
    )
    output_root = Path(args.output_root).resolve() if args.output_root else None
    source_root, inputs = discover_inputs(source, args.pattern)
    converted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for source_file in inputs:
        try:
            payload = convert_one(
                source_file=source_file,
                source_root=source_root,
                output_root=output_root,
                ctx=ctx,
            )
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
        "applied_method": "api" if any(item["import_method"].startswith("mineru-api:") for item in converted) else "local",
        "converted": converted,
        "skipped": skipped,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
