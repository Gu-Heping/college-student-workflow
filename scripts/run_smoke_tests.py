#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDENT_OS_SCRIPTS = ROOT / "student-os" / "scripts"
EXAMPLES_ROOT = ROOT / "examples"


def run_script(name: str, *args: str, cwd: Path = ROOT) -> str:
    script_path = STUDENT_OS_SCRIPTS / name
    result = subprocess.run(
        [sys.executable, "-B", str(script_path), *args],
        check=True,
        capture_output=True,
        text=True,
        cwd=cwd,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return result.stdout.strip()


def run_script_failure(name: str, *args: str, cwd: Path = ROOT) -> str:
    script_path = STUDENT_OS_SCRIPTS / name
    result = subprocess.run(
        [sys.executable, "-B", str(script_path), *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=cwd,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if result.returncode == 0:
        raise AssertionError(f"Expected {name} to fail for args {args!r}")
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
    ensure_contains(resolved_path, "## Triage Notes")
    ensure_contains(resolved_path, "## Resolution Summary")
    ensure_contains(second_triaged_path, f'feedback_id: "{expected_feedback_id}"')
    ensure_contains(summary_path, "## Developer Handoff")
    ensure_contains(summary_path, "0.7.0")
    ensure_contains(summary_path, "- Triaged items: 1")
    ensure_contains(summary_path, expected_feedback_id)
    if "must stay under" not in failure_output:
        raise AssertionError(f"Expected path-guard failure, got: {failure_output}")


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


def verify_git_grouping(repo: Path, today: date) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Smoke Test"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "smoke@example.com"], check=True, capture_output=True, text=True)
    run_script("scaffold_repo.py", str(repo))
    run_script("scaffold_course.py", str(repo), "Linear Algebra")
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
    (repo / "tmp").mkdir(parents=True, exist_ok=True)
    (repo / "tmp" / "scratch.log").write_text("temporary notes\n", encoding="utf-8", newline="\n")
    (repo / "references" / "slides").mkdir(parents=True, exist_ok=True)
    (repo / "references" / "slides" / "lecture-capture.mp4").write_bytes(b"fake-binary")
    conflict_path = repo / "tasks" / "deadlines" / "manual-study-block.sync-conflict-20260704.md"
    conflict_path.write_text("# conflict copy\n", encoding="utf-8", newline="\n")
    (repo / ".env").write_text("API_KEY=local\n", encoding="utf-8", newline="\n")
    (repo / ".venv").mkdir(parents=True, exist_ok=True)
    (repo / ".venv" / "pyvenv.cfg").write_text("home = C:/Python\n", encoding="utf-8", newline="\n")
    gitignore = repo / ".gitignore"
    gitignore.write_text(gitignore.read_text(encoding="utf-8") + ".venv/\n", encoding="utf-8", newline="\n")

    payload = json.loads(run_script("group_git_changes.py", str(repo)))
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
    if ".venv/" not in hold_back:
        raise AssertionError("group_git_changes.py should hold back ignored local artifacts")

    grouped_tasks = payload["artifact_grouping"].get("tasks", [])
    if "tasks/deadlines/manual-study-block.md" not in grouped_tasks:
        raise AssertionError("group_git_changes.py should keep normal task artifacts in the tasks group")

    split_paths = {
        path
        for split in payload["recommended_commit_split"]
        for path in split["paths"]
    }
    unexpected = hold_back & split_paths
    if unexpected:
        raise AssertionError(f"Hold-back files should not be suggested for commit splits: {sorted(unexpected)}")

    reasons = payload.get("hold_back_reasons", {})
    if reasons.get("tmp/") != "temporary file":
        raise AssertionError("Expected a temporary-file reason for tmp/")
    if reasons.get(".env") != "environment file":
        raise AssertionError("Expected an environment-file reason for .env")
    if reasons.get(".venv/") != "ignored local artifact":
        raise AssertionError("Expected an ignored-local-artifact reason for .venv/")
    if reasons.get("tasks/deadlines/manual-study-block.sync-conflict-20260704.md") != "sync-conflict file":
        raise AssertionError("Expected a sync-conflict reason for the conflict copy")


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
        verify_inspect_repo(multi_repo)
        verify_git_grouping(grouping_repo, today)

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
    if args.refresh_examples:
        print(f"REFRESHED {EXAMPLES_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
