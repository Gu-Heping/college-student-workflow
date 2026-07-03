#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
        [sys.executable, str(script_path), *args],
        check=True,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result.stdout.strip()


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


def build_single_semester(repo: Path, today: date) -> None:
    due_date = (today + timedelta(days=8)).isoformat()
    run_script("scaffold_repo.py", str(repo))
    run_script("scaffold_course.py", str(repo), "Linear Algebra")
    run_script("scaffold_homework.py", str(repo), "linear-algebra", "Worksheet A", "--due", due_date)
    run_script("build_review_indexes.py", str(repo))
    run_script("build_week_plan.py", str(repo), "--days", "14")
    run_script("rebuild_indexes.py", str(repo))

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
    run_script("scaffold_repo.py", str(repo))
    legacy_course = repo / "courses" / "legacy-course"
    (legacy_course / "homework").mkdir(parents=True, exist_ok=True)
    (legacy_course / "reviews").mkdir(parents=True, exist_ok=True)

    run_script("scaffold_homework.py", str(repo), "legacy-course", "Legacy Sheet", "--due", due_date)
    run_script("build_review_indexes.py", str(repo))
    run_script("build_week_plan.py", str(repo), "--days", "14")

    ensure_exists(legacy_course / "homework" / "legacy-sheet.md")
    ensure_contains(repo / ".student-os" / "index" / "homework-and-reviews.md", "legacy-sheet.md")
    ensure_contains(weekly_plan, "legacy-course")


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

    print("OK single-semester-demo")
    print("OK multi-semester-demo")
    print("OK legacy-layout-demo")
    if args.refresh_examples:
        print(f"REFRESHED {EXAMPLES_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
