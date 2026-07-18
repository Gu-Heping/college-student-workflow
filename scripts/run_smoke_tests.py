#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROOT_SCRIPTS = ROOT / "scripts"
STUDENT_OS_SCRIPTS = ROOT / "student-os" / "scripts"
EXAMPLES_ROOT = ROOT / "examples"


def load_group_git_changes_module():
    script_path = STUDENT_OS_SCRIPTS / "group_git_changes.py"
    spec = importlib.util.spec_from_file_location("student_os_group_git_changes", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for {script_path}")
    module = importlib.util.module_from_spec(spec)
    original_flag = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = original_flag
    return module


def run_script(name: str, *args: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> str:
    script_path = STUDENT_OS_SCRIPTS / name
    result = subprocess.run(
        [sys.executable, "-B", str(script_path), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
            **(env or {}),
        },
    )
    return result.stdout.strip()


def run_script_with_stdin(
    name: str,
    stdin_text: str,
    *args: str,
    cwd: Path = ROOT,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    script_path = STUDENT_OS_SCRIPTS / name
    return subprocess.run(
        [sys.executable, "-B", str(script_path), *args],
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        input=stdin_text,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
        },
    )


def run_root_script(name: str, *args: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> str:
    script_path = ROOT_SCRIPTS / name
    result = subprocess.run(
        [sys.executable, "-B", str(script_path), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
            **(env or {}),
        },
    )
    return result.stdout.strip()


def run_path_script(script_path: Path, *args: str, cwd: Path, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        [sys.executable, "-B", str(script_path), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
            **(env or {}),
        },
    )
    return result.stdout.strip()


def run_script_failure(name: str, *args: str, cwd: Path = ROOT) -> str:
    script_path = STUDENT_OS_SCRIPTS / name
    result = subprocess.run(
        [sys.executable, "-B", str(script_path), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"},
    )
    if result.returncode == 0:
        raise AssertionError(f"Expected {name} to fail for args {args!r}")
    return (result.stderr or result.stdout).strip()


def run_root_script_failure(name: str, *args: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> str:
    script_path = ROOT_SCRIPTS / name
    result = subprocess.run(
        [sys.executable, "-B", str(script_path), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
            **(env or {}),
        },
    )
    if result.returncode == 0:
        raise AssertionError(f"Expected {name} to fail for args {args!r}")
    return (result.stderr or result.stdout).strip()


def run_path_script_failure(script_path: Path, *args: str, cwd: Path, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        [sys.executable, "-B", str(script_path), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
            **(env or {}),
        },
    )
    if result.returncode == 0:
        raise AssertionError(f"Expected {script_path.name} to fail for args {args!r}")
    return (result.stderr or result.stdout).strip()


def ensure_contains(path: Path, needle: str) -> None:
    text = path.read_text(encoding="utf-8")
    if needle not in text:
        raise AssertionError(f"{path} does not contain expected text: {needle}")


def ensure_exists(path: Path) -> None:
    if not path.exists():
        raise AssertionError(f"Expected path to exist: {path}")


def copy_repo(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def load_root_script_module(name: str, module_name: str) -> object:
    script_path = ROOT_SCRIPTS / name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for {script_path}")
    module = importlib.util.module_from_spec(spec)
    original_flag = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    previous_module = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module
        sys.dont_write_bytecode = original_flag
    return module


def load_student_os_script_module(name: str, module_name: str) -> object:
    script_path = STUDENT_OS_SCRIPTS / name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for {script_path}")
    module = importlib.util.module_from_spec(spec)
    original_flag = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    previous_module = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module
        sys.dont_write_bytecode = original_flag
    return module


def load_import_dependencies() -> tuple[object, object, object, object]:
    try:
        from docx import Document
        from openpyxl import Workbook
        from pypdf import PdfWriter
        from pptx import Presentation
    except ImportError as exc:
        raise SystemExit(
            "Missing one or more import-workflow dependencies. Install requirements.txt before running smoke tests."
        ) from exc
    return Document, Workbook, Presentation, PdfWriter


def normalize_text_files(root: Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == ".gitkeep":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        normalized = text.replace("\r\n", "\n")
        path.write_text(normalized, encoding="utf-8", newline="\n")


def scrub_example_paths(root: Path, source_root: Path) -> None:
    abs_root = str(source_root.resolve())
    escaped_root = abs_root.replace("\\", "\\\\")
    for path in root.rglob("*"):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scrubbed = text
        scrubbed = scrubbed.replace(f"{escaped_root}\\\\", "")
        scrubbed = scrubbed.replace(f"{escaped_root}/", "")
        scrubbed = scrubbed.replace(f"{abs_root}\\", "")
        scrubbed = scrubbed.replace(f"{abs_root}/", "")
        if scrubbed != text:
            path.write_text(scrubbed, encoding="utf-8", newline="\n")


def materialize_empty_dirs(root: Path) -> None:
    for path in sorted([candidate for candidate in root.rglob("*") if candidate.is_dir()], key=lambda item: len(item.parts), reverse=True):
        if any(path.iterdir()):
            continue
        (path / ".gitkeep").write_text("", encoding="utf-8")


def rewrite_legacy_task_link(task_path: Path) -> None:
    text = task_path.read_text(encoding="utf-8")
    old = "- Course: ../../courses/legacy-course/index.md"
    new = "- Course: legacy course folder without generated course home"
    task_path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def write_task_fixture(
    path: Path,
    *,
    title: str,
    due: str = "",
    area: str = "",
    priority: str = "",
    course: str = "",
    tags: str = "[task]",
    course_link: str = "",
) -> None:
    lines = [
        "---",
        "type: task",
        f"course: {course}",
        "status: active",
        f"created: {date.today().isoformat()}",
        f"updated: {date.today().isoformat()}",
        f"tags: {tags}",
        "---",
        "",
        f"# {title}",
        "",
        "## Details",
        "",
        f"- Due: {due}",
        f"- Area: {area}",
        f"- Priority: {priority}",
        "",
        "## Checklist",
        "",
        "- [ ] Clarify scope",
        "- [ ] Start work",
        "- [ ] Finish",
        "",
        "## Links",
        "",
        f"- Course: {course_link}",
        "- Project:",
        "- Source file:",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def seed_planning_inputs(repo: Path, today: date) -> None:
    write_task_fixture(
        repo / "tasks" / "inbox" / "capture-linear-algebra-questions.md",
        title="Capture linear algebra questions",
        area="inbox",
        priority="medium",
        course="Linear Algebra",
        tags="[task, inbox]",
    )
    write_task_fixture(
        repo / "tasks" / "deadlines" / "linear-algebra-midterm-checkpoint.md",
        title="Linear Algebra Midterm",
        due=(today + timedelta(days=10)).isoformat(),
        area="exam",
        priority="high",
        course="Linear Algebra",
        tags="[task, exam]",
    )
    write_task_fixture(
        repo / "tasks" / "deadlines" / "linear-algebra-overdue-reading.md",
        title="Linear Algebra Overdue Reading",
        due=(today - timedelta(days=2)).isoformat(),
        area="reading",
        priority="medium",
        course="Linear Algebra",
    )
    archived_path = repo / "tasks" / "deadlines" / "linear-algebra-archived-quiz.md"
    write_task_fixture(
        archived_path,
        title="Linear Algebra Archived Quiz",
        due=(today - timedelta(days=1)).isoformat(),
        area="exam",
        priority="low",
        course="Linear Algebra",
        tags="[task, exam]",
    )
    archived_text = archived_path.read_text(encoding="utf-8").replace("status: active", "status: archived", 1)
    archived_path.write_text(archived_text, encoding="utf-8", newline="\n")
    review_path = repo / "courses" / "linear-algebra" / "reviews" / "chapter-1-review.md"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        "\n".join(
            [
                "---",
                "type: chapter-review",
                "course: Linear Algebra",
                "status: active",
                f"created: {today.isoformat()}",
                f"updated: {today.isoformat()}",
                "tags: [review]",
                "---",
                "",
                "# Chapter 1 Review",
                "",
                "## Concepts",
                "",
                "- Basis changes",
            ]
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    dashboard_path = repo / "courses" / "linear-algebra" / "dashboard.md"
    dashboard_text = dashboard_path.read_text(encoding="utf-8")
    dashboard_text = dashboard_text.replace("- Next exam:", f"- Next exam: {(today + timedelta(days=9)).isoformat()}", 1)
    dashboard_path.write_text(dashboard_text, encoding="utf-8", newline="\n")


def write_docx_fixture(path: Path) -> None:
    Document, _, _, _ = load_import_dependencies()
    document = Document()
    document.add_heading("Linear Algebra Import Outline", level=1)
    document.add_paragraph("Focus on eigenvalues, diagonalization, and orthogonality.")
    table = document.add_table(rows=3, cols=2)
    table.rows[0].cells[0].text = "Week"
    table.rows[0].cells[1].text = "Topic"
    table.rows[1].cells[0].text = "3"
    table.rows[1].cells[1].text = "Eigenvectors"
    table.rows[2].cells[0].text = "4"
    table.rows[2].cells[1].text = "Orthogonal bases"
    document.save(str(path))


def write_xlsx_fixture(path: Path) -> None:
    _, Workbook, _, _ = load_import_dependencies()
    wb = Workbook()
    ws = wb.active
    ws.title = "Progress"
    ws.append(["Task", "Score", "Weight", "Weighted"])
    ws.append(["Quiz 1", 92, 0.2, "=B2*C2"])
    ws.append(["Homework 1", 88, 0.3, "=B3*C3"])
    ws.append(["Midterm Prep", None, 0.5, "=B4*C4"])
    second = wb.create_sheet("Deadlines")
    second.append(["Item", "Date"])
    second.append(["Worksheet A", "2026-07-11"])
    second.append(["Review Session", "2026-07-12"])
    wb.save(str(path))


def write_pptx_fixture(path: Path) -> None:
    _, _, Presentation, _ = load_import_dependencies()
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Linear Algebra Week 2"
    slide.placeholders[1].text = "Diagonalization and basis changes"
    slide2 = prs.slides.add_slide(prs.slide_layouts[1])
    slide2.shapes.title.text = "Key reminders"
    slide2.placeholders[1].text = "Check eigenvalue multiplicities\nLink notes to review sheets"
    prs.save(str(path))


def write_pdf_fixture(path: Path) -> None:
    _, _, _, PdfWriter = load_import_dependencies()
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT\n/F1 18 Tf\n72 720 Td\n(#Broken linear algebra handout) Tj\n0 -24 Td\n(Page 1) Tj\n0 -24 Td\n(##Next section ........ 4) Tj\n0 -24 Td\n(-  Orthogonal projection summary) Tj\nET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.add_metadata({"/Title": "Linear Algebra Import Handout"})
    with path.open("wb") as handle:
        writer.write(handle)


def write_multipage_pdf_fixture(path: Path, page_count: int) -> None:
    _, _, _, PdfWriter = load_import_dependencies()
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    with path.open("wb") as handle:
        writer.write(handle)


def write_text_heavy_pdf_fixture(path: Path, page_count: int) -> None:
    _, _, _, PdfWriter = load_import_dependencies()
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    filler = "Linear algebra handbook text sample. " * 40
    for page_number in range(1, page_count + 1):
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        stream = DecodedStreamObject()
        # Keep content ASCII-safe for the PDF content stream.
        payload = f"BT\n/F1 10 Tf\n72 720 Td\n(Page {page_number} {filler}) Tj\nET".encode("latin-1", errors="ignore")
        stream.set_data(payload)
        page[NameObject("/Contents")] = writer._add_object(stream)
    with path.open("wb") as handle:
        writer.write(handle)


def write_png_fixture(path: Path) -> None:
    path.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A0000000D4948445200000001000000010802000000907753DE"
            "0000000C49444154789C6360600000000400010D0A2DB40000000049454E44AE426082"
        )
    )


def write_fake_mineru_sdk(root: Path) -> Path:
    module_path = root / "mineru.py"
    module_path.write_text(
        "\n".join(
            [
                "from dataclasses import dataclass, field",
                "from pathlib import Path",
                "",
                "@dataclass",
                "class Image:",
                "    name: str",
                "    data: bytes",
                "",
                "@dataclass",
                "class ExtractResult:",
                "    markdown: str",
                "    images: list[Image] = field(default_factory=list)",
                "    error: str | None = None",
                "",
                "class MinerU:",
                "    def __init__(self, token=None, base_url='https://mineru.net/api/v4', flash_base_url=None):",
                "        self.token = token",
                "",
                "    def extract(self, source, *, model=None, ocr=None, formula=None, table=None, language=None, pages=None, extra_formats=None, file_params=None, timeout=300):",
                "        path = Path(source)",
                "        body = [",
                "            f'# API Parsed - {path.name}',",
                "            '',",
                "            f'- model: {model}',",
                "            f'- language: {language}',",
                "            f'- pages: {pages}',",
                "        ]",
                "        images = []",
                "        if '.part' in path.name:",
                "            body.append('')",
                "            body.append('![figure](images/image1.png)')",
                "            images.append(Image(name='image1.png', data=b'\\x89PNG'))",
                "        return ExtractResult(markdown='\\n'.join(body), images=images)",
            ]
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return root


def exercise_import_workflows(repo: Path) -> None:
    fixture_root = repo / "references" / "imports" / "source"
    fixture_root.mkdir(parents=True, exist_ok=True)
    docx_path = fixture_root / "linear-algebra-outline.docx"
    xlsx_path = fixture_root / "linear-algebra-progress.xlsx"
    pptx_path = fixture_root / "linear-algebra-week-2.pptx"
    pdf_path = fixture_root / "linear-algebra-handout.pdf"
    png_path = fixture_root / "homework-photo.png"
    binary_path = fixture_root / "fpga-lab.bit"
    write_docx_fixture(docx_path)
    write_xlsx_fixture(xlsx_path)
    write_pptx_fixture(pptx_path)
    write_pdf_fixture(pdf_path)
    write_png_fixture(png_path)
    binary_path.write_bytes(b"\x00\x01\x02fpga")

    docx_output = repo / "courses" / "linear-algebra" / "references" / "outline-import.md"
    course_repair_summary = repo / "courses" / "linear-algebra" / "references" / "outline-import-repair-summary.md"
    xlsx_output = repo / "dashboards" / "linear-algebra-progress-import.md"
    pptx_output = repo / "references" / "slides" / "linear-algebra-week-2.md"
    pdf_generic_output = repo / "courses" / "linear-algebra" / "references" / "handout-generic-import.md"
    pdf_mineru_output = repo / "references" / "imports" / "raw" / "linear-algebra-handout.md"
    repair_input = repo / "references" / "imports" / "raw" / "manual-repair-sample.md"
    repair_output = repo / "references" / "imports" / "repaired" / "manual-repair-sample.md"
    repair_summary = repo / "references" / "imports" / "repaired" / "manual-repair-sample-repair-summary.md"

    docx_payload = json.loads(run_script("docx_to_md.py", str(docx_path), "--output", str(docx_output)))
    xlsx_payload = json.loads(run_script("xlsx_to_md.py", str(xlsx_path), "--output", str(xlsx_output), "--max-rows", "3"))
    pptx_payload = json.loads(run_script("pptx_to_md.py", str(pptx_path), "--output", str(pptx_output)))
    pdf_probe_payload = json.loads(run_script("pdf_probe.py", str(pdf_path)))
    pdf_generic_payload = json.loads(
        run_script("pdf_to_markdown.py", str(pdf_path), "--output", str(pdf_generic_output), "--mode", "generic")
    )
    pdf_mineru_payload = json.loads(
        run_script("pdf_to_markdown.py", str(pdf_path), "--output", str(pdf_mineru_output), "--mode", "mineru-style")
    )
    materials_payload = json.loads(
        run_script(
            "materials_convert.py",
            str(fixture_root),
            "--course",
            "Linear Algebra",
        )
    )
    materials_repair_payload = json.loads(
        run_script(
            "materials_convert.py",
            str(docx_path),
            "--course",
            "Linear Algebra",
            "--output-root",
            str(repo / "references" / "imports" / "repair-output"),
            "--repair",
        )
    )

    repair_input.write_text(
        "\n".join(
            [
                "---",
                "type: pdf-import-note",
                "course:",
                "status: active",
                "created:",
                "updated:",
                "tags: [import, pdf]",
                f"source_file: {json.dumps(str(pdf_path))}",
                "import_method: manual-test",
                "repair_status: raw",
                'derived_from_import: ""',
                "---",
                "",
                "#Broken heading",
                "",
                "Page 1",
                "",
                "-  Bullet with extra spacing",
                "",
                "## Next section ........ 4",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    repair_payload = json.loads(
        run_script(
            "repair_markdown_import.py",
            str(repair_input),
            "--output",
            str(repair_output),
            "--summary-path",
            str(repair_summary),
            "--derived-from",
            str(repair_input),
        )
    )

    ensure_exists(Path(docx_payload["output"]))
    ensure_contains(docx_output, "Linear Algebra Import Outline")
    ensure_contains(docx_output, "## Table 1")
    course_repair_summary.write_text("# Repair Summary\n\n- Example only.\n", encoding="utf-8", newline="\n")
    ensure_exists(Path(xlsx_payload["output"]))
    ensure_contains(xlsx_output, "| Task | Score | Weight | Weighted |")
    ensure_contains(xlsx_output, "=B2*C2")
    ensure_contains(xlsx_output, "Truncated after 3 rows.")
    ensure_exists(Path(pptx_payload["output"]))
    ensure_contains(pptx_output, "## Slide 1: Linear Algebra Week 2")
    ensure_contains(pptx_output, "Diagonalization and basis changes")
    if pdf_probe_payload["page_count"] != 1:
        raise AssertionError(f"Expected a one-page PDF fixture, got: {pdf_probe_payload}")
    ensure_exists(Path(pdf_generic_payload["output"]))
    ensure_contains(pdf_generic_output, "Import method: generic")
    ensure_contains(pdf_generic_output, "#Broken linear algebra handout")
    ensure_exists(Path(pdf_mineru_payload["output"]))
    ensure_contains(repo / "references" / "imports" / "raw" / "linear-algebra-handout.md", "repair_status: raw")
    ensure_contains(repo / "references" / "imports" / "repaired" / "linear-algebra-handout.md", "repair_status: repaired")
    ensure_contains(repo / "references" / "imports" / "repaired" / "linear-algebra-handout-repair-summary.md", "# Repair Summary")
    ensure_contains(repo / "references" / "imports" / "repaired" / "linear-algebra-handout-repair-summary.md", "Removed isolated page labels.")
    ensure_contains(repo / "references" / "imports" / "repaired" / "linear-algebra-handout-repair-summary.md", "Normalized heading spacing.")
    ensure_exists(Path(repair_payload["output"]))
    ensure_contains(repair_output, "# Broken heading")
    ensure_contains(repair_output, "- Bullet with extra spacing")
    ensure_contains(repair_summary, "Removed isolated page labels.")
    ensure_contains(repair_summary, "Normalized heading spacing.")
    ensure_contains(repair_summary, "Trimmed heading dot leaders or page-number residue.")

    unicode_derived_root = repo / "references" / "imports" / "用户资料"
    unicode_derived_root.mkdir(parents=True, exist_ok=True)
    unicode_derived_source = unicode_derived_root / "raw-import.md"
    unicode_repair_input = repo / "references" / "imports" / "repaired" / "unicode-path-repair-input.md"
    unicode_repair_output = repo / "references" / "imports" / "repaired" / "unicode-path-repair-output.md"
    unicode_derived_source.write_text("# raw\n", encoding="utf-8", newline="\n")
    unicode_repair_input.write_text(
        "\n".join(
            [
                "---",
                "type: pdf-import-note",
                "course:",
                "status: active",
                "created:",
                "updated:",
                "tags: [import, pdf]",
                'source_file: "sample.pdf"',
                "import_method: manual-test",
                "repair_status:",
                "derived_from_import:",
                "---",
                "",
                "#Broken heading",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    unicode_repair_payload = json.loads(
        run_script(
            "repair_markdown_import.py",
            str(unicode_repair_input),
            "--output",
            str(unicode_repair_output),
            "--derived-from",
            str(unicode_derived_source),
        )
    )
    ensure_exists(Path(unicode_repair_payload["output"]))
    ensure_contains(unicode_repair_output, "derived_from_import:")
    ensure_contains(unicode_repair_output, "raw-import.md")
    # json.dumps escapes non-ASCII path segments; either literal or \\uXXXX form is fine.
    unicode_output_text = unicode_repair_output.read_text(encoding="utf-8")
    if "用户资料" not in unicode_output_text and "\\u7528\\u6237" not in unicode_output_text:
        raise AssertionError(
            "Expected unicode path segment to appear literally or as JSON escapes in derived_from_import"
        )
    ensure_contains(unicode_repair_output, "repair_status: repaired")
    if 'derived_from_import:\n' in unicode_output_text or 'derived_from_import: ""' in unicode_output_text:
        raise AssertionError("derived_from_import should be filled for unicode Windows paths")

    if len(materials_payload["converted"]) != 6:
        raise AssertionError(f"Expected six converted material outputs, got: {materials_payload}")
    ensure_exists(fixture_root / "linear-algebra-outline.docx.md")
    ensure_contains(fixture_root / "linear-algebra-outline.docx.md", 'course: "Linear Algebra"')
    ensure_exists(fixture_root / "linear-algebra-progress.xlsx.md")
    ensure_contains(fixture_root / "linear-algebra-progress.xlsx.md", "| Task | Score | Weight | Weighted |")
    ensure_exists(fixture_root / "linear-algebra-week-2.pptx.md")
    ensure_contains(fixture_root / "linear-algebra-week-2.pptx.md", "## Slide 1: Linear Algebra Week 2")
    ensure_exists(fixture_root / "linear-algebra-handout.pdf.md")
    ensure_exists(fixture_root / "linear-algebra-handout.pdf.raw.md")
    ensure_exists(fixture_root / "linear-algebra-handout.pdf-repair-summary.md")
    ensure_contains(fixture_root / "linear-algebra-handout.pdf.md", "repair_status: repaired")
    ensure_exists(fixture_root / "homework-photo.png.md")
    ensure_contains(fixture_root / "homework-photo.png.md", "OCR is not bundled in the local workflow yet.")
    ensure_exists(fixture_root / "fpga-lab.bit.md")
    ensure_contains(fixture_root / "fpga-lab.bit.md", "Binary or tool-specific source detected.")
    if len(materials_repair_payload["converted"]) != 1:
        raise AssertionError(f"Expected one repaired material output, got: {materials_repair_payload}")
    repair_output_root = repo / "references" / "imports" / "repair-output"
    ensure_exists(repair_output_root / "linear-algebra-outline.docx.md")
    ensure_exists(repair_output_root / "linear-algebra-outline.docx.raw.md")
    ensure_exists(repair_output_root / "linear-algebra-outline.docx-repair-summary.md")
    ensure_contains(repair_output_root / "linear-algebra-outline.docx.md", "repair_status: repaired")
    ensure_contains(repair_output_root / "linear-algebra-outline.docx-repair-summary.md", "# Repair Summary")
    ensure_contains(repair_output_root / "linear-algebra-outline.docx-repair-summary.md", "Output:")

    fake_sdk_root = repo / "references" / "imports" / "fake-sdk"
    fake_sdk_root.mkdir(parents=True, exist_ok=True)
    write_fake_mineru_sdk(fake_sdk_root)
    api_output_root = repo / "references" / "imports" / "api-output"
    api_payload = json.loads(
        run_script(
            "materials_convert.py",
            str(fixture_root),
            "--output-root",
            str(api_output_root),
            "--course",
            "Linear Algebra",
            "--method",
            "api",
            "--api-token",
            "test-token",
            "--language",
            "en",
            "--pages",
            "1-1",
            env={"PYTHONPATH": str(fake_sdk_root)},
        )
    )
    if api_payload["applied_method"] != "api":
        raise AssertionError(f"Expected API mode to be applied, got: {api_payload}")
    ensure_exists(api_output_root / "linear-algebra-outline.docx.md")
    ensure_contains(api_output_root / "linear-algebra-outline.docx.md", "Import method: mineru-api:vlm")
    ensure_contains(api_output_root / "linear-algebra-outline.docx.md", "# API Parsed - linear-algebra-outline.docx")
    ensure_exists(api_output_root / "homework-photo.png.md")
    ensure_contains(api_output_root / "homework-photo.png.md", "# API Parsed - homework-photo.png")
    ensure_exists(api_output_root / "linear-algebra-handout.pdf.md")
    ensure_contains(api_output_root / "linear-algebra-handout.pdf.md", "- pages: 1-1")
    ensure_exists(api_output_root / "fpga-lab.bit.md")
    ensure_contains(api_output_root / "fpga-lab.bit.md", "Binary or tool-specific source detected.")
    api_repair_payload = json.loads(
        run_script(
            "materials_convert.py",
            str(docx_path),
            "--output-root",
            str(repo / "references" / "imports" / "api-repair-output"),
            "--course",
            "Linear Algebra",
            "--method",
            "api",
            "--api-token",
            "test-token",
            "--repair",
            env={"PYTHONPATH": str(fake_sdk_root)},
        )
    )
    if len(api_repair_payload["converted"]) != 1:
        raise AssertionError(f"Expected one API repaired output, got: {api_repair_payload}")
    api_repair_root = repo / "references" / "imports" / "api-repair-output"
    ensure_exists(api_repair_root / "linear-algebra-outline.docx.md")
    ensure_exists(api_repair_root / "linear-algebra-outline.docx.raw.md")
    ensure_exists(api_repair_root / "linear-algebra-outline.docx-repair-summary.md")
    ensure_contains(api_repair_root / "linear-algebra-outline.docx.md", "repair_status: repaired")

    large_pdf_path = fixture_root / "large-textbook.pdf"
    write_multipage_pdf_fixture(large_pdf_path, 5)
    split_output_root = repo / "references" / "imports" / "api-split-output"
    split_payload = json.loads(
        run_script(
            "materials_convert.py",
            str(large_pdf_path),
            "--output-root",
            str(split_output_root),
            "--course",
            "Linear Algebra",
            "--method",
            "api",
            "--api-token",
            "test-token",
            "--chunk-size",
            "2",
            env={"PYTHONPATH": str(fake_sdk_root)},
        )
    )
    if len(split_payload["converted"]) != 1:
        raise AssertionError(f"Expected one auto-split conversion, got: {split_payload}")
    split_info = split_payload["converted"][0].get("split")
    if not split_info or split_info.get("part_count") != 3 or not split_info.get("merged"):
        raise AssertionError(f"Expected 3 merged PDF chunks, got: {split_payload['converted'][0]}")
    split_output = split_output_root / "large-textbook.pdf.md"
    ensure_exists(split_output)
    ensure_contains(split_output, "<!-- MERGED from 3 parts: pages 1-2, pages 3-4, pages 5-5 -->")
    ensure_contains(split_output, "# API Parsed - large-textbook.pdf.part1.pdf")
    ensure_contains(split_output, "# API Parsed - large-textbook.pdf.part2.pdf")
    ensure_contains(split_output, "# API Parsed - large-textbook.pdf.part3.pdf")
    leftover_parts = list(split_output_root.glob("**/*.part*.pdf"))
    if leftover_parts:
        raise AssertionError(f"Auto-split should clean temporary PDF chunks, found: {leftover_parts}")
    # Each chunk emits an image named image1.png; they must not overwrite each other.
    split_image_dir = split_output_root / "images"
    for part_index in (1, 2, 3):
        ensure_exists(split_image_dir / f"part{part_index}-image1.png")
        ensure_contains(split_output, f"images/part{part_index}-image1.png")
    if (split_image_dir / "image1.png").exists():
        raise AssertionError("Auto-split should not leave unprefixed chunk images that collide across parts")

    no_split_output = run_path_script_failure(
        STUDENT_OS_SCRIPTS / "materials_convert.py",
        str(large_pdf_path),
        "--output-root",
        str(repo / "references" / "imports" / "api-no-split-output"),
        "--method",
        "api",
        "--api-token",
        "test-token",
        "--chunk-size",
        "2",
        "--no-auto-split",
        "--overwrite",
        cwd=ROOT,
        env={"PYTHONPATH": str(fake_sdk_root)},
    )
    no_split_payload = json.loads(no_split_output)
    if not no_split_payload.get("errors"):
        raise AssertionError(f"Expected --no-auto-split to record conversion errors, got: {no_split_payload}")
    if "exceeds --chunk-size" not in no_split_payload["errors"][0].get("error", ""):
        raise AssertionError(f"Expected chunk-size error message, got: {no_split_payload['errors']}")

    dotenv_cwd = repo / "references" / "imports" / "dotenv-cwd"
    dotenv_cwd.mkdir(parents=True, exist_ok=True)
    empty_skill_root = dotenv_cwd / "empty-skill-root"
    empty_skill_root.mkdir(parents=True, exist_ok=True)
    (dotenv_cwd / ".env").write_text('MINERU_TOKEN="dotenv-from-cwd"\n', encoding="utf-8", newline="\n")
    dotenv_output_root = repo / "references" / "imports" / "api-dotenv-output"
    dotenv_payload = json.loads(
        run_script(
            "materials_convert.py",
            str(pdf_path),
            "--output-root",
            str(dotenv_output_root),
            "--method",
            "api",
            "--overwrite",
            cwd=dotenv_cwd,
            env={
                "PYTHONPATH": str(fake_sdk_root),
                "MINERU_TOKEN": "",
                "MINERU_API_TOKEN": "",
                "STUDENT_OS_SKILL_ROOT": str(empty_skill_root),
            },
        )
    )
    if dotenv_payload["applied_method"] != "api":
        raise AssertionError(f"Expected cwd .env token to enable API mode, got: {dotenv_payload}")
    ensure_exists(dotenv_output_root / "linear-algebra-handout.pdf.md")
    ensure_contains(dotenv_output_root / "linear-algebra-handout.pdf.md", "Import method: mineru-api:vlm")

    # A --chunk-size above MinerU's 200-page limit must still split PDFs over 200 pages.
    over_limit_pdf = fixture_root / "over-limit.pdf"
    write_multipage_pdf_fixture(over_limit_pdf, 201)
    cap_payload = json.loads(
        run_script(
            "materials_convert.py",
            str(over_limit_pdf),
            "--output-root",
            str(repo / "references" / "imports" / "api-cap-output"),
            "--method",
            "api",
            "--api-token",
            "test-token",
            "--chunk-size",
            "500",
            env={"PYTHONPATH": str(fake_sdk_root)},
        )
    )
    cap_split = cap_payload["converted"][0].get("split")
    if not cap_split or cap_split.get("part_count") != 2 or cap_split.get("chunk_size") != 200:
        raise AssertionError(f"Expected --chunk-size to be capped at 200 pages, got: {cap_payload['converted'][0]}")
    over_limit_pdf.unlink()

    # A PDF within the page limit but over the byte cap must still be split by size.
    size_split_payload = json.loads(
        run_script(
            "materials_convert.py",
            str(large_pdf_path),
            "--output-root",
            str(repo / "references" / "imports" / "api-size-split-output"),
            "--method",
            "api",
            "--api-token",
            "test-token",
            "--chunk-size",
            "50",
            env={"PYTHONPATH": str(fake_sdk_root), "STUDENT_OS_MINERU_MAX_FILE_BYTES": "1"},
        )
    )
    size_split = size_split_payload["converted"][0].get("split")
    if not size_split or size_split.get("part_count") != 5:
        raise AssertionError(f"Expected size-driven split into single-page chunks, got: {size_split_payload['converted'][0]}")

    # A malformed PDF must be reported per-file (JSON stdout), not abort the batch.
    bad_pdf = fixture_root / "corrupt.pdf"
    bad_pdf.write_bytes(b"%PDF-1.4 not really a pdf")
    bad_result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(STUDENT_OS_SCRIPTS / "materials_convert.py"),
            str(bad_pdf),
            "--output-root",
            str(repo / "references" / "imports" / "api-bad-pdf-output"),
            "--method",
            "api",
            "--api-token",
            "test-token",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8", "PYTHONPATH": str(fake_sdk_root)},
    )
    if bad_result.returncode == 0:
        raise AssertionError("Expected malformed PDF to produce a non-zero exit code")
    bad_payload = json.loads(bad_result.stdout)
    if not bad_payload.get("errors") or "page-count probe" not in bad_payload["errors"][0].get("error", ""):
        raise AssertionError(f"Expected malformed PDF to be captured in errors, got: {bad_payload}")
    bad_pdf.unlink()

    # --no-merge must not clobber existing chunk sidecars without --overwrite, and
    # --repair must run on each chunk sidecar.
    no_merge_root = repo / "references" / "imports" / "api-no-merge-output"
    no_merge_payload = json.loads(
        run_script(
            "materials_convert.py",
            str(large_pdf_path),
            "--output-root",
            str(no_merge_root),
            "--method",
            "api",
            "--api-token",
            "test-token",
            "--chunk-size",
            "2",
            "--no-merge",
            "--repair",
            env={"PYTHONPATH": str(fake_sdk_root)},
        )
    )
    no_merge_converted = no_merge_payload["converted"][0]
    if not no_merge_converted.get("part_repairs") or len(no_merge_converted["part_repairs"]) != 3:
        raise AssertionError(f"Expected --no-merge --repair to repair each chunk, got: {no_merge_converted}")
    for part_index in (1, 2, 3):
        ensure_exists(no_merge_root / f"large-textbook.pdf.part{part_index}.md")
        ensure_exists(no_merge_root / f"large-textbook.pdf.part{part_index}-repair-summary.md")

    sentinel_part = no_merge_root / "large-textbook.pdf.part1.md"
    sentinel_part.write_text("SENTINEL EDIT\n", encoding="utf-8")
    rerun_payload = json.loads(
        run_script(
            "materials_convert.py",
            str(large_pdf_path),
            "--output-root",
            str(no_merge_root),
            "--method",
            "api",
            "--api-token",
            "test-token",
            "--chunk-size",
            "2",
            "--no-merge",
            env={"PYTHONPATH": str(fake_sdk_root)},
        )
    )
    if not rerun_payload["skipped"] or rerun_payload["skipped"][0].get("reason") != "output-exists":
        raise AssertionError(f"Expected --no-merge rerun to skip existing chunk sidecars, got: {rerun_payload}")
    if sentinel_part.read_text(encoding="utf-8") != "SENTINEL EDIT\n":
        raise AssertionError("--no-merge rerun without --overwrite must not clobber existing chunk sidecars")

    repair_only_input = repo / "references" / "imports" / "repair-only-sample.md"
    repair_only_input.write_text(
        "\n".join(
            [
                "---",
                "type: imported-reference",
                "course:",
                "status: active",
                "created:",
                "updated:",
                "tags: [import, reference]",
                'source_file: "sample.pdf"',
                "import_method: manual-test",
                "repair_status:",
                "derived_from_import:",
                "---",
                "",
                "#Broken heading",
                "",
                "Page 1",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    repair_only_payload = json.loads(
        run_script(
            "materials_convert.py",
            str(repair_only_input),
            "--repair-only",
        )
    )
    if len(repair_only_payload["converted"]) != 1:
        raise AssertionError(f"Expected one repair-only output, got: {repair_only_payload}")
    ensure_contains(repair_only_input, "# Broken heading")
    ensure_contains(repair_only_input, "repair_status: repaired")
    ensure_exists(repo / "references" / "imports" / "repair-only-sample-repair-summary.md")
    ensure_contains(repo / "references" / "imports" / "repair-only-sample-repair-summary.md", "Removed isolated page labels.")

    # Content-aware probing / smart routing.
    no_token_env = {
        "MINERU_TOKEN": "",
        "MINERU_API_TOKEN": "",
        "STUDENT_OS_SKILL_ROOT": str(empty_skill_root),
    }
    probe_only_payload = json.loads(
        run_script(
            "materials_convert.py",
            str(fixture_root),
            "--probe-only",
            cwd=empty_skill_root,
            env=no_token_env,
        )
    )
    if not probe_only_payload.get("probe_only") or not probe_only_payload.get("probes"):
        raise AssertionError(f"Expected --probe-only JSON report, got: {probe_only_payload}")
    probes_by_name = {Path(item["source"]).name: item for item in probe_only_payload["probes"]}
    if probes_by_name["linear-algebra-handout.pdf"]["tool"] not in {"pdf-to-md", "pymupdf"}:
        raise AssertionError(
            f"Without a token, PDF probes should stay local, got: {probes_by_name['linear-algebra-handout.pdf']}"
        )
    if probes_by_name["homework-photo.png"]["tool"] != "image-index":
        raise AssertionError("Without a token, image probes should degrade to image-index")
    if probes_by_name["linear-algebra-outline.docx"]["tool"] not in {"pandoc", "docx-to-md"}:
        raise AssertionError(f"Unexpected DOCX tool: {probes_by_name['linear-algebra-outline.docx']}")

    scanned_pdf = fixture_root / "scanned-blank.pdf"
    write_multipage_pdf_fixture(scanned_pdf, 2)
    scanned_probe = json.loads(
        run_script(
            "materials_convert.py",
            str(scanned_pdf),
            "--probe-only",
            "--api-token",
            "test-token",
        )
    )["probes"][0]
    if (
        scanned_probe["strategy"] != "scanned"
        or scanned_probe.get("tool") != "mineru-api"
        or not scanned_probe.get("needs_ocr")
    ):
        raise AssertionError(f"Expected blank PDF to probe as scanned+mineru-api+OCR, got: {scanned_probe}")

    manual_pdf = fixture_root / "text-manual.pdf"
    write_text_heavy_pdf_fixture(manual_pdf, 3)
    manual_probe = json.loads(
        run_script(
            "materials_convert.py",
            str(manual_pdf),
            "--probe-only",
            cwd=empty_skill_root,
            env={
                **no_token_env,
                "STUDENT_OS_PDF_MANUAL_CHARS_PER_PAGE": "100",
            },
        )
    )["probes"][0]
    if manual_probe["tool"] != "pymupdf":
        raise AssertionError(f"Expected text-heavy PDF to prefer pymupdf, got: {manual_probe}")

    pymupdf_root = repo / "references" / "imports" / "pymupdf-output"
    pymupdf_payload = json.loads(
        run_script(
            "materials_convert.py",
            str(manual_pdf),
            "--output-root",
            str(pymupdf_root),
            "--force-strategy",
            "pymupdf",
            "--pages",
            "2",
            "--overwrite",
        )
    )
    if pymupdf_payload["converted"][0].get("import_method") != "pymupdf":
        raise AssertionError(f"Expected forced pymupdf conversion, got: {pymupdf_payload}")
    pymupdf_md = (pymupdf_root / "text-manual.pdf.md").read_text(encoding="utf-8")
    if "## Page 2" not in pymupdf_md or "## Page 1" in pymupdf_md or "## Page 3" in pymupdf_md:
        raise AssertionError(f"Expected pymupdf --pages 2 to extract only page 2, got:\n{pymupdf_md}")

    invalid_pages_result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(STUDENT_OS_SCRIPTS / "materials_convert.py"),
            str(manual_pdf),
            "--output-root",
            str(repo / "references" / "imports" / "pymupdf-invalid-pages"),
            "--force-strategy",
            "pymupdf",
            "--pages",
            "99",
            "--overwrite",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"},
    )
    if invalid_pages_result.returncode == 0:
        raise AssertionError("Expected out-of-range --pages to exit nonzero")
    invalid_pages_payload = json.loads(invalid_pages_result.stdout)
    if not invalid_pages_payload.get("errors") or "does not select any pages" not in invalid_pages_payload["errors"][
        0
    ].get("error", ""):
        raise AssertionError(f"Expected invalid --pages error, got: {invalid_pages_payload}")

    method_api_no_token = subprocess.run(
        [
            sys.executable,
            "-B",
            str(STUDENT_OS_SCRIPTS / "materials_convert.py"),
            str(manual_pdf),
            "--output-root",
            str(repo / "references" / "imports" / "method-api-no-token"),
            "--method",
            "api",
            "--overwrite",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=empty_skill_root,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
            **no_token_env,
        },
    )
    if method_api_no_token.returncode == 0:
        raise AssertionError("Expected --method api without token to exit nonzero")
    method_api_payload = json.loads(method_api_no_token.stdout)
    if method_api_payload.get("converted"):
        raise AssertionError(f"--method api without token must not convert locally, got: {method_api_payload}")
    if not method_api_payload.get("errors") or "requires a token" not in method_api_payload["errors"][0].get(
        "error", ""
    ):
        raise AssertionError(f"Expected --method api without token to error, got: {method_api_payload}")

    forced_api_no_token = subprocess.run(
        [
            sys.executable,
            "-B",
            str(STUDENT_OS_SCRIPTS / "materials_convert.py"),
            str(manual_pdf),
            "--output-root",
            str(repo / "references" / "imports" / "forced-api-no-token"),
            "--force-strategy",
            "mineru-api",
            "--overwrite",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=empty_skill_root,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
            **no_token_env,
        },
    )
    if forced_api_no_token.returncode == 0:
        raise AssertionError("Expected forced mineru-api without token to exit nonzero")
    forced_api_payload = json.loads(forced_api_no_token.stdout)
    if not forced_api_payload.get("errors") or "requires a token" not in forced_api_payload["errors"][0].get("error", ""):
        raise AssertionError(f"Expected forced API without token to error, got: {forced_api_payload}")

    corrupt_docx = fixture_root / "corrupt.docx"
    corrupt_docx.write_bytes(b"PK\x03\x04not-a-real-docx")
    corrupt_probe_result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(STUDENT_OS_SCRIPTS / "materials_convert.py"),
            str(corrupt_docx),
            "--probe-only",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"},
    )
    if corrupt_probe_result.returncode == 0:
        raise AssertionError("Expected corrupt DOCX --probe-only to exit nonzero")
    corrupt_probe_payload = json.loads(corrupt_probe_result.stdout)
    if not corrupt_probe_payload.get("errors") or "Failed to probe DOCX" not in corrupt_probe_payload["errors"][0].get(
        "error", ""
    ):
        raise AssertionError(f"Expected corrupt DOCX probe error, got: {corrupt_probe_payload}")
    corrupt_docx.unlink()

    image_heavy_docx = fixture_root / "image-heavy.docx"
    Document, _, _, _ = load_import_dependencies()
    from docx.shared import Inches
    import struct
    import zlib

    def _png_chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    valid_png = fixture_root / "valid-1x1.png"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\x00\x00")
    valid_png.write_bytes(b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", idat) + _png_chunk(b"IEND", b""))
    heavy_doc = Document()
    heavy_doc.add_paragraph("pic")
    heavy_doc.add_picture(str(valid_png), width=Inches(1.5))
    heavy_doc.save(str(image_heavy_docx))
    heavy_probe = json.loads(
        run_script(
            "materials_convert.py",
            str(image_heavy_docx),
            "--probe-only",
            "--api-token",
            "test-token",
        )
    )["probes"][0]
    if (
        heavy_probe["tool"] != "mineru-api"
        or heavy_probe["strategy"] != "image-heavy-docx"
        or not heavy_probe.get("needs_ocr")
    ):
        raise AssertionError(f"Expected image-heavy DOCX to prefer MinerU API+OCR, got: {heavy_probe}")
    valid_png.unlink()

    auto_image_payload = json.loads(
        run_script(
            "materials_convert.py",
            str(png_path),
            "--output-root",
            str(repo / "references" / "imports" / "auto-image-api"),
            "--method",
            "auto",
            "--api-token",
            "test-token",
            "--overwrite",
            env={"PYTHONPATH": str(fake_sdk_root)},
        )
    )
    if auto_image_payload["converted"][0].get("import_method") != "mineru-api:vlm":
        raise AssertionError(f"Expected auto image routing to MinerU API, got: {auto_image_payload}")
    if not auto_image_payload["converted"][0].get("ocr"):
        raise AssertionError("Expected auto image routing to enable OCR")

    legacy_doc = fixture_root / "legacy-notes.doc"
    legacy_doc.write_bytes(b"\xd0\xcf\x11\xe0legacy-doc")
    legacy_probe = json.loads(
        run_script(
            "materials_convert.py",
            str(legacy_doc),
            "--probe-only",
            "--api-token",
            "test-token",
        )
    )["probes"][0]
    if legacy_probe["tool"] != "mineru-api":
        raise AssertionError(f"Expected legacy .doc to prefer MinerU API, got: {legacy_probe}")
    legacy_no_token = json.loads(
        run_script(
            "materials_convert.py",
            str(legacy_doc),
            "--probe-only",
            cwd=empty_skill_root,
            env=no_token_env,
        )
    )["probes"][0]
    if legacy_no_token["tool"] != "legacy-office-index":
        raise AssertionError(f"Expected legacy .doc without token to degrade to index, got: {legacy_no_token}")

    scanned_pdf.unlink()
    manual_pdf.unlink()
    image_heavy_docx.unlink()
    legacy_doc.unlink()

    docx_path.unlink()
    xlsx_path.unlink()
    pptx_path.unlink()
    pdf_path.unlink()
    large_pdf_path.unlink()
    png_path.unlink()
    binary_path.unlink()


def exercise_exam_census(repo: Path) -> None:
    exams_dir = repo / "courses" / "linear-algebra" / "references" / "exams"
    exams_dir.mkdir(parents=True, exist_ok=True)

    papers = {
        "2019-期中-A.pdf.md": "\n".join(
            [
                "---",
                "type: pdf-import-note",
                'course: "Linear Algebra"',
                "status: active",
                "tags: [import, pdf, exam]",
                "---",
                "",
                "# 2019 Midterm A",
                "",
                "1. Compute the rank of a matrix.",
                "2. Diagonalize a symmetric matrix via eigenvalues.",
                "",
            ]
        ),
        "2020-期中-B.pdf.md": "\n".join(
            [
                "---",
                "type: pdf-import-note",
                'course: "Linear Algebra"',
                "status: active",
                "tags: [import, pdf, exam]",
                "---",
                "",
                "# 2020 Midterm B",
                "",
                "1. Find the rank and nullity.",
                "2. Solve a linear system with Gaussian elimination.",
                "",
            ]
        ),
        "2021-期中-C.pdf.md": "\n".join(
            [
                "---",
                "type: pdf-import-note",
                'course: "Linear Algebra"',
                "status: active",
                "tags: [import, pdf, exam]",
                "---",
                "",
                "# 2021 Midterm C",
                "",
                "1. Eigenvalues and diagonalization.",
                "2. Rank of an augmented matrix.",
                "",
            ]
        ),
    }
    for name, body in papers.items():
        (exams_dir / name).write_text(body + "\n", encoding="utf-8", newline="\n")

    init_payload = json.loads(
        run_script(
            "init_exam_census.py",
            str(repo),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "期中",
            "--papers-dir",
            "courses/linear-algebra/references/exams",
            "--pattern",
            "**/*.pdf.md",
            "--batch-size",
            "2",
        )
    )
    if init_payload.get("paper_count") != 3 or init_payload.get("batch_count") != 2:
        raise AssertionError(f"Unexpected exam-census init payload: {init_payload}")

    state_dir = repo / ".student-os" / "state" / "exam-census" / "linear-algebra" / "期中"
    taxonomy_path = state_dir / "taxonomy.yaml"
    taxonomy_path.write_text(
        "\n".join(
            [
                "version: 1",
                'course: "Linear Algebra"',
                "exam_scope: 期中",
                "types:",
                "  - id: matrix-rank",
                "    name: 矩阵的秩",
                "    aliases: [秩, rank]",
                "    keywords: [秩, 行阶梯]",
                "  - id: eigen-decomp",
                "    name: 特征值与对角化",
                "    aliases: [特征值, diagonalize]",
                "    keywords: [特征值, 对角化]",
                "  - id: gaussian-elim",
                "    name: 高斯消元",
                "    aliases: [消元]",
                "    keywords: [高斯, 行变换]",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )

    annotations = {
        "2019-期中-A": {
            "source": "courses/linear-algebra/references/exams/2019-期中-A.pdf.md",
            "exam_label": "2019 期中 A",
            "types_present": ["matrix-rank", "eigen-decomp"],
            "type_counts": {"matrix-rank": 1, "eigen-decomp": 1},
            "confidence": "high",
            "notes": "classic pair",
        },
        "2020-期中-B": {
            "source": "courses/linear-algebra/references/exams/2020-期中-B.pdf.md",
            "exam_label": "2020 期中 B",
            "types_present": ["matrix-rank", "gaussian-elim"],
            "type_counts": {"matrix-rank": 1, "gaussian-elim": 1},
            "confidence": "high",
            "notes": "",
        },
        "2021-期中-C": {
            "source": "courses/linear-algebra/references/exams/2021-期中-C.pdf.md",
            "exam_label": "2021 期中 C",
            "types_present": ["matrix-rank", "eigen-decomp"],
            "type_counts": {"matrix-rank": 1, "eigen-decomp": 1},
            "confidence": "low",
            "notes": "OCR a bit noisy",
        },
    }
    annotations_dir = state_dir / "annotations"
    for stem, payload in annotations.items():
        (annotations_dir / f"{stem}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    stats_payload = json.loads(
        run_script(
            "build_exam_type_stats.py",
            str(repo),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "期中",
            "--overwrite",
        )
    )
    ranked_ids = [item["id"] for item in stats_payload.get("ranked_types", [])]
    if ranked_ids[:2] != ["matrix-rank", "eigen-decomp"]:
        raise AssertionError(f"Expected matrix-rank then eigen-decomp by appearance, got: {ranked_ids}")
    if stats_payload["ranked_types"][0]["paper_count"] != 3:
        raise AssertionError(f"matrix-rank should appear in all 3 papers: {stats_payload}")
    if not stats_payload["ranked_types"][0]["must_know"]:
        raise AssertionError("matrix-rank should be must-know at 100% appearance")

    report_path = repo / "courses" / "linear-algebra" / "reviews" / "期中" / "题型频率统计.md"
    ensure_exists(report_path)
    ensure_contains(report_path, "type: exam-type-frequency-report")
    ensure_contains(report_path, "matrix-rank")
    ensure_contains(report_path, "Low-confidence annotations")
    ensure_contains(report_path, "`2021-期中-C`")
    ensure_contains(report_path, "](../../references/exams/2019-期中-A.pdf.md)")

    first_skeleton = repo / "courses" / "linear-algebra" / "reviews" / "期中" / "题型解析" / "01-matrix-rank.md"
    ensure_exists(first_skeleton)
    ensure_contains(first_skeleton, "type: exam-type-analysis")
    ensure_contains(first_skeleton, "exam_type_id: \"matrix-rank\"")
    ensure_contains(first_skeleton, "Must-know tier: yes")
    ensure_contains(first_skeleton, "](../../../references/exams/2019-期中-A.pdf.md)")

    second_skeleton = repo / "courses" / "linear-algebra" / "reviews" / "期中" / "题型解析" / "02-eigen-decomp.md"
    ensure_exists(second_skeleton)
    third_skeleton = repo / "courses" / "linear-algebra" / "reviews" / "期中" / "题型解析" / "03-gaussian-elim.md"
    ensure_exists(third_skeleton)

    # Pipe characters in type names must not break the Markdown table.
    taxonomy_path.write_text(
        taxonomy_path.read_text(encoding="utf-8").replace(
            "    name: 矩阵的秩\n",
            "    name: \"矩阵的秩 P(A|B)\"\n",
        ),
        encoding="utf-8",
        newline="\n",
    )
    run_script(
        "build_exam_type_stats.py",
        str(repo),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期中",
        "--overwrite",
    )
    ensure_contains(report_path, "矩阵的秩 P(A\\|B)")

    # Unknown types_present / type_counts keys must appear in the durable report and fail --validate.
    bad_annotation = dict(annotations["2021-期中-C"])
    bad_annotation["types_present"] = ["matrix-rank", "not-a-real-type"]
    bad_annotation["type_counts"] = {"matrix-rank": 1, "ghost-count": 2}
    (annotations_dir / "2021-期中-C.json").write_text(
        json.dumps(bad_annotation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    bad_validate = subprocess.run(
        [
            sys.executable,
            "-B",
            str(STUDENT_OS_SCRIPTS / "build_exam_type_stats.py"),
            str(repo),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "期中",
            "--validate",
            "--overwrite",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"},
    )
    if bad_validate.returncode == 0:
        raise AssertionError("Expected --validate to fail on unknown type ids / count keys")
    ensure_contains(report_path, "Unknown type ids in types_present")
    ensure_contains(report_path, "not-a-real-type")
    ensure_contains(report_path, "ghost-count")
    bad_payload = json.loads(bad_validate.stdout)
    if not bad_payload.get("skeletons_skipped_due_to_validate"):
        raise AssertionError("Expected skeleton reconcile to be skipped when --validate fails")

    # Invalid type_counts must not silently become 1.
    invalid_annotation = dict(annotations["2021-期中-C"])
    invalid_annotation["types_present"] = ["matrix-rank", "eigen-decomp"]
    invalid_annotation["type_counts"] = {"matrix-rank": "many", "eigen-decomp": -2}
    (annotations_dir / "2021-期中-C.json").write_text(
        json.dumps(invalid_annotation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    skeleton_before = first_skeleton.read_text(encoding="utf-8")
    invalid_validate = subprocess.run(
        [
            sys.executable,
            "-B",
            str(STUDENT_OS_SCRIPTS / "build_exam_type_stats.py"),
            str(repo),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "期中",
            "--validate",
            "--overwrite",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"},
    )
    if invalid_validate.returncode == 0:
        raise AssertionError("Expected --validate to fail on invalid type_counts values")
    ensure_contains(report_path, "Invalid type_counts values")
    if first_skeleton.read_text(encoding="utf-8") != skeleton_before:
        raise AssertionError("Skeleton must not change when --validate fails")

    # Restore clean annotations after validation failure cases.
    for stem, payload in annotations.items():
        (annotations_dir / f"{stem}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    # Nested papers with the same basename must get distinct annotation ids.
    nested_root = exams_dir / "nested"
    (nested_root / "2019").mkdir(parents=True, exist_ok=True)
    (nested_root / "2020").mkdir(parents=True, exist_ok=True)
    (nested_root / "2019" / "paper.pdf.md").write_text("# nested 2019\n", encoding="utf-8", newline="\n")
    (nested_root / "2020" / "paper.pdf.md").write_text("# nested 2020\n", encoding="utf-8", newline="\n")
    nested_init = json.loads(
        run_script(
            "init_exam_census.py",
            str(repo),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "nested-midterm",
            "--papers-dir",
            "courses/linear-algebra/references/exams/nested",
            "--pattern",
            "**/*.pdf.md",
            "--overwrite",
        )
    )
    nested_manifest = Path(nested_init["manifest"])
    nested_stems = {item["stem"] for item in json.loads(nested_manifest.read_text(encoding="utf-8"))["papers"]}
    if nested_stems != {"2019__paper", "2020__paper"}:
        raise AssertionError(f"Expected path-namespaced annotation ids, got: {nested_stems}")

    # Semester-aware courses must not share census state.
    run_script("scaffold_course.py", str(repo), "Calculus II", "--semester", "2026 Fall")
    run_script("scaffold_course.py", str(repo), "Calculus II", "--semester", "2027 Spring")
    fall_exams = repo / "courses" / "2026-fall" / "calculus-ii" / "references" / "exams"
    spring_exams = repo / "courses" / "2027-spring" / "calculus-ii" / "references" / "exams"
    fall_exams.mkdir(parents=True, exist_ok=True)
    spring_exams.mkdir(parents=True, exist_ok=True)
    (fall_exams / "paper.pdf.md").write_text("# fall\n", encoding="utf-8", newline="\n")
    (spring_exams / "paper.pdf.md").write_text("# spring\n", encoding="utf-8", newline="\n")
    fall_init = json.loads(
        run_script(
            "init_exam_census.py",
            str(repo),
            "--course",
            "calculus-ii",
            "--semester",
            "2026 Fall",
            "--exam-scope",
            "期中",
            "--papers-dir",
            "courses/2026-fall/calculus-ii/references/exams",
        )
    )
    spring_init = json.loads(
        run_script(
            "init_exam_census.py",
            str(repo),
            "--course",
            "calculus-ii",
            "--semester",
            "2027 Spring",
            "--exam-scope",
            "期中",
            "--papers-dir",
            "courses/2027-spring/calculus-ii/references/exams",
        )
    )
    if fall_init["course"] != "2026-fall/calculus-ii" or spring_init["course"] != "2027-spring/calculus-ii":
        raise AssertionError(f"Expected semester-qualified course keys, got {fall_init['course']} / {spring_init['course']}")
    if Path(fall_init["state_dir"]) == Path(spring_init["state_dir"]):
        raise AssertionError("Semester-qualified courses must not share exam-census state directories")

    # Rank changes should retire obsolete generated skeletons.
    taxonomy_path.write_text(
        "\n".join(
            [
                "version: 1",
                'course: "Linear Algebra"',
                "exam_scope: 期中",
                "types:",
                "  - id: matrix-rank",
                "    name: 矩阵的秩",
                "    aliases: [秩, rank]",
                "    keywords: [秩, 行阶梯]",
                "  - id: eigen-decomp",
                "    name: 特征值与对角化",
                "    aliases: [特征值, diagonalize]",
                "    keywords: [特征值, 对角化]",
                "  - id: gaussian-elim",
                "    name: 高斯消元",
                "    aliases: [消元]",
                "    keywords: [高斯, 行变换]",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    for stem, payload in annotations.items():
        (annotations_dir / f"{stem}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    # Boost gaussian-elim above eigen-decomp by swapping one paper's second type.
    boosted = dict(annotations["2021-期中-C"])
    boosted["types_present"] = ["matrix-rank", "gaussian-elim"]
    boosted["type_counts"] = {"matrix-rank": 1, "gaussian-elim": 1}
    (annotations_dir / "2021-期中-C.json").write_text(
        json.dumps(boosted, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    rerank = json.loads(
        run_script(
            "build_exam_type_stats.py",
            str(repo),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "期中",
            "--overwrite",
        )
    )
    if [item["id"] for item in rerank["ranked_types"][:3]] != ["matrix-rank", "gaussian-elim", "eigen-decomp"]:
        raise AssertionError(f"Unexpected reranked order: {rerank['ranked_types']}")
    analysis_dir = repo / "courses" / "linear-algebra" / "reviews" / "期中" / "题型解析"
    ensure_exists(analysis_dir / "02-gaussian-elim.md")
    ensure_exists(analysis_dir / "03-eigen-decomp.md")
    if (analysis_dir / "02-eigen-decomp.md").exists():
        raise AssertionError("Obsolete ranked skeleton 02-eigen-decomp.md should be retired after rerank")

    # --validate should fail when an annotation is missing.
    (annotations_dir / "2021-期中-C.json").unlink()
    validate_result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(STUDENT_OS_SCRIPTS / "build_exam_type_stats.py"),
            str(repo),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "期中",
            "--validate",
            "--overwrite",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"},
    )
    if validate_result.returncode == 0:
        raise AssertionError("build_exam_type_stats.py --validate should fail when annotations are missing")
    # Restore annotation and rebuild final report for the example snapshot.
    for stem, payload in annotations.items():
        (annotations_dir / f"{stem}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    run_script(
        "build_exam_type_stats.py",
        str(repo),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期中",
        "--overwrite",
    )

    # Path-like exam_scope values must be rejected.
    for bad_scope in ("../escape", "", "C:\\windows"):
        bad_init = subprocess.run(
            [
                sys.executable,
                "-B",
                str(STUDENT_OS_SCRIPTS / "init_exam_census.py"),
                str(repo),
                "--course",
                "linear-algebra",
                "--exam-scope",
                bad_scope,
                "--papers-dir",
                "courses/linear-algebra/references/exams",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"},
        )
        if bad_init.returncode == 0:
            raise AssertionError(f"Expected init to reject exam_scope={bad_scope!r}")

    # Without --overwrite, existing skeletons must be skipped (not migrated/deleted).
    analysis_dir = repo / "courses" / "linear-algebra" / "reviews" / "期中" / "题型解析"
    existing_skeletons = sorted(path.name for path in analysis_dir.glob("*.md"))
    if not existing_skeletons:
        raise AssertionError("Expected skeletons before no-overwrite rebuild")
    no_overwrite = json.loads(
        run_script(
            "build_exam_type_stats.py",
            str(repo),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "期中",
        )
    )
    if not no_overwrite.get("skeletons_skipped"):
        raise AssertionError("Expected existing skeletons to be skipped without --overwrite")
    after_skeletons = sorted(path.name for path in analysis_dir.glob("*.md"))
    if after_skeletons != existing_skeletons:
        raise AssertionError(f"Skeletons changed without --overwrite: {existing_skeletons} -> {after_skeletons}")

    # User-edited skeletons (fingerprint mismatch) are archived, not deleted.
    user_skeleton = analysis_dir / existing_skeletons[-1]
    user_text = user_skeleton.read_text(encoding="utf-8") + "\n## User Notes\n\nKeep me.\n"
    user_skeleton.write_text(user_text, encoding="utf-8", newline="\n")
    user_type = None
    import re as _re

    match = _re.search(r'(?m)^exam_type_id:\s*"?([^"\n]+)"?\s*$', user_text)
    if match:
        user_type = match.group(1)
    if not user_type:
        raise AssertionError(f"Could not read exam_type_id from {user_skeleton}")
    # Drop that type from all annotations so it becomes obsolete and should archive.
    for stem, payload in annotations.items():
        cleaned = dict(payload)
        cleaned["types_present"] = [tid for tid in payload["types_present"] if tid != user_type]
        cleaned["type_counts"] = {
            key: value for key, value in payload["type_counts"].items() if key != user_type
        }
        if "matrix-rank" not in cleaned["types_present"]:
            cleaned["types_present"].append("matrix-rank")
            cleaned["type_counts"]["matrix-rank"] = 1
        (annotations_dir / f"{stem}.json").write_text(
            json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    run_script(
        "build_exam_type_stats.py",
        str(repo),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期中",
        "--overwrite",
    )
    if user_skeleton.exists():
        raise AssertionError("Edited obsolete skeleton should leave 题型解析/")
    archived = analysis_dir / "_archive" / user_skeleton.name
    ensure_exists(archived)
    ensure_contains(archived, "Keep me.")

    # Taxonomy JSON round-trip preserves string ids like "true" and comma-bearing names.
    utils_spec = importlib.util.spec_from_file_location(
        "exam_census_utils_smoke", STUDENT_OS_SCRIPTS / "exam_census_utils.py"
    )
    if utils_spec is None or utils_spec.loader is None:
        raise RuntimeError("Unable to load exam_census_utils for round-trip check")
    exam_census_utils = importlib.util.module_from_spec(utils_spec)
    sys.path.insert(0, str(STUDENT_OS_SCRIPTS))
    try:
        utils_spec.loader.exec_module(exam_census_utils)
    finally:
        if sys.path and sys.path[0] == str(STUDENT_OS_SCRIPTS):
            sys.path.pop(0)
    roundtrip_path = state_dir / "taxonomy-roundtrip.yaml"
    exam_census_utils.write_taxonomy(
        roundtrip_path,
        {
            "version": 1,
            "course": "Linear Algebra",
            "exam_scope": "期中",
            "types": [
                {"id": "true", "name": "A, B family", "aliases": ["x,y"], "keywords": ["a,b"]},
            ],
        },
    )
    loaded = exam_census_utils.load_taxonomy_yaml(roundtrip_path)
    if loaded["types"][0]["id"] != "true":
        raise AssertionError(f"Expected id 'true' string round-trip, got {loaded['types'][0]['id']!r}")
    if loaded["types"][0]["name"] != "A, B family":
        raise AssertionError(f"Expected comma-bearing name preserved, got {loaded['types'][0]['name']!r}")
    dumped = exam_census_utils.dump_taxonomy_yaml(loaded)
    if '"true"' not in dumped:
        raise AssertionError("Writer should JSON-quote the id true")

    # Paths with spaces must produce quoted Markdown hrefs.
    spaced = exams_dir / "mid term paper.pdf.md"
    spaced.write_text("# spaced\n", encoding="utf-8", newline="\n")
    spaced_init = json.loads(
        run_script(
            "init_exam_census.py",
            str(repo),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "spaced-scope",
            "--papers-dir",
            "courses/linear-algebra/references/exams",
            "--pattern",
            "mid term paper.pdf.md",
            "--overwrite",
        )
    )
    spaced_state = Path(spaced_init["state_dir"])
    (spaced_state / "taxonomy.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                'course: "Linear Algebra"',
                'exam_scope: "spaced-scope"',
                "types:",
                '  - id: "matrix-rank"',
                '    name: "矩阵的秩"',
                "    aliases: []",
                "    keywords: []",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    stem = "mid term paper"
    # annotation id from basename without .pdf.md
    (spaced_state / "annotations" / f"{stem}.json").write_text(
        json.dumps(
            {
                "source": "courses/linear-algebra/references/exams/mid term paper.pdf.md",
                "exam_label": "spaced",
                "types_present": ["matrix-rank"],
                "type_counts": {"matrix-rank": 1},
                "confidence": "high",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    # Fix annotation filename: annotation_id uses relative path
    spaced_manifest = json.loads((spaced_state / "manifest.json").read_text(encoding="utf-8"))
    spaced_stem = spaced_manifest["papers"][0]["stem"]
    (spaced_state / "annotations" / f"{stem}.json").rename(spaced_state / "annotations" / f"{spaced_stem}.json")
    run_script(
        "build_exam_type_stats.py",
        str(repo),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "spaced-scope",
        "--overwrite",
    )
    spaced_report = repo / "courses" / "linear-algebra" / "reviews" / "spaced-scope" / "题型频率统计.md"
    ensure_contains(spaced_report, "mid%20term%20paper.pdf.md")

    # Restore linear-algebra midterm annotations for any later consumers of this fixture.
    for stem, payload in annotations.items():
        (annotations_dir / f"{stem}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    # Phase A–E mechanical scripts (fill queue, quality gate, multi-dim, deep-dive, cross-val).
    run_script(
        "build_exam_type_stats.py",
        str(repo),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期中",
        "--validate",
        "--overwrite",
    )
    fill_payload = json.loads(
        run_script(
            "fill_type_analysis.py",
            str(repo),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "期中",
        )
    )
    if fill_payload.get("item_count", 0) < 1:
        raise AssertionError(f"Expected fill queue items, got: {fill_payload}")
    ensure_exists(state_dir / "fill-queue.json")
    fill_queue = json.loads((state_dir / "fill-queue.json").read_text(encoding="utf-8"))
    if fill_queue.get("quality_reference") != "references/exam-census-quality.md":
        raise AssertionError(f"Expected skill-relative quality_reference, got: {fill_queue.get('quality_reference')}")
    if not fill_queue["items"][0].get("source_papers"):
        raise AssertionError("Expected source_papers on fill-queue items")

    review_result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(STUDENT_OS_SCRIPTS / "review_type_analysis.py"),
            str(repo),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "期中",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"},
    )
    if review_result.returncode != 1:
        raise AssertionError(f"Expected Phase B exit code 1 for bare skeletons, got {review_result.returncode}")
    ensure_exists(state_dir / "quality-reviews.json")
    quality_report = json.loads((state_dir / "quality-reviews.json").read_text(encoding="utf-8"))
    if quality_report.get("needs_revision_count", 0) <= 0:
        raise AssertionError(f"Expected needs_revision_count > 0, got: {quality_report}")
    ensure_exists(repo / "courses" / "linear-algebra" / "reviews" / "期中" / "analysis" / "质量门禁.md")

    multi = json.loads(
        run_script(
            "build_multi_dim_stats.py",
            str(repo),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "期中",
            "--overwrite",
        )
    )
    if multi.get("pair_count", 0) < 1:
        raise AssertionError(f"Expected co-occurrence pairs from annotations, got: {multi}")
    ensure_exists(repo / "courses" / "linear-algebra" / "reviews" / "期中" / "analysis" / "题型关联分析.md")
    if multi.get("format_labels", {}).get("unspecified", 0) < 1:
        raise AssertionError(f"Expected unspecified format labels when annotations omit format: {multi}")

    deep = json.loads(
        run_script(
            "init_exam_deep_dive.py",
            str(repo),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "期中",
            "--limit",
            "2",
            "--overwrite",
        )
    )
    if not deep.get("written"):
        raise AssertionError(f"Expected Phase D deep-dive scaffolds, got: {deep}")
    deep_dir = repo / "courses" / "linear-algebra" / "reviews" / "期中" / "真题精析"
    ensure_exists(deep_dir)
    if not any(deep_dir.glob("*-精析.md")):
        raise AssertionError("Expected at least one deep-dive markdown under 真题精析/")

    cross = json.loads(
        run_script(
            "cross_validate_exam_census.py",
            str(repo),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "期中",
        )
    )
    if not cross.get("ok"):
        raise AssertionError(f"Expected clean cross-validation after census rebuild, got: {cross}")
    ensure_exists(repo / "courses" / "linear-algebra" / "reviews" / "期中" / "analysis" / "覆盖率检查.md")

    # Prep guide without real type links must fail Phase E.
    prep_guide = repo / "courses" / "linear-algebra" / "reviews" / "期中" / "备考指南.md"
    prep_guide.write_text(
        "\n".join(
            [
                "---",
                'course: "Linear Algebra"',
                "status: draft",
                "review_scope: exam-census",
                "---",
                "",
                "# Prep guide",
                "",
                "Study hard.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    linked_fail = subprocess.run(
        [
            sys.executable,
            "-B",
            str(STUDENT_OS_SCRIPTS / "cross_validate_exam_census.py"),
            str(repo),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "期中",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"},
    )
    if linked_fail.returncode == 0:
        raise AssertionError("Expected Phase E to fail when prep guide has no type links")
    prep_guide.unlink()

    # Platform adapters install into the vault (not the skill dir).
    adapter_payload = json.loads(
        run_script(
            "install_exam_census_adapters.py",
            str(repo),
            "--platforms",
            "claude,cursor,opencode,github",
            "--json",
        )
    )
    if adapter_payload.get("installed") != 4:
        raise AssertionError(f"Expected 4 adapters installed, got: {adapter_payload}")
    claude_wf = repo / ".claude" / "workflows" / "exam-census.js"
    cursor_rule = repo / ".cursor" / "rules" / "exam-census.mdc"
    ensure_exists(claude_wf)
    ensure_exists(cursor_rule)
    ensure_exists(repo / ".opencode" / "exam-census.md")
    ensure_exists(repo / ".github" / "copilot-exam-census.md")
    ensure_contains(claude_wf, "name: 'exam-census'")
    ensure_contains(claude_wf, "export const meta")
    ensure_contains(cursor_rule, "alwaysApply: false")
    ensure_contains(cursor_rule, "exam-census")
    # Second install without --force should skip.
    skip_payload = json.loads(
        run_script(
            "install_exam_census_adapters.py",
            str(repo),
            "--platforms",
            "claude",
            "--json",
        )
    )
    if skip_payload.get("skipped") != 1:
        raise AssertionError(f"Expected claude adapter skip on reinstall, got: {skip_payload}")


def exercise_feedback_lifecycle(repo: Path) -> None:
    feedback_day = date.today()
    expected_feedback_id = f'fb-{feedback_day.strftime("%Y%m%d")}-weekly-plan-omitted-imported-deadline-2'
    raw_path = Path(
        run_script(
            "log_feedback.py",
            str(repo),
            "--title",
            "Weekly plan omitted imported deadline",
            "--feedback-kind",
            "workflow",
            "--severity",
            "high",
            "--reproducibility",
            "always",
            "--source-context",
            "plan-week request after adding a linked homework task",
            "--related-artifacts",
            "tasks/weekly/current.md,tasks/deadlines/sample.md",
            "--related-roles",
            "coordinator,planning-assistant",
            "--what-happened",
            "- The generated weekly plan skipped a deadline that already existed in tasks/deadlines/.",
            "--expected-behavior",
            "- Weekly plans should include near-term deadline tasks alongside inbox and review items.",
            "--why-unsatisfying",
            "- The user still has to manually inspect deadlines after asking for a full weekly plan.",
            "--likely-cause",
            "- The planning workflow did not include imported deadline artifacts in the scan window.",
            "--suggested-improvement",
            "- Expand planning scans to include imported deadline artifacts before sorting upcoming work.",
            "--developer-summary",
            "- Planning scans need a regression check for imported or linked deadline artifacts.",
            "--evidence",
            "- tasks/weekly/current.md and tasks/deadlines/sample.md",
            "--follow-up",
            "Triage into the next planning iteration.",
        )
    )
    triaged_path = Path(
        run_script(
            "triage_feedback.py",
            str(repo),
            str(raw_path),
            "--feedback-kind",
            "workflow",
            "--severity",
            "high",
            "--reproducibility",
            "always",
            "--triage-status",
            "queued-for-planning",
            "--follow-up",
            "Bundle with the next planning workflow fix.",
            "--triage-notes",
            "- Confirmed the issue belongs to planning ingestion rather than task creation.",
        )
    )
    triaged_text = triaged_path.read_text(encoding="utf-8")
    triaged_text = triaged_text.replace('github_issue_url: ""', 'github_issue_url: "https://github.com/Gu-Heping/college-student-workflow/issues/42"')
    triaged_text = triaged_text.replace('github_issue_number: ""', 'github_issue_number: "42"')
    triaged_text = triaged_text.replace('github_issue_status: ""', 'github_issue_status: "open"')
    triaged_text = triaged_text.replace('reported_to_github_at: ""', 'reported_to_github_at: "2026-07-16"')
    triaged_path.write_text(triaged_text, encoding="utf-8", newline="\n")
    resolved_path = Path(
        run_script(
            "resolve_feedback.py",
            str(repo),
            str(triaged_path),
            "--resolution-summary",
            "- Added planning regression coverage so imported deadlines appear in weekly plan summaries.",
            "--fix-version",
            "0.7.0",
            "--changelog-note",
            "- Weekly plans now preserve imported and linked deadline tasks in the upcoming-work scan.",
            "--follow-up",
            "Verify once against a real imported-deadline workflow.",
        )
    )
    second_raw_path = Path(
        run_script(
            "log_feedback.py",
            str(repo),
            "--title",
            "Weekly plan omitted imported deadline",
            "--feedback-kind",
            "workflow",
            "--severity",
            "medium",
            "--reproducibility",
            "sometimes",
            "--source-context",
            "second collision test",
            "--developer-summary",
            "- This duplicate entry should keep a unique filename and feedback_id.",
        )
    )
    second_triaged_path = Path(
        run_script(
            "triage_feedback.py",
            str(repo),
            str(second_raw_path),
            "--triage-status",
            "needs-dedup-review",
            "--triage-notes",
            "- Collision handling preserved the older resolved item.",
        )
    )
    quoted_text = second_triaged_path.read_text(encoding="utf-8")
    quoted_text = quoted_text.replace("status: triaged", 'status: "triaged"')
    quoted_text = quoted_text.replace("severity: medium", 'severity: "medium"')
    second_triaged_path.write_text(quoted_text, encoding="utf-8", newline="\n")
    outside_path = repo.parent / "outside-feedback.md"
    outside_path.write_text("---\nstatus: open\n---\n", encoding="utf-8", newline="\n")
    failure_output = run_script_failure("triage_feedback.py", str(repo), str(outside_path))
    summary_path = Path(
        run_script(
            "summarize_feedback.py",
            str(repo),
            "--title",
            "Developer feedback handoff",
            "--scope",
            "smoke-test",
            "--audience",
            "developer",
        )
    )

    ensure_exists(resolved_path)
    ensure_contains(resolved_path, "feedback_id:")
    ensure_contains(resolved_path, 'github_issue_url: "https://github.com/Gu-Heping/college-student-workflow/issues/42"')
    ensure_contains(resolved_path, 'github_issue_number: "42"')
    ensure_contains(resolved_path, 'github_issue_status: "open"')
    ensure_contains(resolved_path, 'reported_to_github_at: "2026-07-16"')
    ensure_contains(resolved_path, "## Triage Notes")
    ensure_contains(resolved_path, "## Resolution Summary")
    ensure_contains(second_triaged_path, f'feedback_id: "{expected_feedback_id}"')
    ensure_contains(summary_path, "## Developer Handoff")
    ensure_contains(summary_path, "0.7.0")
    ensure_contains(summary_path, "- Triaged items: 1")
    ensure_contains(summary_path, expected_feedback_id)
    if "must stay under" not in failure_output:
        raise AssertionError(f"Expected path-guard failure, got: {failure_output}")

    archive_feedback = Path(
        run_script(
            "log_feedback.py",
            str(repo),
            "--title",
            "Archive should not fake GitHub status",
            "--feedback-kind",
            "docs",
            "--severity",
            "low",
            "--developer-summary",
            "- Archive status should preserve any known GitHub issue state.",
        )
    )
    archived_text = archive_feedback.read_text(encoding="utf-8")
    archived_text = archived_text.replace('github_issue_url: ""', 'github_issue_url: "https://github.com/Gu-Heping/college-student-workflow/issues/77"')
    archived_text = archived_text.replace('github_issue_number: ""', 'github_issue_number: "77"')
    archived_text = archived_text.replace('github_issue_status: ""', 'github_issue_status: "open"')
    archive_feedback.write_text(archived_text, encoding="utf-8", newline="\n")
    archived_path = Path(
        run_script(
            "resolve_feedback.py",
            str(repo),
            str(archive_feedback),
            "--status",
            "archived",
            "--resolution-summary",
            "- Archived locally without changing the public issue state.",
        )
    )
    ensure_contains(archived_path, 'github_issue_status: "open"')

    github_issue_feedback = Path(
        run_script(
            "log_feedback.py",
            str(repo),
            "--title",
            r"Privacy check D:\vault\notes.md sk-proj-1234567890-ABCDEFGHIJKLMNOPQRST",
            "--feedback-kind",
            "install",
            "--severity",
            "high",
            "--source-context",
            r"Codex on Windows with installed version: D:\vault\private-course\version-secret.txt and /Users/alice/My Vault/notes.md",
            "--related-artifacts",
            r"D:\vault\private-course\notes.md,.env,/Users/alice/private-notes.md",
            "--related-roles",
            "feedback-operator,codex",
            "--what-happened",
            "- The installer exposed a private path from D:\\vault\\private-course\\notes.md, C:\\Users\\Alice\\My Vault\\notes.md and /Users/alice/private-notes.md.",
            "--expected-behavior",
            "- Public reports should redact private Windows paths and vault references.",
            "--evidence",
            "- D:\\vault\\private-course\\notes.md\n- C:\\Users\\Alice\\My Vault\\notes.md\n- /Users/alice/My Vault/notes.md\n- .env.local: DATABASE_URL=postgres://secret@example\n- password: \"correct horse battery staple\"\n- sk-proj-1234567890-ABCDEFGHIJKLMNOPQRST\n- github_pat_1234567890ABCDEFGHIJKLMNOP\n- eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature\n- +1 555-123-4567",
        )
    )
    issue_payload = json.loads(
        run_script(
            "prepare_github_issue.py",
            str(repo),
            str(github_issue_feedback),
        )
    )
    if issue_payload["feedback_id"] == "":
        raise AssertionError("prepare_github_issue.py should include feedback_id in its JSON output")
    if issue_payload["labels"] != ["feedback", "feedback:install", "severity:high"]:
        raise AssertionError("prepare_github_issue.py should derive labels from feedback kind and severity")
    if "## Feedback ID" not in issue_payload["body"] or "## Privacy Check" not in issue_payload["body"]:
        raise AssertionError("prepare_github_issue.py should emit the expected issue body sections")
    if "## Completeness Check" not in issue_payload["body"] or "## Environment" not in issue_payload["body"]:
        raise AssertionError("prepare_github_issue.py should emit completeness and environment sections")
    for leaked_text in [
        r"D:\vault\private-course\notes.md",
        r"C:\Users\Alice\My Vault\notes.md",
        "/Users/alice/private-notes.md",
        "/Users/alice/My Vault/notes.md",
        "sk-proj-1234567890-ABCDEFGHIJKLMNOPQRST",
        "github_pat_1234567890ABCDEFGHIJKLMNOP",
        "version-secret.txt",
        "DATABASE_URL=postgres://secret@example",
        "correct horse battery staple",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature",
        "+1 555-123-4567",
        "d-vault-private-course",
        "my-vault-notes",
    ]:
        if leaked_text in issue_payload["body"]:
            raise AssertionError(f"prepare_github_issue.py should redact sensitive text from public issue bodies: {leaked_text}")
    for redacted_marker in [
        "[REDACTED_WINDOWS_PATH]",
        "[REDACTED_UNIX_PATH]",
        "[REDACTED_TOKEN]",
        "[REDACTED_JWT]",
        "[REDACTED_PHONE]",
        "[REDACTED_ENV_FILE]",
    ]:
        if redacted_marker not in issue_payload["body"]:
            raise AssertionError(f"prepare_github_issue.py should include redaction marker {redacted_marker}")
    joined_warnings = "\n".join(issue_payload["privacy_warnings"])
    for expected_warning in ["Windows absolute paths", "Unix-style absolute paths", ".env", "token-like strings", "private vault path"]:
        if expected_warning not in joined_warnings:
            raise AssertionError(f"Expected privacy warning containing {expected_warning!r}, got: {joined_warnings}")
    joined_blockers = "\n".join(issue_payload["privacy_blockers"])
    for expected_blocker in ["secret-like key/value", "JWT-like tokens", "phone-number-like"]:
        if expected_blocker not in joined_blockers:
            raise AssertionError(f"Expected privacy blocker containing {expected_blocker!r}, got: {joined_blockers}")
    if not issue_payload["sanitized"]:
        raise AssertionError("prepare_github_issue.py should mark sanitized drafts")
    if not isinstance(issue_payload["completeness_warnings"], list):
        raise AssertionError("prepare_github_issue.py should return completeness warnings as a list")
    if "fb-public-" not in issue_payload["title"] or "fb-public-" not in issue_payload["body"]:
        raise AssertionError("prepare_github_issue.py should use a neutral public feedback identifier")
    if "- Python: unknown" not in issue_payload["body"]:
        raise AssertionError("prepare_github_issue.py should leave Python version as unknown unless the feedback explicitly captured it")

    stdin_safe = run_script_with_stdin(
        "prepare_github_issue.py",
        "Repro notes for a generic workflow failure without secrets.\n",
        "--stdin",
    )
    if "Repro notes for a generic workflow failure without secrets." not in stdin_safe.stdout:
        raise AssertionError("prepare_github_issue.py --stdin should pass through safe issue drafts")
    if stdin_safe.stderr.strip():
        raise AssertionError("prepare_github_issue.py --stdin should stay quiet for safe drafts")

    stdin_warning_held = run_script_with_stdin(
        "prepare_github_issue.py",
        "Saw a failure while reading C:\\Users\\Alice\\notes.md during import.\n",
        "--stdin",
        check=False,
    )
    if stdin_warning_held.returncode == 0:
        raise AssertionError("prepare_github_issue.py --stdin should hold back warning-bearing drafts without --allow-privacy-warnings")
    if stdin_warning_held.stdout.strip():
        raise AssertionError("prepare_github_issue.py --stdin should not emit stdout when warnings are held back")
    if "WARN:" not in stdin_warning_held.stderr or "Windows absolute paths" not in stdin_warning_held.stderr:
        raise AssertionError("prepare_github_issue.py --stdin should emit WARN lines for privacy warnings")

    stdin_warning = run_script_with_stdin(
        "prepare_github_issue.py",
        "Saw a failure while reading C:\\Users\\Alice\\notes.md during import.\n",
        "--stdin",
        "--allow-privacy-warnings",
    )
    if "[REDACTED_WINDOWS_PATH]" not in stdin_warning.stdout:
        raise AssertionError("prepare_github_issue.py --stdin --allow-privacy-warnings should redact Windows paths in stdout")
    if "C:\\Users\\Alice\\notes.md" in stdin_warning.stdout:
        raise AssertionError("prepare_github_issue.py --stdin should not leave absolute Windows paths in stdout")
    if "WARN:" not in stdin_warning.stderr or "Windows absolute paths" not in stdin_warning.stderr:
        raise AssertionError("prepare_github_issue.py --stdin should emit WARN lines for privacy warnings")

    stdin_blocker = run_script_with_stdin(
        "prepare_github_issue.py",
        "password: \"correct horse battery staple\"\n",
        "--stdin",
        check=False,
    )
    if stdin_blocker.returncode == 0:
        raise AssertionError("prepare_github_issue.py --stdin should abort when privacy blockers are present")
    if "BLOCK:" not in stdin_blocker.stderr:
        raise AssertionError("prepare_github_issue.py --stdin should emit BLOCK lines for privacy blockers")
    if stdin_blocker.stdout.strip():
        raise AssertionError("prepare_github_issue.py --stdin should not emit sanitized stdout when blockers abort publishing")

    stdin_check = run_script_with_stdin(
        "prepare_github_issue.py",
        "password: \"correct horse battery staple\"\n",
        "--stdin",
        "--check-only",
        check=False,
    )
    if stdin_check.returncode == 0:
        raise AssertionError("prepare_github_issue.py --stdin --check-only should exit non-zero for blockers")
    if "BLOCK:" not in stdin_check.stderr:
        raise AssertionError("prepare_github_issue.py --stdin --check-only should report blockers on stderr")
    if stdin_check.stdout.strip():
        raise AssertionError("prepare_github_issue.py --stdin --check-only should not rewrite the draft")

    stdin_json = run_script_with_stdin(
        "prepare_github_issue.py",
        json.dumps({"body": "Contact me at alice@example.com about the vault at /Users/alice/My Vault/notes.md\n"}),
        "--stdin",
        "--stdin-format",
        "json",
        "--allow-privacy-warnings",
    )
    if "[REDACTED_EMAIL]" not in stdin_json.stdout or "[REDACTED_UNIX_PATH]" not in stdin_json.stdout:
        raise AssertionError("prepare_github_issue.py --stdin-format json should sanitize the body field")
    if "alice@example.com" in stdin_json.stdout or "/Users/alice/My Vault/notes.md" in stdin_json.stdout:
        raise AssertionError("prepare_github_issue.py --stdin-format json should not leak original sensitive body text")

    stdin_json_title_check = run_script_with_stdin(
        "prepare_github_issue.py",
        json.dumps({"title": "password: hunter2 leaked", "body": "Harmless body describing a workflow bug.\n"}),
        "--stdin",
        "--stdin-format",
        "json",
        "--check-only",
        check=False,
    )
    if stdin_json_title_check.returncode == 0:
        raise AssertionError("prepare_github_issue.py --stdin-format json --check-only should scan the title field for blockers")
    if "BLOCK:" not in stdin_json_title_check.stderr:
        raise AssertionError("prepare_github_issue.py --stdin-format json --check-only should report title blockers on stderr")

    stdin_json_title = run_script_with_stdin(
        "prepare_github_issue.py",
        json.dumps({"title": "Bug hit while reading C:\\Users\\Bob\\notes.md", "body": "Body without sensitive data.\n"}),
        "--stdin",
        "--stdin-format",
        "json",
        "--allow-privacy-warnings",
    )
    title_payload = json.loads(stdin_json_title.stdout)
    if "[REDACTED_WINDOWS_PATH]" not in title_payload["title"]:
        raise AssertionError("prepare_github_issue.py --stdin-format json should sanitize the title field")
    if "C:\\Users\\Bob\\notes.md" in stdin_json_title.stdout:
        raise AssertionError("prepare_github_issue.py --stdin-format json should not leak the original title path")
    if title_payload["body"].strip() != "Body without sensitive data.":
        raise AssertionError("prepare_github_issue.py --stdin-format json should preserve the sanitized body alongside the title")

    privacy_blocked_payload = json.loads(
        run_path_script(
            STUDENT_OS_SCRIPTS / "publish_github_issue.py",
            str(repo),
            str(github_issue_feedback),
            "--github-repo",
            "Gu-Heping/college-student-workflow",
            "--json",
            cwd=repo,
            env={"PATH": ""},
        )
    )
    if privacy_blocked_payload["published"]:
        raise AssertionError("publish_github_issue.py should not publish feedback with privacy warnings by default")
    if privacy_blocked_payload["blocked_reason"] != "privacy-blockers":
        raise AssertionError("publish_github_issue.py should report privacy-blockers when blocking sensitive data is present")
    if "--allow-privacy-warnings" in privacy_blocked_payload["next_step"]:
        raise AssertionError("publish_github_issue.py should not suggest overriding blocking sensitive data")
    if "gh_command" in privacy_blocked_payload:
        raise AssertionError("publish_github_issue.py should not emit a runnable gh command for blocker-only drafts")
    privacy_blocked_stdout = run_script(
        "publish_github_issue.py",
        str(repo),
        str(github_issue_feedback),
        "--github-repo",
        "Gu-Heping/college-student-workflow",
    )
    if "Publishing blocked due to privacy warnings." not in privacy_blocked_stdout:
        raise AssertionError("Non-JSON blocking output should still explain that publishing was blocked")
    if "gh issue create" in privacy_blocked_stdout:
        raise AssertionError("Non-JSON privacy blocking output should not print a ready-to-run publish command")

    publish_failure = json.loads(
        run_script(
            "publish_github_issue.py",
            str(repo),
            str(resolved_path),
            "--github-repo",
            "Gu-Heping/college-student-workflow",
            "--json",
        )
    )
    if publish_failure["blocked_reason"] != "already-linked":
        raise AssertionError("publish_github_issue.py should refuse duplicate publication for already-linked feedback")
    if publish_failure["existing_issue_number"] != "42":
        raise AssertionError("publish_github_issue.py should surface the existing linked issue metadata")

    manual_feedback = repo / "feedback" / "triaged" / "manual-path-feedback.md"
    manual_feedback.write_text(
        "\n".join(
            [
                "---",
                'type: "feedback"',
                'status: "triaged"',
                f'created: "{feedback_day.isoformat()}"',
                f'updated: "{feedback_day.isoformat()}"',
                'tags: ["feedback"]',
                'feedback_id: "../../notes/leak"',
                'feedback_kind: "other"',
                'severity: "medium"',
                'reproducibility: "sometimes"',
                'source_context: "manual import"',
                'related_course: ""',
                'related_artifacts: ""',
                'related_roles: "feedback-operator"',
                'github_issue_url: ""',
                'github_issue_number: ""',
                'github_issue_status: ""',
                'reported_to_github_at: ""',
                "---",
                "",
                "# Feedback - Manual path $(danger) `tick` test",
                "",
                "## What Happened",
                "",
                "- Fallback issue body generation should stay inside feedback/summaries.",
                "",
                "## Expected Behavior",
                "",
                "- Draft issue body should use a safe filename.",
                "",
                "## Why This Was Unsatisfying",
                "",
                "- Path traversal in feedback_id should not escape the summaries directory.",
                "",
                "## Likely Cause",
                "",
                "- The fallback body path trusted frontmatter directly.",
                "",
                "## Suggested Improvement",
                "",
                "- Normalize feedback IDs before using them in filenames.",
                "",
                "## Evidence",
                "",
                "- Manual path traversal test.",
                "",
                "## Follow-up",
                "",
                "- Confirm the generated draft body lives under feedback/summaries.",
                "",
            ]
        ) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    publish_payload = json.loads(
        run_path_script(
            STUDENT_OS_SCRIPTS / "publish_github_issue.py",
            str(repo),
            str(manual_feedback),
            "--github-repo",
            "Gu-Heping/college-student-workflow",
            "--json",
            cwd=repo,
            env={"PATH": ""},
        )
    )
    if publish_payload["published"]:
        raise AssertionError("publish_github_issue.py fallback path should not publish when gh is unavailable")
    if publish_payload["blocked_reason"] != "gh-unavailable":
        raise AssertionError("publish_github_issue.py should distinguish gh-unavailable fallback from privacy blocking")
    body_path = repo / publish_payload["body_path"]
    ensure_exists(body_path)
    try:
        body_path.relative_to(repo / "feedback" / "summaries")
    except ValueError as exc:
        raise AssertionError("Fallback GitHub issue body should stay inside feedback/summaries") from exc
    if body_path.name != "manual-path-feedback-github-issue-body.md":
        raise AssertionError("Fallback body file should use a unique source-based name when feedback_id is unsafe or empty")
    gh_command = publish_payload["gh_command"]
    if "../../notes/leak" in gh_command:
        raise AssertionError("Fallback gh command should not expose the raw feedback_id once a neutral public ID is used")
    if "fb-public-" not in gh_command:
        raise AssertionError("Fallback gh command should use the neutral public feedback identifier in issue titles")
    if "--label" in gh_command:
        raise AssertionError("Fallback gh command should omit labels when the repo label set cannot be verified")
    if publish_payload["omitted_labels"] != ["feedback", "feedback:other", "severity:medium"]:
        raise AssertionError("publish_github_issue.py should report labels omitted from fallback publication guidance")

    single_quote_feedback = repo / "feedback" / "triaged" / "single-quote-empty-issue-fields.md"
    single_quote_feedback.write_text(
        "\n".join(
            [
                "---",
                "type: 'feedback'",
                "status: 'triaged'",
                f"created: '{feedback_day.isoformat()}'",
                f"updated: '{feedback_day.isoformat()}'",
                "tags: ['feedback']",
                "feedback_id: 'single-quote-empty'",
                "feedback_kind: 'docs'",
                "severity: 'low'",
                "reproducibility: 'sometimes'",
                "source_context: 'single quote empty metadata'",
                "related_course: ''",
                "related_artifacts: ''",
                "related_roles: 'feedback-operator'",
                "github_issue_url: ''",
                "github_issue_number: ''",
                "github_issue_status: ''",
                "reported_to_github_at: ''",
                "---",
                "",
                "# Feedback - Single quote empty fields",
                "",
                "## What Happened",
                "",
                "- Empty quoted GitHub fields should not block first-time publish preparation.",
                "",
                "## Expected Behavior",
                "",
                "- The publish helper should treat '' as empty metadata.",
                "",
                "## Why This Was Unsatisfying",
                "",
                "- Migrated feedback can otherwise be misclassified as already linked.",
                "",
                "## Likely Cause",
                "",
                "- Duplicate detection only stripped double quotes.",
                "",
                "## Suggested Improvement",
                "",
                "- Normalize scalar issue metadata before duplicate checks.",
                "",
                "## Evidence",
                "",
                "- Manual migrated feedback fixture.",
                "",
                "## Follow-up",
                "",
                "- Confirm fallback preparation succeeds without gh.",
                "",
            ]
        ) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    single_quote_payload = json.loads(
        run_path_script(
            STUDENT_OS_SCRIPTS / "publish_github_issue.py",
            str(repo),
            str(single_quote_feedback),
            "--github-repo",
            "Gu-Heping/college-student-workflow",
            "--json",
            cwd=repo,
            env={"PATH": ""},
        )
    )
    if single_quote_payload["published"]:
        raise AssertionError("Single-quoted empty GitHub issue fields should not force a publish path")
    if single_quote_payload["blocked_reason"] != "gh-unavailable":
        raise AssertionError("Single-quoted empty GitHub metadata should still allow draft preparation")


def build_single_semester(repo: Path, today: date) -> None:
    due_date = (today + timedelta(days=8)).isoformat()
    default_week_label = f"{today.isoformat()}-plus-7d"
    run_script("scaffold_repo.py", str(repo))
    run_script("scaffold_course.py", str(repo), "Linear Algebra")
    run_script("scaffold_homework.py", str(repo), "linear-algebra", "Worksheet A", "--due", due_date)
    seed_planning_inputs(repo, today)
    run_script("build_review_indexes.py", str(repo))
    exercise_feedback_lifecycle(repo)
    exercise_import_workflows(repo)
    exercise_exam_census(repo)
    run_script("build_review_indexes.py", str(repo))
    run_script("build_week_plan.py", str(repo))
    ensure_contains(repo / "tasks" / "weekly" / f"{default_week_label}.md", "Linear Algebra Midterm")
    ensure_contains(repo / "tasks" / "weekly" / f"{default_week_label}.md", "courses/linear-algebra/dashboard.md")
    default_plan_text = (repo / "tasks" / "weekly" / f"{default_week_label}.md").read_text(encoding="utf-8")
    if "- `linear-algebra` -> prioritize Worksheet A" in default_plan_text:
        raise AssertionError("Course actions should not prioritize out-of-window homework in the default weekly plan")
    if "- `linear-algebra` -> prioritize Linear Algebra Midterm" in default_plan_text:
        raise AssertionError("Course actions should not prioritize out-of-window exam tasks in the default weekly plan")
    (repo / "tasks" / "weekly" / f"{default_week_label}.md").unlink()
    (repo / "dashboards" / "weekly" / f"{default_week_label}.md").unlink()
    run_script("build_week_plan.py", str(repo), "--days", "14")
    run_script("rebuild_indexes.py", str(repo))

    ensure_exists(repo / "courses" / "linear-algebra" / "index.md")
    ensure_exists(repo / "courses" / "linear-algebra" / "homework" / "worksheet-a.md")
    ensure_contains(repo / ".student-os" / "index" / "courses.md", "courses/linear-algebra")
    ensure_contains(repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-14d.md", "## Overdue Carryover")
    ensure_contains(repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-14d.md", "Linear Algebra Midterm")
    ensure_contains(repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-14d.md", "Imported Materials To Curate")
    ensure_contains(repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-14d.md", "courses/linear-algebra/references/outline-import.md")
    ensure_contains(repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-14d.md", "courses/linear-algebra/dashboard.md")
    weekly_plan_text = (repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-14d.md").read_text(encoding="utf-8")
    ensure_contains(
        repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-14d.md",
        f"- `linear-algebra` -> prioritize Linear Algebra Overdue Reading ({(today - timedelta(days=2)).isoformat()})",
    )
    if "manual-repair-sample-repair-summary.md" in weekly_plan_text:
        raise AssertionError("Repair summaries should not appear in imported-material triage")
    dashboard_exam_line = f"{(today + timedelta(days=9)).isoformat()} :: courses/linear-algebra/dashboard.md"
    task_exam_line = f"{(today + timedelta(days=10)).isoformat()} :: Linear Algebra Midterm"
    exams_section = weekly_plan_text.split("## Exams And Countdowns", 1)[1].split("## Course Actions", 1)[0]
    if exams_section.index(task_exam_line) < exams_section.index(dashboard_exam_line):
        raise AssertionError("Exam countdowns should be sorted chronologically across tasks and dashboard signals")
    if "Archived Quiz" in (repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-14d.md").read_text(encoding="utf-8"):
        raise AssertionError("Archived tasks should not be listed in the weekly plan")
    ensure_contains(repo / "dashboards" / "weekly" / f"{today.isoformat()}-plus-14d.md", "Imported materials to review")
    ensure_contains(repo / ".student-os" / "index" / "dashboards.md", f"dashboards/weekly/{today.isoformat()}-plus-14d.md")


def build_repo_inside_weekly_parent(repo: Path, today: date) -> None:
    run_script("scaffold_repo.py", str(repo))
    run_script("scaffold_course.py", str(repo), "Signals")
    write_task_fixture(
        repo / "tasks" / "deadlines" / "signals-quiz.md",
        title="Signals Quiz",
        due=(today + timedelta(days=3)).isoformat(),
        area="exam",
        priority="high",
        course="Signals",
        tags="[task, exam]",
    )
    run_script("build_week_plan.py", str(repo))
    ensure_contains(repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-7d.md", "Signals Quiz")


def build_multi_semester(repo: Path, today: date) -> None:
    due_date = (today + timedelta(days=7)).isoformat()
    run_script("scaffold_repo.py", str(repo))
    run_script("scaffold_course.py", str(repo), "CS 101", "--semester", "2026 Fall")
    run_script("scaffold_course.py", str(repo), "Calculus II", "--semester", "2026 Fall")
    run_script("scaffold_course.py", str(repo), "CS 101", "--semester", "2027 Spring")
    run_script("scaffold_course.py", str(repo), "Data & Models", "--semester", "2026 Fall")
    run_script("scaffold_course.py", str(repo), "Data & Models", "--semester", "2027 Spring")
    run_script(
        "scaffold_homework.py",
        str(repo),
        "2026-fall/cs-101",
        "Problem Set 1",
        "--due",
        due_date,
    )
    write_task_fixture(
        repo / "tasks" / "deadlines" / "problem-set-1.md",
        title="Manual CS 101 checkpoint",
        due=due_date,
        area="homework",
        priority="medium",
        course="CS 101",
        course_link="../../courses/2026-fall/cs-101/index.md",
    )
    write_task_fixture(
        repo / "tasks" / "deadlines" / "2026-fall-data-models-reading.md",
        title="Data & Models reading",
        due=due_date,
        area="review",
        priority="medium",
        course="Data & Models",
    )
    write_task_fixture(
        repo / "tasks" / "deadlines" / "problem-set-2.md",
        title="Ambiguous CS 101 follow-up",
        due=due_date,
        area="homework",
        priority="medium",
        course="CS 101",
    )
    run_script("build_review_indexes.py", str(repo))
    run_script("build_week_plan.py", str(repo), "--days", "14")
    run_script("rebuild_indexes.py", str(repo))

    ensure_exists(repo / "semesters" / "2026-fall" / "overview.md")
    ensure_exists(repo / "tasks" / "deadlines" / "2026-fall-cs-101-problem-set-1.md")
    ensure_contains(repo / ".student-os" / "repo-profile.md", "enabled: true")
    ensure_contains(repo / "semesters" / "2026-fall" / "overview.md", "[CS 101]")
    ensure_contains(repo / ".student-os" / "index" / "courses.md", "courses/2026-fall/cs-101")
    ensure_contains(
        repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-14d.md",
        "- `2026-fall/cs-101` -> prioritize CS 101 - Problem Set 1",
    )
    ensure_contains(
        repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-14d.md",
        "- `2026-fall/data-models` -> prioritize Data & Models reading",
    )
    if "- `2027-spring/cs-101` -> prioritize CS 101 - Problem Set 1" in (
        repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-14d.md"
    ).read_text(encoding="utf-8"):
        raise AssertionError("Duplicate course titles across semesters should not steal another semester's deadline priority")
    if "- `2027-spring/data-models` -> prioritize Data & Models reading" in (
        repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-14d.md"
    ).read_text(encoding="utf-8"):
        raise AssertionError("Duplicate normalized titles should not steal another semester's title-based priority")
    if "Ambiguous CS 101 follow-up" in (
        repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-14d.md"
    ).read_text(encoding="utf-8").split("## Course Actions", 1)[1].split("## Review Targets", 1)[0]:
        raise AssertionError("Ambiguous unscoped duplicate-course tasks should stay out of course-action prioritization")


def verify_chinese_slug_support(repo: Path, today: date) -> None:
    due_date = (today + timedelta(days=6)).isoformat()
    run_script("scaffold_repo.py", str(repo))
    course_path = Path(run_script("scaffold_course.py", str(repo), "模电", "--semester", "2026 春"))
    if course_path.relative_to(repo).as_posix() != "courses/2026-春/模电":
        raise AssertionError("Chinese semester and course names should produce stable unicode-aware course paths")
    run_script(
        "scaffold_homework.py",
        str(repo),
        "2026-春/模电",
        "第 1 次作业",
        "--due",
        due_date,
    )
    ensure_exists(repo / "courses" / "2026-春" / "模电" / "homework" / "第-1-次作业.md")
    ensure_exists(repo / "courses" / "2026-春" / "模电" / "homework" / "第-1-次作业-solution.md")
    ensure_exists(repo / "tasks" / "deadlines" / "2026-春-模电-第-1-次作业.md")
    ensure_contains(repo / ".student-os" / "repo-profile.md", "enabled: true")
    ensure_contains(repo / "semesters" / "2026-春" / "overview.md", "[模电]")
    run_script("build_week_plan.py", str(repo), "--days", "14")
    ensure_contains(
        repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-14d.md",
        "- `2026-春/模电` -> prioritize 模电 - 第 1 次作业",
    )
    hindi_course_path = Path(
        run_script("scaffold_course.py", str(repo), "हिन्दी", "--semester", "2026 वसंत")
    )
    if hindi_course_path.relative_to(repo).as_posix() != "courses/2026-वसंत/हिन्दी":
        raise AssertionError("Unicode slugs should preserve combining marks for non-Latin scripts")


def build_legacy_layout(repo: Path, today: date) -> None:
    due_date = (today + timedelta(days=9)).isoformat()
    weekly_plan = repo / "tasks" / "weekly" / f"{today.isoformat()}-plus-14d.md"
    task_path = repo / "tasks" / "deadlines" / "legacy-course-legacy-sheet.md"
    run_script("scaffold_repo.py", str(repo))
    legacy_course = repo / "courses" / "legacy-course"
    (legacy_course / "homework").mkdir(parents=True, exist_ok=True)
    (legacy_course / "reviews").mkdir(parents=True, exist_ok=True)

    run_script("scaffold_homework.py", str(repo), "legacy-course", "Legacy Sheet", "--due", due_date)
    rewrite_legacy_task_link(task_path)
    run_script("build_review_indexes.py", str(repo))
    run_script("build_week_plan.py", str(repo), "--days", "14")

    ensure_exists(legacy_course / "homework" / "legacy-sheet.md")
    ensure_contains(repo / ".student-os" / "index" / "homework-and-reviews.md", "legacy-sheet.md")
    ensure_contains(weekly_plan, "legacy-course")
    ensure_contains(task_path, "legacy course folder without generated course home")


def verify_inspect_repo(repo: Path) -> None:
    payload = json.loads(run_script("inspect_repo.py", str(repo)))
    if "semesters" not in payload["canonical_dirs_present"]:
        raise AssertionError("inspect_repo.py did not report semesters as a canonical directory")
    if payload["dirty_files"]:
        raise AssertionError(f"Expected no dirty files in smoke-test repo, found: {payload['dirty_files']}")
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Smoke Test"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "smoke@example.com"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "baseline"], check=True, capture_output=True, text=True)
    (repo / "tasks" / "deadlines" / "linear-algebra.sync-conflict-20260710.md").write_text(
        "# conflict copy\n",
        encoding="utf-8",
        newline="\n",
    )
    (repo / ".obsidian").mkdir(parents=True, exist_ok=True)
    (repo / ".obsidian" / "workspace.json").write_text("{}", encoding="utf-8", newline="\n")
    (repo / "__pycache__").mkdir(parents=True, exist_ok=True)
    (repo / "__pycache__" / "inspect_repo.cpython-310.pyc").write_bytes(b"\0PYCCACHE")
    (repo / "tmp").mkdir(parents=True, exist_ok=True)
    (repo / "tmp" / "scratch.log").write_text("temporary scratch\n", encoding="utf-8", newline="\n")
    (repo / "references" / "textbooks").mkdir(parents=True, exist_ok=True)
    (repo / "references" / "textbooks" / "linear-algebra-textbook.pdf").write_bytes(b"%PDF-1.4\n")
    (repo / "references" / "slides").mkdir(parents=True, exist_ok=True)
    (repo / "references" / "slides" / "week-1-capture.mp4").write_bytes(b"fake-binary")
    (repo / "references" / "imports" / "raw").mkdir(parents=True, exist_ok=True)
    (repo / "references" / "imports" / "raw" / "ocr-dump.txt").write_text(
        "x" * (10 * 1024 * 1024 + 1),
        encoding="utf-8",
        newline="\n",
    )
    broken_link_supported = True
    broken_link = repo / "references" / "imports" / "raw" / "broken-link.txt"
    try:
        broken_link.symlink_to(repo / "references" / "imports" / "raw" / "missing-target.txt")
    except OSError:
        broken_link_supported = False
    staged_only_large = repo / "references" / "imports" / "raw" / "staged-large.txt"
    staged_only_large.write_text("x" * (10 * 1024 * 1024 + 2), encoding="utf-8", newline="\n")
    subprocess.run(["git", "-C", str(repo), "add", "references/imports/raw/staged-large.txt"], check=True, capture_output=True, text=True)
    staged_only_large.write_text("shrunk\n", encoding="utf-8", newline="\n")

    payload = json.loads(run_script("inspect_repo.py", str(repo)))
    if broken_link_supported and "references/imports/raw/broken-link.txt" in {item["path"] for item in payload["large_files"]}:
        raise AssertionError("inspect_repo.py should skip unreadable broken symlinks instead of treating them as large files")
    if "tasks/deadlines/linear-algebra.sync-conflict-20260710.md" not in payload["conflict_files"]:
        raise AssertionError("inspect_repo.py should report sync-conflict copies")
    if ".obsidian/workspace.json" not in payload["local_only_files"]:
        raise AssertionError("inspect_repo.py should report local workspace files")
    if "__pycache__/inspect_repo.cpython-310.pyc" not in payload["generated_cache_files"]:
        raise AssertionError("inspect_repo.py should report generated cache files")
    if "tmp/scratch.log" not in payload["temp_files"]:
        raise AssertionError("inspect_repo.py should report files under tmp/temp paths")
    if "references/textbooks/linear-algebra-textbook.pdf" not in payload["binary_files"]:
        raise AssertionError("inspect_repo.py should report binary source documents")
    if "references/slides/week-1-capture.mp4" not in payload["binary_files"]:
        raise AssertionError("inspect_repo.py should report binary media files")
    large_file_paths = {item["path"] for item in payload["large_files"]}
    if "references/imports/raw/ocr-dump.txt" not in large_file_paths:
        raise AssertionError("inspect_repo.py should report files above the large-file threshold")
    if "references/imports/raw/staged-large.txt" not in large_file_paths:
        raise AssertionError("inspect_repo.py should report oversized staged blobs even after the worktree copy shrinks")
    binary_zone_paths = {zone["path"] for zone in payload["binary_zones"]}
    if "references/textbooks" not in binary_zone_paths or "references/slides" not in binary_zone_paths:
        raise AssertionError("inspect_repo.py should summarize binary-heavy repository areas")
    warnings = payload.get("hygiene_warnings", [])
    for snippet in [
        "sync-conflict files detected",
        "generated caches detected",
        "local-only workspace or environment files detected",
        "temporary files detected under tmp/temp paths",
        "large files detected",
        "binary-heavy areas detected",
    ]:
        if not any(snippet in warning for warning in warnings):
            raise AssertionError(f"inspect_repo.py should emit a hygiene warning containing: {snippet}")


def verify_git_grouping(repo: Path, today: date) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Smoke Test"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "smoke@example.com"], check=True, capture_output=True, text=True)
    run_script("scaffold_repo.py", str(repo))
    run_script("scaffold_course.py", str(repo), "Linear Algebra")
    (repo / "references" / "slides").mkdir(parents=True, exist_ok=True)
    (repo / "references" / "slides" / "old-capture.mp4").write_bytes(b"tracked-binary")
    (repo / ".env.shared").write_text("TRACKED_SECRET=1\n", encoding="utf-8", newline="\n")
    (repo / ".env.tracked").write_text("TRACKED_SECRET=baseline\n", encoding="utf-8", newline="\n")
    nested_env_note = repo / "courses" / "env" / "notes.md"
    nested_env_note.parent.mkdir(parents=True, exist_ok=True)
    nested_env_note.write_text("# Environment course note\n", encoding="utf-8", newline="\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "baseline"], check=True, capture_output=True, text=True)

    write_task_fixture(
        repo / "tasks" / "deadlines" / "manual-study-block.md",
        title="Manual Study Block",
        due=(today + timedelta(days=5)).isoformat(),
        area="study",
        priority="medium",
        course="Linear Algebra",
    )
    write_task_fixture(
        repo / "tasks" / "deadlines" / "模电-第1次作业.md",
        title="模电 第1次作业",
        due=(today + timedelta(days=6)).isoformat(),
        area="homework",
        priority="high",
        course="模电",
        tags="[task, homework]",
    )
    (repo / "tmp").mkdir(parents=True, exist_ok=True)
    (repo / "tmp" / "scratch.log").write_text("temporary notes\n", encoding="utf-8", newline="\n")
    (repo / "references" / "slides").mkdir(parents=True, exist_ok=True)
    (repo / "references" / "slides" / "lecture-capture.mp4").write_bytes(b"fake-binary")
    (repo / "references" / "textbooks").mkdir(parents=True, exist_ok=True)
    (repo / "references" / "textbooks" / "linear-algebra-textbook.pdf").write_bytes(b"%PDF-1.4\n")
    (repo / "references" / "imports" / "raw").mkdir(parents=True, exist_ok=True)
    (repo / "references" / "imports" / "raw" / "lecture-slides.pptx").write_bytes(b"PK\x03\x04")
    (repo / "references" / "imports" / "raw" / "ocr-dump.txt").write_text(
        "x" * (10 * 1024 * 1024 + 1),
        encoding="utf-8",
        newline="\n",
    )
    staged_only_large = repo / "references" / "imports" / "raw" / "staged-large.txt"
    staged_only_large.write_text("x" * (10 * 1024 * 1024 + 2), encoding="utf-8", newline="\n")
    conflict_path = repo / "tasks" / "deadlines" / "manual-study-block.sync-conflict-20260704.md"
    conflict_path.write_text("# conflict copy\n", encoding="utf-8", newline="\n")
    (repo / ".env").write_text("API_KEY=local\n", encoding="utf-8", newline="\n")
    (repo / ".env.local").write_text("API_KEY=override\n", encoding="utf-8", newline="\n")
    (repo / "env").mkdir(parents=True, exist_ok=True)
    (repo / "env" / "pyvenv.cfg").write_text("home = C:/Python\n", encoding="utf-8", newline="\n")
    (repo / "venv").mkdir(parents=True, exist_ok=True)
    (repo / "venv" / "pyvenv.cfg").write_text("home = C:/Python\n", encoding="utf-8", newline="\n")
    (repo / ".venv").mkdir(parents=True, exist_ok=True)
    (repo / ".venv" / "pyvenv.cfg").write_text("home = C:/Python\n", encoding="utf-8", newline="\n")
    nested_virtualenv = repo / "courses" / "project" / "env"
    nested_virtualenv.mkdir(parents=True, exist_ok=True)
    (nested_virtualenv / "pyvenv.cfg").write_text("home = C:/Python\n", encoding="utf-8", newline="\n")
    (nested_virtualenv / "lib64").mkdir(parents=True, exist_ok=True)
    (nested_virtualenv / "lib64" / "python3.12.txt").write_text("stdlib marker\n", encoding="utf-8", newline="\n")
    mixed_case_virtualenv = repo / "courses" / "Project" / "env"
    mixed_case_virtualenv.mkdir(parents=True, exist_ok=True)
    (mixed_case_virtualenv / "pyvenv.cfg").write_text("home = C:/Python\n", encoding="utf-8", newline="\n")
    (mixed_case_virtualenv / "lib64").mkdir(parents=True, exist_ok=True)
    (mixed_case_virtualenv / "lib64" / "python3.12.txt").write_text("stdlib marker\n", encoding="utf-8", newline="\n")
    (repo / "references" / "slides" / "old-capture.mp4").unlink()
    subprocess.run(
        ["git", "-C", str(repo), "mv", ".env.shared", "tasks/env-note.md"],
        check=True,
        capture_output=True,
        text=True,
    )
    nested_env_note.write_text("# Environment course note\n\nUpdated for grouping test.\n", encoding="utf-8", newline="\n")
    nested_venv_course_note = repo / "courses" / "venv" / "notes" / "week1.md"
    nested_venv_course_note.parent.mkdir(parents=True, exist_ok=True)
    nested_venv_course_note.write_text("# Venv Course Note\n\nThis is coursework, not a virtualenv.\n", encoding="utf-8", newline="\n")
    nested_env_scripts_note = repo / "courses" / "env" / "scripts" / "week1.md"
    nested_env_scripts_note.parent.mkdir(parents=True, exist_ok=True)
    nested_env_scripts_note.write_text("# Env Scripts Note\n\nThis is coursework, not a virtualenv.\n", encoding="utf-8", newline="\n")
    tmp_slug_note = repo / "courses" / "notmp" / "notes.md"
    tmp_slug_note.parent.mkdir(parents=True, exist_ok=True)
    tmp_slug_note.write_text("# Notmp Course Note\n\nThis should not be treated as a temp path.\n", encoding="utf-8", newline="\n")
    (repo / ".env.tracked").write_text("TRACKED_SECRET=staged-update\n", encoding="utf-8", newline="\n")
    subprocess.run(["git", "-C", str(repo), "add", ".env.tracked"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "add", "references/imports/raw/staged-large.txt"], check=True, capture_output=True, text=True)
    (repo / ".env.tracked").unlink()
    staged_only_large.write_text("shrunk\n", encoding="utf-8", newline="\n")
    gitignore = repo / ".gitignore"
    gitignore.write_text(gitignore.read_text(encoding="utf-8") + ".venv/\n", encoding="utf-8", newline="\n")

    raw_grouping_output = run_script("group_git_changes.py", str(repo))
    if "tasks/deadlines/模电-第1次作业.md" not in raw_grouping_output:
        raise AssertionError("group_git_changes.py CLI output should preserve readable Unicode paths")
    if "\\u6a21\\u7535" in raw_grouping_output:
        raise AssertionError("group_git_changes.py CLI output should not ASCII-escape Unicode task paths")
    payload = json.loads(raw_grouping_output)
    if not payload.get("is_git_repo"):
        raise AssertionError(f"Expected a git repository payload, got: {payload}")
    hold_back = set(payload["hold_back_files"])
    if "tmp/" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back ignored temporary directories")
    if "references/slides/lecture-capture.mp4" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back binary media assets by default")
    if "tasks/deadlines/manual-study-block.sync-conflict-20260704.md" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back sync-conflict files")
    if ".env" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back .env files")
    if ".env.local" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back .env.* files")
    if "env/pyvenv.cfg" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back env/ virtual environment files")
    if ".venv/" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back ignored local virtual environments")
    if "venv/pyvenv.cfg" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back unignored virtual environment files")
    if "courses/project/env/pyvenv.cfg" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back nested env virtual environment files")
    if "courses/project/env/lib64/python3.12.txt" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back nested env virtual environment lib64 files")
    if "references/textbooks/linear-algebra-textbook.pdf" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back raw imported PDF source documents")
    if "references/imports/raw/lecture-slides.pptx" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back raw imported office source documents")
    if "references/imports/raw/ocr-dump.txt" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back oversized text exports by default")
    if "references/imports/raw/staged-large.txt" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back oversized staged blobs even after the worktree copy shrinks")
    if ".env.shared -> tasks/env-note.md" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back renames from environment files")
    if ".env.tracked" not in hold_back:
        raise AssertionError("group_git_changes.py should keep mixed delete statuses for env files on hold-back")

    grouped_tasks = payload["artifact_grouping"].get("tasks", [])
    if "tasks/deadlines/manual-study-block.md" not in grouped_tasks:
        raise AssertionError("group_git_changes.py should keep normal task artifacts in the tasks group")
    if "tasks/deadlines/模电-第1次作业.md" not in grouped_tasks:
        raise AssertionError("group_git_changes.py should preserve readable Unicode task paths in grouped output")
    grouped_imports = payload["artifact_grouping"].get("imports", [])
    if "references/slides/old-capture.mp4" not in grouped_imports:
        raise AssertionError("group_git_changes.py should keep tracked hold-back deletions in commit guidance")
    split_paths = {
        path
        for split in payload["recommended_commit_split"]
        for path in split["paths"]
    }
    for expected_path, message in [
        ("tasks/deadlines/模电-第1次作业.md", "group_git_changes.py should not escape or drop Unicode task paths"),
        ("courses/env/notes.md", "group_git_changes.py should not treat nested env course paths as virtual environments"),
        ("courses/venv/notes/week1.md", "group_git_changes.py should not treat course slugs named venv as virtual environments without evidence"),
        ("courses/env/scripts/week1.md", "group_git_changes.py should not treat coursework under env/scripts as a virtual environment without pyvenv evidence"),
        ("courses/notmp/notes.md", "group_git_changes.py should not treat path components that only end with tmp as temporary directories"),
    ]:
        if expected_path in hold_back:
            raise AssertionError(message)
        if expected_path not in split_paths:
            raise AssertionError(f"{message}; expected {expected_path} to remain in recommended commit guidance")
    unexpected = hold_back & split_paths
    if unexpected:
        raise AssertionError(f"Hold-back files should not be suggested for commit splits: {sorted(unexpected)}")

    reasons = payload.get("hold_back_reasons", {})
    if reasons.get("tmp/") != "temporary file":
        raise AssertionError("Expected a temporary-file reason for tmp/")
    if reasons.get(".env") != "environment file":
        raise AssertionError("Expected an environment-file reason for .env")
    if reasons.get(".env.local") != "environment file":
        raise AssertionError("Expected an environment-file reason for .env.local")
    if reasons.get("env/pyvenv.cfg") != "local virtual environment":
        raise AssertionError("Expected a local-virtual-environment reason for env/pyvenv.cfg")
    if reasons.get(".venv/") != "local virtual environment":
        raise AssertionError("Expected a local-virtual-environment reason for .venv/")
    if reasons.get("venv/pyvenv.cfg") != "local virtual environment":
        raise AssertionError("Expected a local-virtual-environment reason for venv/pyvenv.cfg")
    if reasons.get("courses/project/env/pyvenv.cfg") != "local virtual environment":
        raise AssertionError("Expected a local-virtual-environment reason for nested env/pyvenv.cfg")
    if reasons.get("courses/project/env/lib64/python3.12.txt") != "local virtual environment":
        raise AssertionError("Expected a local-virtual-environment reason for nested env/lib64 virtualenv files")
    if reasons.get("references/textbooks/linear-algebra-textbook.pdf") != "binary source document":
        raise AssertionError("Expected a binary-source-document reason for imported PDFs")
    if reasons.get("references/imports/raw/lecture-slides.pptx") != "binary source document":
        raise AssertionError("Expected a binary-source-document reason for imported office files")
    if reasons.get("references/imports/raw/ocr-dump.txt") != "large file":
        raise AssertionError("Expected a large-file reason for oversized text exports")
    if reasons.get("references/imports/raw/staged-large.txt") != "large file":
        raise AssertionError("Expected a large-file reason for oversized staged blobs")
    if reasons.get(".env.shared -> tasks/env-note.md") != "environment file":
        raise AssertionError("Expected an environment-file reason for renames from environment files")
    if reasons.get(".env.tracked") != "environment file":
        raise AssertionError("Expected an environment-file reason for mixed delete env states")
    if reasons.get("tasks/deadlines/manual-study-block.sync-conflict-20260704.md") != "sync-conflict file":
        raise AssertionError("Expected a sync-conflict reason for the conflict copy")

    group_git_changes = load_group_git_changes_module()
    if not group_git_changes.is_virtualenv_path(repo, "courses/Project/env/pyvenv.cfg"):
        raise AssertionError("group_git_changes.py should detect mixed-case nested env virtual environment pyvenv markers")
    if not group_git_changes.is_virtualenv_path(repo, "courses/Project/env/lib64/python3.12.txt"):
        raise AssertionError("group_git_changes.py should detect mixed-case nested env virtual environment lib64 files")
    if group_git_changes.hold_back_reason(repo, "courses/notmp/notes.md"):
        raise AssertionError("group_git_changes.py should not mark coursework paths like courses/notmp/notes.md as temporary files")
    if group_git_changes.hold_back_reason(repo, "courses/Project/env/lib64/python3.12.txt") != "local virtual environment":
        raise AssertionError("group_git_changes.py should preserve original path casing when classifying virtualenv artifacts from CLI paths")


def init_git_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(repo), "init", "-b", "main"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Smoke Test"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "smoke@example.com"], check=True, capture_output=True, text=True)


def commit_all(repo: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", message], check=True, capture_output=True, text=True)
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def seed_fake_student_os_source(repo: Path, *, version_label: str) -> str:
    skill_root = repo / "student-os"
    scripts_root = skill_root / "scripts"
    templates_root = skill_root / "templates"
    references_root = skill_root / "references"
    scripts_root.mkdir(parents=True, exist_ok=True)
    templates_root.mkdir(parents=True, exist_ok=True)
    references_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "SKILL.md").write_text(
        "---\n"
        "name: student-os\n"
        "description: fixture skill\n"
        "---\n\n"
        f"# Student OS Fixture {version_label}\n",
        encoding="utf-8",
        newline="\n",
    )
    (scripts_root / "fixture_script.py").write_text(
        "def main():\n"
        f"    return '{version_label}'\n",
        encoding="utf-8",
        newline="\n",
    )
    (templates_root / "fixture.md").write_text(
        f"# Fixture Template {version_label}\n",
        encoding="utf-8",
        newline="\n",
    )
    (references_root / "fixture.md").write_text(
        f"# Fixture Reference {version_label}\n",
        encoding="utf-8",
        newline="\n",
    )
    shutil.copy2(STUDENT_OS_SCRIPTS / "update_student_os.py", scripts_root / "update_student_os.py")
    shutil.copy2(STUDENT_OS_SCRIPTS / "update_student_os_impl.py", scripts_root / "update_student_os_impl.py")
    return commit_all(repo, f"fixture: {version_label}")


def build_copy_install_fixture(base_dir: Path, source_repo: Path, installed_commit: str) -> Path:
    install_module = load_root_script_module("install_student_os.py", "student_os_install_smoke")
    source_skill = source_repo / "student-os"
    target = base_dir / "installed-student-os"
    shutil.copytree(source_skill, target)
    overrides_dir = target / ".student-os-local-overrides"
    overrides_dir.mkdir(parents=True, exist_ok=True)
    (overrides_dir / "notes.md").write_text("# Local override\n", encoding="utf-8", newline="\n")
    (target / ".student-os-install.local.json").write_text('{"theme":"custom"}\n', encoding="utf-8", newline="\n")
    manifest = install_module.build_install_manifest(
        destination=target,
        agent="codex",
        scope="user",
        install_method="copied",
        used_symlink=False,
        source_repo=str(source_repo.resolve()),
        source_ref="main",
        installed_commit=installed_commit,
        linked_source_path="",
    )
    install_module.write_manifest(target, manifest)
    return target


def assert_no_pycache(root: Path) -> None:
    pycache_paths = sorted(str(path) for path in root.rglob("__pycache__"))
    if pycache_paths:
        raise AssertionError(f"Validation should not leave __pycache__ artifacts behind: {pycache_paths}")


def verify_token_loader(tmp_root: Path) -> None:
    module = load_student_os_script_module("token_loader.py", "student_os_token_loader_smoke")
    install_module = load_root_script_module("install_student_os.py", "student_os_install_dotenv_smoke")
    update_module = load_student_os_script_module("update_student_os_impl.py", "student_os_update_dotenv_smoke")

    if ".env" not in install_module.LOCAL_OVERRIDE_NAMES:
        raise AssertionError("install_student_os.py should preserve skill-local .env across installs/updates")
    if ".env" not in update_module.LOCAL_OVERRIDE_NAMES:
        raise AssertionError("update_student_os_impl.py should preserve skill-local .env across updates")
    if not (ROOT / "student-os" / ".env.example").exists():
        raise AssertionError("student-os/.env.example should exist as the documented template")
    repo_gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for needle in [".env", "student-os/.env", "!.env.example"]:
        if needle not in repo_gitignore:
            raise AssertionError(f"repository .gitignore should ignore skill secrets via {needle!r}")

    skill_root = tmp_root / "skill-root"
    cwd = tmp_root / "cwd"
    skill_root.mkdir(parents=True, exist_ok=True)
    cwd.mkdir(parents=True, exist_ok=True)
    (skill_root / ".env").write_text('MINERU_TOKEN="skill-token"\n# comment\nexport MINERU_API_TOKEN=unused\n', encoding="utf-8", newline="\n")
    (cwd / ".env").write_text("MINERU_TOKEN=cwd-token\n", encoding="utf-8", newline="\n")

    scaffold_repo = tmp_root / "scaffold-gitignore"
    run_script("scaffold_repo.py", str(scaffold_repo))
    gitignore_text = (scaffold_repo / ".gitignore").read_text(encoding="utf-8")
    for needle in [".env", "*.env", "!.env.example"]:
        if needle not in gitignore_text:
            raise AssertionError(f"scaffold_repo.py should ignore secrets via {needle!r}")

    existing_vault = tmp_root / "existing-vault"
    existing_vault.mkdir(parents=True, exist_ok=True)
    (existing_vault / ".gitignore").write_text("*.log\nnode_modules/\n", encoding="utf-8", newline="\n")
    run_script("scaffold_repo.py", str(existing_vault))
    merged_gitignore = (existing_vault / ".gitignore").read_text(encoding="utf-8")
    if "*.log" not in merged_gitignore or "node_modules/" not in merged_gitignore:
        raise AssertionError("scaffold_repo.py should preserve existing .gitignore entries")
    for needle in [".env", "*.env", "!.env.example"]:
        if needle not in merged_gitignore:
            raise AssertionError(f"scaffold_repo.py should append missing secret rule {needle!r} to existing .gitignore")

    env_backup = {name: os.environ.get(name) for name in ["MINERU_TOKEN", "MINERU_API_TOKEN"]}
    try:
        os.environ.pop("MINERU_TOKEN", None)
        os.environ.pop("MINERU_API_TOKEN", None)

        if module.load_token(" cli-token ", skill_root=skill_root, cwd=cwd) != "cli-token":
            raise AssertionError("CLI token should win over env and .env files")

        os.environ["MINERU_TOKEN"] = " process-env-token "
        if module.load_token(None, skill_root=skill_root, cwd=cwd) != "process-env-token":
            raise AssertionError("Process environment should win over .env files")
        os.environ.pop("MINERU_TOKEN", None)

        if module.load_token(None, skill_root=skill_root, cwd=cwd) != "skill-token":
            raise AssertionError("Skill-root .env should win over cwd .env")

        (skill_root / ".env").unlink()
        if module.load_token(None, skill_root=skill_root, cwd=cwd) != "cwd-token":
            raise AssertionError("cwd .env should be used when skill-root .env is absent")

        (cwd / ".env").write_text("MINERU_API_TOKEN=alias-token\n", encoding="utf-8", newline="\n")
        if module.load_token(None, skill_root=skill_root, cwd=cwd) != "alias-token":
            raise AssertionError("MINERU_API_TOKEN in .env should be accepted as an alias")

        (cwd / ".env").write_bytes(b"\xff\xfeMINERU_TOKEN=bad-encoding\n")
        if module.load_token(None, skill_root=skill_root, cwd=cwd) is not None:
            raise AssertionError("Unreadable/non-UTF-8 .env files should be skipped without raising")

        repair_only_md = cwd / "repair-only-local.md"
        repair_only_md.write_text(
            "\n".join(
                [
                    "---",
                    "type: imported-reference",
                    "repair_status:",
                    "derived_from_import:",
                    "---",
                    "",
                    "#Broken",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        local_payload = json.loads(
            run_script(
                "materials_convert.py",
                str(repair_only_md),
                "--method",
                "local",
                "--repair-only",
                cwd=cwd,
                env={"MINERU_TOKEN": "", "MINERU_API_TOKEN": ""},
            )
        )
        if not local_payload.get("converted"):
            raise AssertionError(f"Local/repair-only conversion should ignore bad cwd .env, got: {local_payload}")
    finally:
        for name, value in env_backup.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    # Legacy entry-symlink layout: scripts/ points at the source checkout, but .env lives
    # in the installed skill root and must still be discovered.
    legacy_install = tmp_root / "legacy-entry-symlink-install"
    legacy_scripts = legacy_install / "scripts"
    legacy_scripts.mkdir(parents=True, exist_ok=True)
    try:
        for child in (ROOT / "student-os").iterdir():
            if child.name == "scripts":
                continue
            target = legacy_install / child.name
            if child.is_dir():
                target.symlink_to(child.resolve(), target_is_directory=True)
            else:
                target.symlink_to(child.resolve())
        # Replace real scripts dir with a symlink to the source scripts.
        shutil.rmtree(legacy_scripts)
        legacy_scripts.symlink_to((ROOT / "student-os" / "scripts").resolve(), target_is_directory=True)
    except OSError:
        return
    (legacy_install / ".env").write_text("MINERU_TOKEN=legacy-install-token\n", encoding="utf-8", newline="\n")
    loader_via_symlink = legacy_scripts / "token_loader.py"
    spec = importlib.util.spec_from_file_location("student_os_token_loader_symlink_smoke", loader_via_symlink)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load token_loader via legacy scripts symlink")
    symlink_module = importlib.util.module_from_spec(spec)
    original_flag = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(symlink_module)
    finally:
        sys.dont_write_bytecode = original_flag
    lexical_root = symlink_module.skill_root_dir()
    if lexical_root.resolve() != legacy_install.resolve():
        # Compare using absolute() semantics: resolved source checkout should NOT win.
        if Path(lexical_root).absolute() != legacy_install.absolute():
            raise AssertionError(
                f"skill_root_dir() should keep the installed root for entry-symlink layouts, got: {lexical_root}"
            )
    env_backup = {name: os.environ.get(name) for name in ["MINERU_TOKEN", "MINERU_API_TOKEN"]}
    try:
        os.environ.pop("MINERU_TOKEN", None)
        os.environ.pop("MINERU_API_TOKEN", None)
        if symlink_module.load_token(None, cwd=tmp_root / "empty-cwd") != "legacy-install-token":
            raise AssertionError("Entry-symlink installs should read .env from the installed skill root")
    finally:
        for name, value in env_backup.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def verify_install_manifest_generation(tmp_root: Path) -> None:
    install_module = load_root_script_module("install_student_os.py", "student_os_install_manifest_smoke")
    codex_home = tmp_root / "codex-home"
    payload = json.loads(
        run_root_script(
            "install_student_os.py",
            "--agent",
            "codex",
            "--scope",
            "user",
            "--mode",
            "copy",
            "--json",
            env={"CODEX_HOME": str(codex_home)},
        )
    )
    result = payload["results"][0]
    destination = Path(result["destination"])
    manifest_path = destination / ".student-os-install.json"
    if not manifest_path.exists():
        raise AssertionError("install_student_os.py should write an install manifest into the installed skill")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for key in [
        "skill_name",
        "source_repo",
        "source_ref",
        "installed_commit",
        "installed_at",
        "install_method",
        "agent",
        "scope",
        "target_path",
        "used_symlink",
        "tracked_files",
    ]:
        if key not in manifest:
            raise AssertionError(f"install manifest should include {key}")
    if manifest["skill_name"] != "student-os":
        raise AssertionError("install manifest should record the skill name")
    if manifest["install_method"] != "copied":
        raise AssertionError("copy installs should record copied as the install method")
    if manifest["source_repo"] != install_module.discover_source_repo():
        raise AssertionError("install manifests should record the actual source repo by default")

    (destination / ".env").write_text("MINERU_TOKEN=preserve-me\n", encoding="utf-8", newline="\n")
    forced = json.loads(
        run_root_script(
            "install_student_os.py",
            "--agent",
            "codex",
            "--scope",
            "user",
            "--mode",
            "copy",
            "--force",
            "--json",
            env={"CODEX_HOME": str(codex_home)},
        )
    )
    forced_destination = Path(forced["results"][0]["destination"])
    preserved_env = forced_destination / ".env"
    if not preserved_env.exists():
        raise AssertionError("Forced copy reinstall should preserve skill-local .env")
    if "preserve-me" not in preserved_env.read_text(encoding="utf-8"):
        raise AssertionError("Forced copy reinstall should restore the previous .env contents")
    if ".env" not in forced["results"][0].get("preserved_overrides", ""):
        raise AssertionError("Forced reinstall payload should report preserved .env overrides")


def verify_legacy_link_install_detection(tmp_root: Path) -> None:
    install_module = load_root_script_module("install_student_os.py", "student_os_install_link_smoke")
    legacy_destination = tmp_root / "legacy-linked-student-os"
    try:
        legacy_destination.symlink_to((ROOT / "student-os").resolve(), target_is_directory=True)
    except OSError:
        return
    if not install_module.same_link_install(legacy_destination):
        raise AssertionError("install_student_os.py should recognize legacy whole-directory symlink installs")
    child_link_install = tmp_root / "child-linked-student-os"
    child_link_install.mkdir(parents=True, exist_ok=True)
    (child_link_install / "SKILL.md").symlink_to((ROOT / "student-os" / "SKILL.md").resolve())
    if not install_module.same_link_install(child_link_install):
        raise AssertionError("install_student_os.py should still recognize linked installs that symlink top-level children")
    created_entries = install_module.sync_linked_entries(child_link_install, ROOT / "student-os")
    if "references" not in created_entries:
        raise AssertionError("install_student_os.py should recreate missing top-level symlink entries for linked installs")
    if not (child_link_install / "references").is_symlink():
        raise AssertionError("install_student_os.py should materialize recreated linked entries as symlinks")
    source_manifest = ROOT / "student-os" / ".student-os-install.json"
    if source_manifest.exists():
        source_manifest.unlink()
    legacy_root = tmp_root / "legacy-link-root"
    legacy_root.mkdir(parents=True, exist_ok=True)
    legacy_install = legacy_root / "student-os"
    try:
        legacy_install.symlink_to((ROOT / "student-os").resolve(), target_is_directory=True)
    except OSError:
        return
    result = install_module.install_one(
        install_module.InstallTarget(agent="codex", scope="user", root=legacy_root),
        "auto",
        False,
        source_repo="https://example.com/fork.git",
        source_ref="main",
    )
    if result["manifest"] != "":
        raise AssertionError("Legacy whole-directory symlink installs should not write manifests into the source checkout")
    if source_manifest.exists():
        raise AssertionError("Legacy whole-directory symlink installs should not create a manifest in the source repo")


def verify_update_source_override_and_project_copy_detection(tmp_root: Path) -> None:
    install_module = load_root_script_module("install_student_os.py", "student_os_install_override_smoke")
    update_module = load_root_script_module("update_student_os.py", "student_os_update_override_smoke")

    override_repo = tmp_root / "override-source"
    init_git_repo(override_repo)
    override_commit = seed_fake_student_os_source(override_repo, version_label="override")

    target = tmp_root / "override-install"
    shutil.copytree(override_repo / "student-os", target)
    manifest = install_module.build_install_manifest(
        destination=target,
        agent="codex",
        scope="user",
        install_method="copied",
        used_symlink=False,
        source_repo="https://github.com/Gu-Heping/college-student-workflow.git",
        source_ref="main",
        installed_commit=override_commit,
        linked_source_path="",
    )
    install_module.write_manifest(target, manifest)
    info = update_module.build_install_info(target, str(override_repo.resolve()), "main")
    if info.source_repo != str(override_repo.resolve()):
        raise AssertionError("Explicit --repo equivalents should override manifest source_repo values")
    if info.source_ref != "main":
        raise AssertionError("Explicit --ref equivalents should override manifest source_ref values")

    vault_repo = tmp_root / "vault-repo"
    init_git_repo(vault_repo)
    (vault_repo / "README.md").write_text("# Vault\n", encoding="utf-8", newline="\n")
    commit_all(vault_repo, "init vault")
    project_install = vault_repo / ".codex" / "skills" / "student-os"
    project_install.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(override_repo / "student-os", project_install)
    project_manifest = install_module.build_install_manifest(
        destination=project_install,
        agent="codex",
        scope="project",
        install_method="copied",
        used_symlink=False,
        source_repo=str(override_repo.resolve()),
        source_ref="main",
        installed_commit=override_commit,
        linked_source_path="",
    )
    install_module.write_manifest(project_install, project_manifest)
    project_info = update_module.build_install_info(project_install, None, None)
    if project_info.install_kind != "copy":
        raise AssertionError("Copied project installs inside a git repository should still be treated as copy installs")

    env_backup = {name: os.environ.get(name) for name in ["HOME", "USERPROFILE", "CODEX_HOME"]}
    previous_cwd = Path.cwd()
    try:
        isolated_home = tmp_root / "isolated-home"
        os.environ["HOME"] = str(isolated_home)
        os.environ["USERPROFILE"] = str(isolated_home)
        os.environ["CODEX_HOME"] = str(isolated_home / ".codex")
        os.chdir(vault_repo)
        sys.modules.pop("update_student_os_impl", None)
        project_discovery_module = load_root_script_module("update_student_os.py", "student_os_update_discovery_smoke")
        discovered_target = project_discovery_module.discover_target(None)
    finally:
        os.chdir(previous_cwd)
        for name, value in env_backup.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    if discovered_target != project_install:
        raise AssertionError("update_student_os.py should discover project-scoped installs by default")

    legacy_project_install = vault_repo / ".claude" / "skills" / "student-os"
    legacy_project_install.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(override_repo / "student-os", legacy_project_install)
    legacy_project_info = update_module.build_install_info(legacy_project_install, None, None)
    if legacy_project_info.install_kind != "copy":
        raise AssertionError("Manifestless copied installs inside a parent repository should default to copy mode")

    missing_manifest_failure = run_root_script_failure(
        "update_student_os.py",
        "--apply",
        "--target",
        str(legacy_project_install),
        "--repo",
        str(override_repo.resolve()),
        "--ref",
        "main",
    )
    if "--force" not in missing_manifest_failure:
        raise AssertionError("Manifestless copied installs should require --force before replacement")


def verify_self_update_workflow(tmp_root: Path) -> None:
    source_repo = tmp_root / "student-os-source"
    init_git_repo(source_repo)
    commit_v1 = seed_fake_student_os_source(source_repo, version_label="v1")
    install_target = build_copy_install_fixture(tmp_root, source_repo, commit_v1)

    seed_fake_student_os_source(source_repo, version_label="v2")
    (source_repo / "student-os" / "templates" / "fixture.md").write_text(
        "# Fixture Template v2 updated\n",
        encoding="utf-8",
        newline="\n",
    )
    commit_v2 = commit_all(source_repo, "fixture: v2 template tweak")

    check_payload = json.loads(
        run_root_script(
            "update_student_os.py",
            "--check",
            "--target",
            str(install_target),
            "--repo",
            str(source_repo.resolve()),
            "--ref",
            "main",
            "--json",
        )
    )
    if not check_payload["update_available"]:
        raise AssertionError("update_student_os.py --check should report updates when the remote commit is newer")
    if check_payload["current_commit"] != commit_v1:
        raise AssertionError("update_student_os.py --check should report the installed commit from the manifest")
    if check_payload["latest_commit"] != commit_v2:
        raise AssertionError("update_student_os.py --check should resolve the latest remote commit")

    apply_payload = json.loads(
        run_root_script(
            "update_student_os.py",
            "--apply",
            "--target",
            str(install_target),
            "--repo",
            str(source_repo.resolve()),
            "--ref",
            "main",
            "--json",
        )
    )
    if not apply_payload["updated"]:
        raise AssertionError("copy-mode self-update should report an applied update")
    if not apply_payload["backup_path"]:
        raise AssertionError("copy-mode self-update should create and report a backup path")
    if "--restore-backup" not in apply_payload["rollback_command"]:
        raise AssertionError("copy-mode self-update should print a restore command for rollback")
    if ".student-os-local-overrides" not in apply_payload["preserved_override_paths"]:
        raise AssertionError("copy-mode self-update should preserve the documented override directory")
    if ".student-os-install.local.json" not in apply_payload["preserved_override_paths"]:
        raise AssertionError("copy-mode self-update should preserve the documented local override file")
    ensure_contains(install_target / "SKILL.md", "Fixture v2")
    ensure_contains(install_target / ".student-os-local-overrides" / "notes.md", "Local override")
    ensure_contains(install_target / ".student-os-install.local.json", '"theme":"custom"')
    manifest = json.loads((install_target / ".student-os-install.json").read_text(encoding="utf-8"))
    if manifest["installed_commit"] != commit_v2:
        raise AssertionError("copy-mode self-update should refresh the install manifest commit")
    if manifest["source_repo"] != str(source_repo.resolve()):
        raise AssertionError("copy-mode self-update should preserve the configured source repo in the manifest")
    if Path(manifest["target_path"]) != install_target.resolve():
        raise AssertionError("copy-mode self-update should record the final install target in the refreshed manifest")
    installed_updater = install_target / "scripts" / "update_student_os.py"
    ensure_exists(installed_updater)
    installed_check_payload = json.loads(
        run_path_script(
            installed_updater,
            "--check",
            "--target",
            str(install_target),
            "--repo",
            str(source_repo.resolve()),
            "--ref",
            "main",
            "--json",
            cwd=install_target,
        )
    )
    if Path(installed_check_payload["target_path"]) != install_target:
        raise AssertionError("Installed updater entrypoint should work from the installed skill directory")
    if "local_changes" in installed_check_payload and installed_check_payload["local_changes"]:
        raise AssertionError("Installed updater should not report its own __pycache__ artifacts as local changes")
    assert_no_pycache(install_target)
    assert_no_pycache(source_repo)

    (install_target / "SKILL.md").write_text(
        (install_target / "SKILL.md").read_text(encoding="utf-8") + "\nLocal drift\n",
        encoding="utf-8",
        newline="\n",
    )
    (source_repo / "student-os" / "SKILL.md").write_text(
        (source_repo / "student-os" / "SKILL.md").read_text(encoding="utf-8") + "\nFixture v3\n",
        encoding="utf-8",
        newline="\n",
    )
    commit_all(source_repo, "fixture: v3")
    failure = run_root_script_failure(
        "update_student_os.py",
        "--apply",
        "--target",
        str(install_target),
        "--repo",
        str(source_repo.resolve()),
        "--ref",
        "main",
    )
    if "--force" not in failure:
        raise AssertionError("self-update should refuse overwriting local installed-skill drift without --force")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run smoke tests for student-os scaffolding workflows.")
    parser.add_argument(
        "--refresh-examples",
        action="store_true",
        help="Replace example repositories in ./examples with fresh generated snapshots.",
    )
    args = parser.parse_args()
    today = date.today()

    with tempfile.TemporaryDirectory(prefix="student-os-smoke-") as tmp:
        tmp_root = Path(tmp)
        single_repo = tmp_root / "single-semester-demo"
        multi_repo = tmp_root / "multi-semester-demo"
        legacy_repo = tmp_root / "legacy-layout-demo"
        weekly_parent_repo = tmp_root / "weekly" / "nested-weekly-parent-demo"
        grouping_repo = tmp_root / "grouping-demo"

        build_single_semester(single_repo, today)
        build_multi_semester(multi_repo, today)
        build_legacy_layout(legacy_repo, today)
        build_repo_inside_weekly_parent(weekly_parent_repo, today)
        inspect_repo_fixture = tmp_root / "inspect-repo-demo"
        copy_repo(multi_repo, inspect_repo_fixture)
        verify_inspect_repo(inspect_repo_fixture)
        verify_git_grouping(grouping_repo, today)
        verify_chinese_slug_support(tmp_root / "unicode-course-demo", today)
        verify_install_manifest_generation(tmp_root / "install-manifest-demo")
        verify_legacy_link_install_detection(tmp_root / "legacy-link-install-demo")
        verify_update_source_override_and_project_copy_detection(tmp_root / "update-override-demo")
        verify_self_update_workflow(tmp_root / "self-update-demo")
        verify_token_loader(tmp_root / "token-loader-demo")

        if args.refresh_examples:
            EXAMPLES_ROOT.mkdir(parents=True, exist_ok=True)
            copy_repo(single_repo, EXAMPLES_ROOT / "single-semester-demo")
            copy_repo(multi_repo, EXAMPLES_ROOT / "multi-semester-demo")
            copy_repo(legacy_repo, EXAMPLES_ROOT / "legacy-layout-demo")
            for example_root, source_root in [
                (EXAMPLES_ROOT / "single-semester-demo", single_repo),
                (EXAMPLES_ROOT / "multi-semester-demo", multi_repo),
                (EXAMPLES_ROOT / "legacy-layout-demo", legacy_repo),
            ]:
                materialize_empty_dirs(example_root)
                scrub_example_paths(example_root, source_root)
                normalize_text_files(example_root)

    print("OK single-semester-demo")
    print("OK multi-semester-demo")
    print("OK legacy-layout-demo")
    print("OK unicode-course-demo")
    print("OK install-manifest-demo")
    print("OK legacy-link-install-demo")
    print("OK update-override-demo")
    print("OK self-update-demo")
    print("OK token-loader-demo")
    if args.refresh_examples:
        print(f"REFRESHED {EXAMPLES_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
