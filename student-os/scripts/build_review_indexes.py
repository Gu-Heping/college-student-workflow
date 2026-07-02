#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import re


def stem_without_suffix(name: str, suffix: str) -> str:
    return name[: -len(suffix)] if name.endswith(suffix) else name


def review_matches(base: str, review_name: str) -> bool:
    review_stem = stem_without_suffix(review_name, ".md")
    pattern = rf"(^|-)({re.escape(base)})(-|$)"
    return re.search(pattern, review_stem) is not None


def files_in(path: Path) -> list[str]:
    if not path.exists():
        return []
    return sorted([p.name for p in path.glob("*.md") if p.is_file()])


def main() -> int:
    parser = argparse.ArgumentParser(description="Build homework and review indexes for student repositories.")
    parser.add_argument("repo", help="Target repository root")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    out_dir = repo / ".student-os" / "index"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = ["# Homework And Review Index", ""]
    for course_dir in sorted([p for p in (repo / "courses").iterdir() if p.is_dir()]) if (repo / "courses").exists() else []:
        homework = files_in(course_dir / "homework")
        reviews = files_in(course_dir / "reviews")
        solutions = [name for name in homework if name.endswith("-solution.md")]
        assignments = [name for name in homework if not name.endswith("-solution.md")]
        summary.extend([f"## {course_dir.name}", ""])
        summary.append("### Homework")
        summary.extend([f"- {name}" for name in assignments] or ["- None"])
        summary.append("")
        summary.append("### Solutions")
        summary.extend([f"- {name}" for name in solutions] or ["- None"])
        summary.append("")
        summary.append("### Reviews")
        summary.extend([f"- {name}" for name in reviews] or ["- None"])
        summary.append("")
        summary.append("### Homework To Review Links")
        if assignments:
            for name in assignments:
                base = stem_without_suffix(name, ".md")
                related_solution = f"{base}-solution.md" if f"{base}-solution.md" in solutions else "None"
                related_review = next((review for review in reviews if review_matches(base, review)), "None")
                summary.append(f"- {name} -> solution: {related_solution} -> review: {related_review}")
        else:
            summary.append("- None")
        summary.append("")

    target = out_dir / "homework-and-reviews.md"
    target.write_text("\n".join(summary), encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
