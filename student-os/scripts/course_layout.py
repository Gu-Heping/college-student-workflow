#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


def slugify(value: str, fallback: str = "item") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or fallback


def discover_course_dirs(courses_root: Path) -> list[Path]:
    if not courses_root.exists():
        return []

    course_dirs: list[Path] = []
    for child in sorted(path for path in courses_root.iterdir() if path.is_dir()):
        if (child / "index.md").exists():
            course_dirs.append(child)
            continue

        for nested in sorted(path for path in child.iterdir() if path.is_dir()):
            if (nested / "index.md").exists():
                course_dirs.append(nested)

    return sorted(course_dirs, key=lambda path: path.relative_to(courses_root).as_posix())


def resolve_course_dir(repo: Path, course_ref: str, semester: str = "") -> Path:
    courses_root = repo / "courses"
    if not courses_root.exists():
        raise FileNotFoundError(f"Missing courses directory: {courses_root}")

    normalized_ref = Path(course_ref.replace("\\", "/"))
    direct_ref = courses_root / normalized_ref
    if (direct_ref / "index.md").exists():
        return direct_ref

    course_slug = slugify(normalized_ref.name, fallback="course")
    if semester:
        semester_slug = slugify(semester, fallback="semester")
        semester_candidate = courses_root / semester_slug / course_slug
        if (semester_candidate / "index.md").exists():
            return semester_candidate

    direct_candidate = courses_root / course_slug
    if (direct_candidate / "index.md").exists():
        return direct_candidate

    matches = [path for path in discover_course_dirs(courses_root) if path.name == course_slug]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        joined = ", ".join(path.relative_to(repo).as_posix() for path in matches)
        raise ValueError(f"Ambiguous course reference '{course_ref}'. Matches: {joined}")

    raise FileNotFoundError(f"Could not resolve course '{course_ref}' in {courses_root}")
