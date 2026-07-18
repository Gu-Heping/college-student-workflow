#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import unicodedata
from pathlib import Path

from course_layout import configure_stdout_utf8


INTEGRATIONS_ROOT = Path(__file__).resolve().parents[1] / "integrations"

# Allowed ASCII controls in templates: TAB, LF. CR is tolerated when reading
# Windows CRLF, but repository templates should be LF-only.
_ALLOWED_CONTROLS = frozenset({"\t", "\n", "\r"})

# Bidirectional / zero-width / BOM-like characters that can hide in approval UIs.
_DANGEROUS_NAMED = frozenset(
    {
        "\u200b",  # ZERO WIDTH SPACE
        "\u200c",  # ZERO WIDTH NON-JOINER
        "\u200d",  # ZERO WIDTH JOINER
        "\u200e",  # LEFT-TO-RIGHT MARK
        "\u200f",  # RIGHT-TO-LEFT MARK
        "\u202a",  # LRE
        "\u202b",  # RLE
        "\u202c",  # PDF
        "\u202d",  # LRO
        "\u202e",  # RLO
        "\u2060",  # WORD JOINER
        "\u2066",  # LRI
        "\u2067",  # RLI
        "\u2068",  # FSI
        "\u2069",  # PDI
        "\ufeff",  # BOM / ZWNBSP
    }
)


