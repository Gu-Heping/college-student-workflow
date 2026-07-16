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


def run_script(name: str, *args: str, cwd: Path = ROOT) -> str:
    script_path = STUDENT_OS_SCRIPTS / name
    result = subprocess.run(
        [sys.executable, "-B", str(script_path), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"},
    )
    return result.stdout.strip()


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


def exercise_import_workflows(repo: Path) -> None:
    fixture_root = repo / "references" / "imports" / "source"
    fixture_root.mkdir(parents=True, exist_ok=True)
    docx_path = fixture_root / "linear-algebra-outline.docx"
    xlsx_path = fixture_root / "linear-algebra-progress.xlsx"
    pptx_path = fixture_root / "linear-algebra-week-2.pptx"
    pdf_path = fixture_root / "linear-algebra-handout.pdf"
    write_docx_fixture(docx_path)
    write_xlsx_fixture(xlsx_path)
    write_pptx_fixture(pptx_path)
    write_pdf_fixture(pdf_path)

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

    docx_path.unlink()
    xlsx_path.unlink()
    pptx_path.unlink()
    pdf_path.unlink()


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
    ensure_contains(resolved_path, 'github_issue_status: "closed"')
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
            "GitHub issue prep privacy check",
            "--feedback-kind",
            "install",
            "--severity",
            "high",
            "--source-context",
            "Codex on Windows with installed version: 0.7.0",
            "--related-artifacts",
            r"D:\vault\private-course\notes.md,.env,/Users/alice/private-notes.md",
            "--related-roles",
            "feedback-operator,codex",
            "--what-happened",
            "- The installer exposed a private path from D:\\vault\\private-course\\notes.md and /Users/alice/private-notes.md.",
            "--expected-behavior",
            "- Public reports should redact private Windows paths and vault references.",
            "--evidence",
            "- D:\\vault\\private-course\\notes.md\n- /Users/alice/private-notes.md\n- .env\n- sk-proj-1234567890-ABCDEFGHIJKLMNOPQRST\n- github_pat_1234567890ABCDEFGHIJKLMNOP",
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
    joined_warnings = "\n".join(issue_payload["privacy_warnings"])
    for expected_warning in ["Windows absolute paths", "Unix-style absolute paths", ".env", "token-like strings", "private vault path"]:
        if expected_warning not in joined_warnings:
            raise AssertionError(f"Expected privacy warning containing {expected_warning!r}, got: {joined_warnings}")

    publish_failure = run_script_failure(
        "publish_github_issue.py",
        str(repo),
        str(resolved_path),
        "--github-repo",
        "Gu-Heping/college-student-workflow",
    )
    if "already linked to a GitHub issue" not in publish_failure:
        raise AssertionError("publish_github_issue.py should refuse duplicate publication for already-linked feedback")

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
    body_path = repo / publish_payload["body_path"]
    ensure_exists(body_path)
    try:
        body_path.relative_to(repo / "feedback" / "summaries")
    except ValueError as exc:
        raise AssertionError("Fallback GitHub issue body should stay inside feedback/summaries") from exc
    gh_command = publish_payload["gh_command"]
    if "'../../notes/leak: Manual path $(danger) `tick` test'" not in gh_command:
        raise AssertionError("Fallback gh command should shell-quote feedback-controlled titles safely")


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
    if args.refresh_examples:
        print(f"REFRESHED {EXAMPLES_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
