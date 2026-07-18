#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path

from course_layout import configure_stdout_utf8


INTEGRATIONS_ROOT = Path(__file__).resolve().parents[1] / "integrations"

# Allowed ASCII controls in templates after CRLF normalization: TAB, LF only.
# Bare CR is rejected (can hide text in terminals / approval UIs).
_ALLOWED_CONTROLS = frozenset({"\t", "\n"})

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

LEGACY_CLAUDE_WORKFLOW_REL = Path(".claude") / "workflows" / "exam-census.js"


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
                "dest_rel": LEGACY_CLAUDE_WORKFLOW_REL,
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
    """Scan text for dangerous control characters.

    CRLF pairs are normalized to LF first so Windows line endings do not trip
    the scanner; any remaining bare CR is reported.
    """
    normalized = text.replace("\r\n", "\n")
    hits: list[dict[str, object]] = []
    for index, ch in enumerate(normalized):
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


def collect_planned_destinations(
    vault: Path,
    platforms: list[str],
    *,
    include_experimental_claude_workflow: bool,
) -> list[str]:
    planned: list[str] = []
    for platform in platforms:
        for file_spec in platform_file_specs(
            platform,
            include_experimental_claude_workflow=include_experimental_claude_workflow,
        ):
            planned.append(str(vault / file_spec["dest_rel"]))
        if platform == "claude" and not include_experimental_claude_workflow:
            planned.append(str(vault / LEGACY_CLAUDE_WORKFLOW_REL))
    # Preserve order, drop duplicates.
    seen: set[str] = set()
    unique: list[str] = []
    for path in planned:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def collect_git_baseline(vault: Path, planned_destinations: list[str]) -> dict[str, object]:
    """Report pre-existing dirty paths that overlap planned adapter writes."""
    baseline: dict[str, object] = {
        "is_git_repo": False,
        "planned_destinations": planned_destinations,
        "preexisting_dirty": [],
        "note": "",
    }
    git_dir = vault / ".git"
    if not git_dir.exists():
        baseline["note"] = "vault is not a git repository; skipped dirty-worktree check"
        return baseline

    baseline["is_git_repo"] = True
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "-uall", "--", "."],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=vault,
        )
    except OSError as exc:
        baseline["note"] = f"git status unavailable: {exc}"
        return baseline

    if result.returncode != 0:
        baseline["note"] = (
            f"git status failed (exit {result.returncode}): "
            f"{(result.stderr or result.stdout).strip()}"
        )
        return baseline

    dirty_relpaths: set[str] = set()
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path_part = line[3:]
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1]
        dirty_relpaths.add(path_part.replace("\\", "/"))

    planned_rel = {
        str(Path(path).relative_to(vault)).replace("\\", "/")
        for path in planned_destinations
    }
    overlap = sorted(path for path in dirty_relpaths if path in planned_rel)
    baseline["preexisting_dirty"] = overlap
    if overlap:
        baseline["note"] = (
            "planned adapter destinations already dirty in git; "
            "installer changes are distinct from these pre-existing paths"
        )
    else:
        baseline["note"] = "no pre-existing dirty overlap with planned adapter destinations"
    return baseline


def atomic_copy2(source: Path, dest: Path) -> None:
    """Copy source to dest via a same-directory temp file, then os.replace."""
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{dest.name}.",
        suffix=".tmp",
        dir=str(dest.parent),
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        shutil.copy2(source, tmp_path)
        os.replace(tmp_path, dest)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


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

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        assert_safe_destination(vault, dest)

        if dest.exists() and not force:
            return {
                **base,
                "status": "skipped",
                "reason": "exists (pass --force to overwrite)",
            }

        backup = ""
        if dest.exists() and force:
            backup_path = dest.with_suffix(dest.suffix + ".bak")
            assert_safe_destination(vault, backup_path)
            atomic_copy2(dest, backup_path)
            backup = str(backup_path)

        atomic_copy2(source, dest)
    except SystemExit as exc:
        return {**base, "status": "error", "error": str(exc)}
    except OSError as exc:
        return {**base, "status": "error", "error": f"filesystem error: {exc}"}

    return {
        **base,
        "status": "installed",
        "backup": backup,
    }


def retire_legacy_claude_workflow(vault: Path) -> dict[str, object] | None:
    """Back up and remove a previously default-installed workflow JS file."""
    dest = vault / LEGACY_CLAUDE_WORKFLOW_REL
    base: dict[str, object] = {
        "platform": "claude",
        "source": "",
        "destination": str(dest),
        "action": "retire_legacy_workflow",
    }
    if not dest.exists() and not dest.is_symlink():
        return None

    try:
        assert_safe_destination(vault, dest)
        backup_path = dest.with_suffix(dest.suffix + ".bak")
        assert_safe_destination(vault, backup_path)
        atomic_copy2(dest, backup_path)
        dest.unlink()
    except SystemExit as exc:
        return {**base, "status": "error", "error": str(exc)}
    except OSError as exc:
        return {**base, "status": "error", "error": f"filesystem error: {exc}"}

    return {
        **base,
        "status": "retired",
        "backup": str(backup_path),
        "reason": (
            "legacy .claude/workflows/exam-census.js is no longer installed by "
            "default; prefer /exam-census skill/command "
            "(pass --include-experimental-claude-workflow to keep/install it)"
        ),
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

    if platform == "claude" and not include_experimental_claude_workflow:
        retired = retire_legacy_claude_workflow(vault)
        if retired is not None:
            file_results.append(retired)

    statuses = [str(item["status"]) for item in file_results]
    if any(status == "error" for status in statuses):
        aggregate = "error"
    elif any(status in {"installed", "retired"} for status in statuses):
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
    planned = collect_planned_destinations(
        vault,
        platforms,
        include_experimental_claude_workflow=args.include_experimental_claude_workflow,
    )
    git_baseline = collect_git_baseline(vault, planned)

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
        "git_baseline": git_baseline,
        "results": results,
        "installed": sum(1 for item in file_items if item["status"] == "installed"),
        "skipped": sum(1 for item in file_items if item["status"] == "skipped"),
        "retired": sum(1 for item in file_items if item["status"] == "retired"),
        "errors": sum(1 for item in file_items if item["status"] == "error"),
        "include_experimental_claude_workflow": bool(
            args.include_experimental_claude_workflow
        ),
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Vault: {vault}")
        if git_baseline.get("preexisting_dirty"):
            print("  preexisting dirty (planned destinations):")
            for path in git_baseline["preexisting_dirty"]:
                print(f"    - {path}")
        elif git_baseline.get("note"):
            print(f"  git: {git_baseline['note']}")
        for item in results:
            print(f"  [{item['status']}] {item['platform']}")
            for file_item in item["files"]:
                status = file_item["status"]
                detail = (
                    file_item.get("error")
                    if status == "error"
                    else file_item.get("destination")
                )
                print(f"    [{status}] {detail}")
                if file_item.get("backup"):
                    print(f"      backup: {file_item['backup']}")
                if file_item.get("reason") and status == "retired":
                    print(f"      reason: {file_item['reason']}")
        print(
            f"Summary: installed={payload['installed']} "
            f"skipped={payload['skipped']} retired={payload['retired']} "
            f"errors={payload['errors']}"
        )

    return 1 if payload["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
