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


def exercise_feedback_lifecycle(repo: Path) -> None:
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
    ensure_contains(second_triaged_path, 'feedback_id: "fb-20260703-weekly-plan-omitted-imported-deadline-2"')
    ensure_contains(summary_path, "## Developer Handoff")
    ensure_contains(summary_path, "0.7.0")
    ensure_contains(summary_path, "- Triaged items: 1")
    ensure_contains(summary_path, "fb-20260703-weekly-plan-omitted-imported-deadline-2")
    if "must stay under" not in failure_output:
        raise AssertionError(f"Expected path-guard failure, got: {failure_output}")


def build_single_semester(repo: Path, today: date) -> None:
    due_date = (today + timedelta(days=8)).isoformat()
    run_script("scaffold_repo.py", str(repo))
    run_script("scaffold_course.py", str(repo), "Linear Algebra")
    run_script("scaffold_homework.py", str(repo), "linear-algebra", "Worksheet A", "--due", due_date)
    run_script("build_review_indexes.py", str(repo))
    run_script("build_week_plan.py", str(repo), "--days", "14")
    run_script("rebuild_indexes.py", str(repo))
    exercise_feedback_lifecycle(repo)

    ensure_exists(repo / "courses" / "linear-algebra" / "index.md")
    ensure_exists(repo / "courses" / "linear-algebra" / "homework" / "worksheet-a.md")
    ensure_contains(repo / ".student-os" / "index" / "courses.md", "courses/linear-algebra")


def build_multi_semester(repo: Path, today: date) -> None:
    due_date = (today + timedelta(days=7)).isoformat()
    run_script("scaffold_repo.py", str(repo))
    run_script("scaffold_course.py", str(repo), "CS 101", "--semester", "2026 Fall")
    run_script("scaffold_course.py", str(repo), "Calculus II", "--semester", "2026 Fall")
    run_script(
        "scaffold_homework.py",
        str(repo),
        "2026-fall/cs-101",
        "Problem Set 1",
        "--due",
        due_date,
    )
    run_script("build_review_indexes.py", str(repo))
    run_script("build_week_plan.py", str(repo), "--days", "14")
    run_script("rebuild_indexes.py", str(repo))

    ensure_exists(repo / "semesters" / "2026-fall" / "overview.md")
    ensure_exists(repo / "tasks" / "deadlines" / "2026-fall-cs-101-problem-set-1.md")
    ensure_contains(repo / ".student-os" / "repo-profile.md", "enabled: true")
    ensure_contains(repo / "semesters" / "2026-fall" / "overview.md", "[CS 101]")
    ensure_contains(repo / ".student-os" / "index" / "courses.md", "courses/2026-fall/cs-101")


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

        build_single_semester(single_repo, today)
        build_multi_semester(multi_repo, today)
        build_legacy_layout(legacy_repo, today)
        verify_inspect_repo(multi_repo)

        if args.refresh_examples:
            EXAMPLES_ROOT.mkdir(parents=True, exist_ok=True)
            copy_repo(single_repo, EXAMPLES_ROOT / "single-semester-demo")
            copy_repo(multi_repo, EXAMPLES_ROOT / "multi-semester-demo")
            copy_repo(legacy_repo, EXAMPLES_ROOT / "legacy-layout-demo")
            for example_root in EXAMPLES_ROOT.iterdir():
                if not example_root.is_dir():
                    continue
                materialize_empty_dirs(example_root)
                normalize_text_files(example_root)

    print("OK single-semester-demo")
    print("OK multi-semester-demo")
    print("OK legacy-layout-demo")
    if args.refresh_examples:
        print(f"REFRESHED {EXAMPLES_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
