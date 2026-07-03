from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path


STATUS_TO_DIR = {
    "open": "raw",
    "triaged": "triaged",
    "resolved": "resolved",
    "archived": "resolved",
}

VALID_KINDS = {
    "workflow",
    "template",
    "routing",
    "import",
    "git",
    "quality",
    "docs",
    "course-pack",
    "install",
    "other",
}
VALID_SEVERITIES = {"low", "medium", "high"}
VALID_REPRO = {"always", "sometimes", "one-off", "unclear"}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "feedback"


def quoted_yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def yaml_list(items: list[str]) -> str:
    if not items:
        return ""
    return ", ".join(quoted_yaml_string(item) for item in items)


def parse_csv(value: str) -> list[str]:
    if not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_yaml_list(value: str) -> list[str]:
    text = value.strip()
    if not text.startswith("[") or not text.endswith("]"):
        return []
    inner = text[1:-1].strip()
    if not inner:
        return []
    pattern = re.compile(r'"((?:\\.|[^"])*)"')
    items = [match.group(1).replace('\\"', '"').replace("\\\\", "\\") for match in pattern.finditer(inner)]
    if items:
        return items
    return [part.strip().strip('"') for part in inner.split(",") if part.strip()]


def normalize_scalar(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        inner = text[1:-1]
        if text[0] == '"':
            return inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner.replace("\\'", "'").replace("\\\\", "\\")
    return text


def parse_frontmatter(path: Path) -> tuple[OrderedDict[str, str], str]:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return OrderedDict(), text
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return OrderedDict(), text
    block = parts[1]
    body = parts[2]
    data: OrderedDict[str, str] = OrderedDict()
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data, body.lstrip("\n")


def dump_frontmatter(data: OrderedDict[str, str]) -> str:
    lines = ["---"]
    lines.extend(f"{key}: {value}" for key, value in data.items())
    lines.append("---")
    return "\n".join(lines)


def write_feedback(path: Path, frontmatter: OrderedDict[str, str], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"{dump_frontmatter(frontmatter)}\n\n{body.strip()}\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def extract_title(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# Feedback - "):
            return line.removeprefix("# Feedback - ").strip()
    return ""


def replace_section(body: str, heading: str, content_lines: list[str]) -> str:
    normalized = body.replace("\r\n", "\n").strip()
    lines = normalized.split("\n")
    marker = f"## {heading}"
    start = None
    for index, line in enumerate(lines):
        if line.strip() == marker:
            start = index
            break
    block = [marker, ""] + content_lines + [""]
    if start is None:
        if normalized:
            return f"{normalized}\n\n" + "\n".join(block).rstrip() + "\n"
        return "\n".join(block).rstrip() + "\n"
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    new_lines = lines[:start] + block + lines[end:]
    return "\n".join(new_lines).strip() + "\n"


def build_feedback_id(created: str, title: str) -> str:
    compact = created.replace("-", "")
    return f"fb-{compact}-{slugify(title)}"


def resolve_feedback_path(repo: Path, candidate: str) -> Path:
    path = Path(candidate)
    if not path.is_absolute():
        path = repo / candidate
    resolved = path.resolve()
    feedback_root = (repo / "feedback").resolve()
    try:
        resolved.relative_to(feedback_root)
    except ValueError as exc:
        raise SystemExit(f"Feedback path must stay under {feedback_root}: {resolved}") from exc
    return resolved


def unique_feedback_path(target_dir: Path, filename: str, source_path: Path | None = None) -> Path:
    candidate = target_dir / filename
    if source_path is not None and candidate.resolve() == source_path.resolve():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 2
    while candidate.exists():
        candidate = target_dir / f"{stem}-{counter}{suffix}"
        if source_path is not None and candidate.resolve() == source_path.resolve():
            return candidate
        counter += 1
    return candidate
