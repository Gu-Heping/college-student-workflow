#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path


DEFAULT_TOKEN_KEYS = ("MINERU_TOKEN", "MINERU_API_TOKEN")


def skill_root_dir() -> Path:
    override = os.environ.get("STUDENT_OS_SKILL_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    # Prefer the lexical install root so a legacy layout whose scripts/ entry is a
    # symlink still finds .env beside the installed skill, not only in the source
    # checkout that the symlink targets. Fall back to the resolved root when needed.
    lexical = Path(__file__).absolute().parent.parent
    resolved = Path(__file__).resolve().parent.parent
    candidates: list[Path] = []
    for candidate in (lexical, resolved):
        if candidate not in candidates:
            candidates.append(candidate)
    for candidate in candidates:
        if (candidate / ".env").is_file():
            return candidate
    for candidate in candidates:
        if (candidate / ".student-os-install.json").is_file() or (candidate / "SKILL.md").exists():
            return candidate
    return lexical


def strip_env_value(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
        return cleaned[1:-1]
    return cleaned


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        raw_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # Unreadable or non-UTF-8 .env files must not abort local-only workflows.
        return {}
    values: dict[str, str] = {}
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = strip_env_value(value)
    return values


def read_env_keys_from_files(keys: tuple[str, ...] | list[str], search_dirs: list[Path]) -> str | None:
    for search_dir in search_dirs:
        values = parse_env_file(search_dir / ".env")
        for key in keys:
            candidate = values.get(key, "").strip()
            if candidate:
                return candidate
    return None


def load_token(
    cli_token: str | None = None,
    *,
    env_keys: tuple[str, ...] | list[str] = DEFAULT_TOKEN_KEYS,
    skill_root: Path | None = None,
    cwd: Path | None = None,
) -> str | None:
    """
    Load a secret token with priority:
    CLI argument > process environment > skill-root .env > cwd .env
    """
    if cli_token is not None:
        cleaned = cli_token.strip()
        if cleaned:
            return cleaned

    for key in env_keys:
        value = os.environ.get(key)
        if value and value.strip():
            return value.strip()

    return read_env_keys_from_files(
        env_keys,
        [skill_root or skill_root_dir(), (cwd or Path.cwd()).resolve()],
    )
