#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from course_layout import configure_stdout_utf8


INTEGRATIONS_ROOT = Path(__file__).resolve().parents[1] / "integrations"

PLATFORM_MAP = {
    "claude": {
        "source": INTEGRATIONS_ROOT / "claude" / "workflows" / "exam-census.js",
        "dest_rel": Path(".claude") / "workflows" / "exam-census.js",
    },
    "cursor": {
        "source": INTEGRATIONS_ROOT / "cursor" / "rules" / "exam-census.mdc",
        "dest_rel": Path(".cursor") / "rules" / "exam-census.mdc",
    },
    "opencode": {
        "source": INTEGRATIONS_ROOT / "opencode" / "exam-census.md",
        "dest_rel": Path(".opencode") / "exam-census.md",
    },
    "github": {
        "source": INTEGRATIONS_ROOT / "github" / "copilot-exam-census.md",
        "dest_rel": Path(".github") / "copilot-exam-census.md",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Install exam-census platform adapters into a learning vault "
            "(.claude/workflows, .cursor/rules, .opencode, .github)."
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


def install_one(vault: Path, platform: str, *, force: bool) -> dict[str, object]:
    spec = PLATFORM_MAP[platform]
    source: Path = spec["source"]
    dest = vault / spec["dest_rel"]
    if not source.is_file():
        return {
            "platform": platform,
            "status": "error",
            "error": f"missing source template: {source}",
        }

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        return {
            "platform": platform,
            "status": "skipped",
            "destination": str(dest),
            "reason": "exists (pass --force to overwrite)",
        }

    backup = ""
    if dest.exists() and force:
        backup_path = dest.with_suffix(dest.suffix + ".bak")
        shutil.copy2(dest, backup_path)
        backup = str(backup_path)

    shutil.copy2(source, dest)
    return {
        "platform": platform,
        "status": "installed",
        "source": str(source),
        "destination": str(dest),
        "backup": backup,
    }


def main() -> int:
    configure_stdout_utf8()
    args = parse_args()
    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        raise SystemExit(f"Vault path is not a directory: {vault}")

    platforms = parse_platforms(args.platforms)
    results = [install_one(vault, platform, force=args.force) for platform in platforms]
    payload = {
        "vault": str(vault),
        "results": results,
        "installed": sum(1 for item in results if item["status"] == "installed"),
        "skipped": sum(1 for item in results if item["status"] == "skipped"),
        "errors": sum(1 for item in results if item["status"] == "error"),
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Vault: {vault}")
        for item in results:
            status = item["status"]
            dest = item.get("destination") or item.get("error")
            print(f"  [{status}] {item['platform']}: {dest}")
            if item.get("backup"):
                print(f"    backup: {item['backup']}")
        print(
            f"Summary: installed={payload['installed']} "
            f"skipped={payload['skipped']} errors={payload['errors']}"
        )

    return 1 if payload["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
