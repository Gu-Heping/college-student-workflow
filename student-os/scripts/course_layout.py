#!/usr/bin/env python3
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

COURSE_MARKERS = {"notes", "homework", "reviews", "labs", "references"}


def slugify(value: str, fallback: str = "item") -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    pieces: list[str] = []
    last_was_separator = False
    for char in normalized:
        category = unicodedata.category(char)
        if category[0] in {"L", "N"}:
            pieces.append(char.casefold())
            last_was_separator = False
            continue
        if not pieces or last_was_separator:
            continue
        pieces.append("-")
        last_was_separator = True
    slug = "".join(pieces).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or fallback


def looks_like_course_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    if (path / "index.md").exists():
        return True
    child_names = {child.name for child in path.iterdir() if child.is_dir()}
    return bool(child_names & COURSE_MARKERS)


def discover_course_dirs(courses_root: Path) -> list[Path]:
    if not courses_root.exists():
        return []

    course_dirs: list[Path] = []
    for child in sorted(path for path in courses_root.iterdir() if path.is_dir()):
        if looks_like_course_dir(child):
            course_dirs.append(child)
            continue

        for nested in sorted(path for path in child.iterdir() if path.is_dir()):
            if looks_like_course_dir(nested):
                course_dirs.append(nested)

    return sorted(course_dirs, key=lambda path: path.relative_to(courses_root).as_posix())


def resolve_course_dir(repo: Path, course_ref: str, semester: str = "") -> Path:
    courses_root = repo / "courses"
    if not courses_root.exists():
        raise FileNotFoundError(f"Missing courses directory: {courses_root}")

    normalized_ref = Path(course_ref.replace("\\", "/"))
    direct_ref = courses_root / normalized_ref
    if looks_like_course_dir(direct_ref):
        return direct_ref

    course_slug = slugify(normalized_ref.name, fallback="course")
    if semester:
        semester_slug = slugify(semester, fallback="semester")
        semester_candidate = courses_root / semester_slug / course_slug
        if looks_like_course_dir(semester_candidate):
            return semester_candidate

    direct_candidate = courses_root / course_slug
    if looks_like_course_dir(direct_candidate):
        return direct_candidate

    matches = [path for path in discover_course_dirs(courses_root) if path.name == course_slug]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        joined = ", ".join(path.relative_to(repo).as_posix() for path in matches)
        raise ValueError(f"Ambiguous course reference '{course_ref}'. Matches: {joined}")

    raise FileNotFoundError(f"Could not resolve course '{course_ref}' in {courses_root}")
