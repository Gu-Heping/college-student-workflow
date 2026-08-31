#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from update_student_os_impl import (
    SKILL_NAME,
    absolute_path,
    build_install_info,
    clone_source,
    discover_targets,
    path_exists,
    remote_latest_commit,
    replace_copy_install,
    summarize_check,
    update_git_install,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check or update every discovered student-os install instead of failing on multiple targets."
    )
    parser.add_argument("--check", action="store_true", help="Inspect all selected installs without changing files.")
    parser.add_argument("--apply", action="store_true", help="Apply updates to all selected installs.")
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help="Limit the run to one installed student-os directory. May be passed more than once.",
    )
    parser.add_argument("--repo", help="Source repo URL/path override for every selected target.")
    parser.add_argument("--ref", help="Source ref override for every selected target.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--force", action="store_true", help="Allow overwriting local installed-skill changes.")
    return parser.parse_args()


def selected_targets(explicit_targets: list[str]) -> list[Path]:
    if explicit_targets:
        raw_targets = [absolute_path(target) for target in explicit_targets]
    else:
        raw_targets = discover_targets()
    unique: list[Path] = []
    for target in raw_targets:
        if target not in unique:
            unique.append(target)
    return unique


def system_exit_message(exc: SystemExit) -> str:
    if isinstance(exc.code, int):
        return f"exited with status {exc.code}"
    return str(exc.code or "student-os updater failed")


def target_label(info: Any) -> dict[str, str]:
    agent = info.manifest.get("agent")
    scope = info.manifest.get("scope")
    return {
        "agent": str(agent) if agent else "unknown",
        "scope": str(scope) if scope else "unknown",
    }


def target_error(target: Path, stage: str, error: str) -> dict[str, object]:
    return {
        "ok": False,
        "target_path": str(target),
        "stage": stage,
        "error": error,
    }


def latest_commit_for(info: Any, latest_cache: dict[tuple[str, str], str]) -> str:
    key = (info.source_repo, info.source_ref)
    if key not in latest_cache:
        latest_cache[key] = remote_latest_commit(info.source_repo, info.source_ref)
    return latest_cache[key]


def check_target(target: Path, args: argparse.Namespace, latest_cache: dict[tuple[str, str], str]) -> dict[str, object]:
    if not path_exists(target):
        return target_error(target, "discovery", "Installed skill directory was not found.")
    try:
        info = build_install_info(target, args.repo, args.ref)
        latest_commit = latest_commit_for(info, latest_cache)
        return {
            "ok": True,
            **target_label(info),
            **summarize_check(info, latest_commit),
        }
    except SystemExit as exc:
        return target_error(target, "check", system_exit_message(exc))
    except Exception as exc:  # pragma: no cover - defensive boundary for one-target isolation.
        return target_error(target, "check", str(exc))


def apply_target(target: Path, args: argparse.Namespace, latest_cache: dict[tuple[str, str], str]) -> dict[str, object]:
    if not path_exists(target):
        return target_error(target, "discovery", "Installed skill directory was not found.")
    try:
        info = build_install_info(target, args.repo, args.ref)
        latest_commit = latest_commit_for(info, latest_cache)
        if info.install_kind in {"symlink", "git"}:
            apply_result = update_git_install(info, force=args.force)
        else:
            temp_dir, checkout_root, commit = clone_source(info.source_repo, info.source_ref)
            try:
                apply_result = replace_copy_install(
                    info,
                    force=args.force,
                    repo=info.source_repo,
                    ref=info.source_ref,
                    commit=commit,
                    source_skill_root=checkout_root / SKILL_NAME,
                )
            finally:
                temp_dir.cleanup()
        return {
            "ok": True,
            **target_label(info),
            "target_path": str(info.target),
            "install_kind": info.install_kind,
            "current_commit": info.current_commit,
            "latest_commit": latest_commit,
            **apply_result,
        }
    except SystemExit as exc:
        return target_error(target, "apply", system_exit_message(exc))
    except Exception as exc:  # pragma: no cover - defensive boundary for one-target isolation.
        return target_error(target, "apply", str(exc))


def build_payload(mode: str, targets: list[Path], results: list[dict[str, object]]) -> dict[str, object]:
    failed = [item for item in results if not item.get("ok")]
    updated = [item for item in results if item.get("ok") and item.get("updated")]
    update_available = [item for item in results if item.get("ok") and item.get("update_available")]
    return {
        "ok": not failed,
        "mode": mode,
        "target_count": len(targets),
        "updated_count": len(updated),
        "update_available_count": len(update_available),
        "failed_count": len(failed),
        "targets": results,
    }


def print_human(payload: dict[str, object]) -> None:
    print(f"student-os multi-update: {payload['mode']}")
    print(f"Targets: {payload['target_count']}")
    if payload["mode"] == "check":
        print(f"Update available: {payload['update_available_count']}")
    print(f"Updated: {payload['updated_count']}")
    print(f"Failed: {payload['failed_count']}")
    for item in payload["targets"]:
        status = "ok" if item.get("ok") else "failed"
        target = item.get("target_path", "")
        agent = item.get("agent", "unknown")
        scope = item.get("scope", "unknown")
        print(f"- [{status}] {agent}/{scope}: {target}")
        if item.get("error"):
            print(f"  error: {item['error']}")
        elif payload["mode"] == "check":
            print(f"  current: {item.get('current_commit') or 'unknown'}")
            print(f"  latest:  {item.get('latest_commit') or 'unknown'}")
            print(f"  update_available: {bool(item.get('update_available'))}")
        else:
            print(f"  updated: {bool(item.get('updated'))}")
            if item.get("backup_path"):
                print(f"  backup: {item['backup_path']}")
            if item.get("rollback_command"):
                print(f"  rollback: {item['rollback_command']}")


def main() -> int:
    args = parse_args()
    if bool(args.check) == bool(args.apply):
        raise SystemExit("Choose exactly one of --check or --apply.")

    targets = selected_targets(args.target)
    if not targets:
        payload = {
            "ok": False,
            "mode": "check" if args.check else "apply",
            "stage": "discovery",
            "error": "Unable to locate any installed student-os skills. Pass --target explicitly.",
            "target_count": 0,
            "updated_count": 0,
            "update_available_count": 0,
            "failed_count": 1,
            "targets": [],
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print_human(payload)
        return 1

    latest_cache: dict[tuple[str, str], str] = {}
    if args.check:
        results = [check_target(target, args, latest_cache) for target in targets]
        payload = build_payload("check", targets, results)
    else:
        results = [apply_target(target, args, latest_cache) for target in targets]
        payload = build_payload("apply", targets, results)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human(payload)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