PLATFORM_MAP: dict[str, dict[str, list[dict[str, Path]]]] = {
    "claude": {
        "files": [
            {
                "source": INTEGRATIONS_ROOT
                / "claude"
                / "skills"
                / "exam-census"
                / "SKILL.md",
                "dest_rel": Path(".claude") / "skills" / "exam-census" / "SKILL.md",
            },
            {
                "source": INTEGRATIONS_ROOT / "claude" / "commands" / "exam-census.md",
                "dest_rel": Path(".claude") / "commands" / "exam-census.md",
            },
        ],
        "experimental_files": [
            {
                "source": INTEGRATIONS_ROOT / "claude" / "workflows" / "exam-census.js",
                "dest_rel": Path(".claude") / "workflows" / "exam-census.js",
            },
        ],
    },
    "cursor": {
        "files": [
            {
                "source": INTEGRATIONS_ROOT / "cursor" / "rules" / "exam-census.mdc",
                "dest_rel": Path(".cursor") / "rules" / "exam-census.mdc",
            },
        ],
    },
    "opencode": {
        "files": [
            {
                "source": INTEGRATIONS_ROOT / "opencode" / "exam-census.md",
                "dest_rel": Path(".opencode") / "exam-census.md",
            },
        ],
    },
    "github": {
        "files": [
            {
                "source": INTEGRATIONS_ROOT / "github" / "copilot-exam-census.md",
                "dest_rel": Path(".github") / "copilot-exam-census.md",
            },
        ],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Install exam-census platform adapters into a learning vault "
            "(.claude/skills+commands, .cursor/rules, .opencode, .github)."
        )
    )
    parser.add_argument(
        "vault",
        help="Target learning vault / project root (receives adapter files)",
    )
    parser.add_argument(
        "--platforms",
        default="claude,cursor,opencode,github",
        help="Comma-separated platforms: claude,cursor,opencode,github (default: all)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing adapter files (keeps a .bak copy)",
    )
    parser.add_argument(
        "--include-experimental-claude-workflow",
        action="store_true",
        help=(
            "Also install Claude .claude/workflows/exam-census.js "
            "(experimental; not recommended — prefer /exam-census skill)"
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON result",
    )
    return parser.parse_args()


def parse_platforms(raw: str) -> list[str]:
    platforms: list[str] = []
    for part in raw.split(","):
        name = part.strip().lower()
        if not name:
            continue
        if name not in PLATFORM_MAP:
            raise SystemExit(
                f"Unknown platform {name!r}. Expected one of: {', '.join(sorted(PLATFORM_MAP))}"
            )
        if name not in platforms:
            platforms.append(name)
    if not platforms:
        raise SystemExit("No platforms selected")
    return platforms


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def assert_safe_destination(vault: Path, dest: Path) -> None:
    """Reject destinations that escape the vault via symlinks or path tricks."""
    vault_resolved = vault.resolve()
    if not _is_relative_to(dest, vault) and dest != vault:
        raise SystemExit(f"Refusing destination outside vault: {dest}")

    # Refuse any symlink/junction from the destination file up through vault children.
    for ancestor in [dest, *dest.parents]:
        if ancestor == vault or ancestor.resolve() == vault_resolved:
            break
        if not _is_relative_to(ancestor, vault) and ancestor != vault:
            break
        if ancestor.is_symlink():
            raise SystemExit(f"Refusing symlink in destination path: {ancestor}")
        if ancestor.exists():
            resolved = ancestor.resolve()
            if resolved != vault_resolved and not _is_relative_to(resolved, vault_resolved):
                raise SystemExit(
                    f"Refusing destination path escaping vault via {ancestor} -> {resolved}"
                )

    parent_resolved = dest.parent.resolve()
    if parent_resolved != vault_resolved and not _is_relative_to(parent_resolved, vault_resolved):
        raise SystemExit(f"Refusing destination parent outside vault: {parent_resolved}")

    if dest.exists() or dest.is_symlink():
        if dest.is_symlink():
            raise SystemExit(f"Refusing to write through symlink destination: {dest}")
        if not _is_relative_to(dest.resolve(), vault_resolved):
            raise SystemExit(f"Refusing destination outside vault: {dest}")


def is_dangerous_control_char(ch: str) -> bool:
    """Return True for control / bidi / zero-width chars unsafe in approval UIs."""
    if ch in _ALLOWED_CONTROLS:
        return False
    if ch in _DANGEROUS_NAMED:
        return True
    code = ord(ch)
    if code == 0 or code == 0x7F:
        return True
    if code < 0x20:
        return True
    if 0x80 <= code <= 0x9F:
        return True
    category = unicodedata.category(ch)
    # Cf = format (includes many invisible controls); Cc = control
    if category in {"Cc", "Cf"} and ch not in _ALLOWED_CONTROLS:
        return True
    return False


def find_dangerous_control_chars(text: str) -> list[dict[str, object]]:
    """Scan text for dangerous control characters. Returns list of hit dicts."""
    hits: list[dict[str, object]] = []
    for index, ch in enumerate(text):
        if is_dangerous_control_char(ch):
            hits.append(
                {
                    "index": index,
                    "codepoint": f"U+{ord(ch):04X}",
                    "category": unicodedata.category(ch),
                }
            )
    return hits


def scan_integration_template(path: Path) -> list[dict[str, object]]:
    """Read a template as UTF-8 and report dangerous control characters."""
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    return find_dangerous_control_chars(text)


def platform_file_specs(
    platform: str, *, include_experimental_claude_workflow: bool
) -> list[dict[str, Path]]:
    spec = PLATFORM_MAP[platform]
    files = list(spec.get("files", []))
    if include_experimental_claude_workflow:
        files.extend(spec.get("experimental_files", []))
    return files


def install_file(
    vault: Path,
    platform: str,
    file_spec: dict[str, Path],
    *,
    force: bool,
) -> dict[str, object]:
    source = file_spec["source"]
    dest = vault / file_spec["dest_rel"]
    base: dict[str, object] = {
        "platform": platform,
        "source": str(source),
        "destination": str(dest),
    }
    if not source.is_file():
        return {
            **base,
            "status": "error",
            "error": f"missing source template: {source}",
        }

    try:
        assert_safe_destination(vault, dest)
    except SystemExit as exc:
        return {**base, "status": "error", "error": str(exc)}

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        assert_safe_destination(vault, dest)
    except SystemExit as exc:
        return {**base, "status": "error", "error": str(exc)}

    if dest.exists() and not force:
        return {
            **base,
            "status": "skipped",
            "reason": "exists (pass --force to overwrite)",
        }

    backup = ""
    if dest.exists() and force:
        backup_path = dest.with_suffix(dest.suffix + ".bak")
        try:
            assert_safe_destination(vault, backup_path)
        except SystemExit as exc:
            return {**base, "status": "error", "error": str(exc)}
        shutil.copy2(dest, backup_path)
        backup = str(backup_path)

    shutil.copy2(source, dest)
    return {
        **base,
        "status": "installed",
        "backup": backup,
    }


def install_platform(
    vault: Path,
    platform: str,
    *,
    force: bool,
    include_experimental_claude_workflow: bool,
) -> dict[str, object]:
    file_specs = platform_file_specs(
        platform,
        include_experimental_claude_workflow=include_experimental_claude_workflow,
    )
    file_results = [
        install_file(vault, platform, file_spec, force=force) for file_spec in file_specs
    ]
    statuses = [str(item["status"]) for item in file_results]
    if any(status == "error" for status in statuses):
        aggregate = "error"
    elif any(status == "installed" for status in statuses):
        aggregate = "installed"
    elif statuses and all(status == "skipped" for status in statuses):
        aggregate = "skipped"
    else:
        aggregate = "error" if not file_results else "skipped"

    return {
        "platform": platform,
        "status": aggregate,
        "files": file_results,
        "destinations": [str(item.get("destination", "")) for item in file_results],
    }


def main() -> int:
    configure_stdout_utf8()
    args = parse_args()
    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        raise SystemExit(f"Vault path is not a directory: {vault}")
    if vault.is_symlink():
        raise SystemExit(f"Refusing symlinked vault root: {vault}")

    platforms = parse_platforms(args.platforms)
    results = [
        install_platform(
            vault,
            platform,
            force=args.force,
            include_experimental_claude_workflow=args.include_experimental_claude_workflow,
        )
        for platform in platforms
    ]
    file_items = [file_item for item in results for file_item in item["files"]]
    payload = {
        "vault": str(vault),
        "results": results,
        "installed": sum(1 for item in file_items if item["status"] == "installed"),
        "skipped": sum(1 for item in file_items if item["status"] == "skipped"),
        "errors": sum(1 for item in file_items if item["status"] == "error"),
        "include_experimental_claude_workflow": bool(
            args.include_experimental_claude_workflow
        ),
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Vault: {vault}")
        for item in results:
            print(f"  [{item['status']}] {item['platform']}")
            for file_item in item["files"]:
                status = file_item["status"]
                dest = file_item.get("destination") or file_item.get("error")
                print(f"    [{status}] {dest}")
                if file_item.get("backup"):
                    print(f"      backup: {file_item['backup']}")
        print(
            f"Summary: installed={payload['installed']} "
            f"skipped={payload['skipped']} errors={payload['errors']}"
        )

    return 1 if payload["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
