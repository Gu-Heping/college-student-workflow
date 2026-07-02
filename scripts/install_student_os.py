#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
import os
from pathlib import Path


SKILL_NAME = "student-os"
REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_SKILL_DIR = REPO_ROOT / SKILL_NAME
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


@dataclass(frozen=True)
class InstallTarget:
    agent: str
    scope: str
    root: Path


AGENT_PATHS = {
    "codex": {
        "user": CODEX_HOME / "skills",
        "project": Path(".codex") / "skills",
    },
    "claude": {
        "user": Path.home() / ".claude" / "skills",
        "project": Path(".claude") / "skills",
    },
    "opencode": {
        "user": Path.home() / ".config" / "opencode" / "skills",
        "project": Path(".opencode") / "skills",
    },
}

AGENT_ALIASES = {
    "all": ("codex", "claude"),
    "claude-code": ("claude",),
    "claude": ("claude",),
    "codex": ("codex",),
    "opencode": ("opencode",),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install the student-os skill for Codex, Claude Code, and OpenCode.",
    )
    parser.add_argument(
        "--agent",
        action="append",
        default=None,
        help="Target agent: codex, claude, claude-code, opencode, or all. Repeatable.",
    )
    parser.add_argument(
        "--scope",
        choices=["user", "project", "both"],
        default="user",
        help="Install globally for the user, into the current project, or both.",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "link", "copy"],
        default="auto",
        help="Install mode. 'auto' tries symlink first, then falls back to copy.",
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root for project-scoped installs. Defaults to the current directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing installation if present.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable output.",
    )
    return parser.parse_args()


def expand_agents(values: list[str]) -> list[str]:
    agents: list[str] = []
    for value in values:
        normalized = value.strip().lower()
        if normalized not in AGENT_ALIASES:
            raise SystemExit(f"Unsupported agent '{value}'. Expected codex, claude, claude-code, opencode, or all.")
        for agent in AGENT_ALIASES[normalized]:
            if agent not in agents:
                agents.append(agent)
    return agents


def scopes_for(selection: str) -> list[str]:
    if selection == "both":
        return ["user", "project"]
    return [selection]


def build_targets(agents: list[str], scope_selection: str, project_root: Path) -> list[InstallTarget]:
    targets: list[InstallTarget] = []
    for agent in agents:
        for scope in scopes_for(scope_selection):
            root = AGENT_PATHS[agent][scope]
            if scope == "project":
                root = project_root / root
            targets.append(InstallTarget(agent=agent, scope=scope, root=root.resolve()))
    return targets


def dedupe_targets(targets: list[InstallTarget]) -> list[InstallTarget]:
    deduped: list[InstallTarget] = []
    seen: set[tuple[str, str]] = set()
    for target in targets:
        destination_key = (target.scope, str((target.root / SKILL_NAME).resolve()))
        if destination_key in seen:
            continue
        seen.add(destination_key)
        deduped.append(target)
    return deduped


def ensure_skill_source() -> None:
    if not SOURCE_SKILL_DIR.exists():
        raise SystemExit(f"Skill source directory not found: {SOURCE_SKILL_DIR}")
    if not (SOURCE_SKILL_DIR / "SKILL.md").exists():
        raise SystemExit(f"Skill entrypoint not found: {SOURCE_SKILL_DIR / 'SKILL.md'}")


def remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if path.exists():
        shutil.rmtree(path)


def install_with_symlink(source: Path, target: Path) -> str:
    target.symlink_to(source, target_is_directory=True)
    return "linked"


def install_with_copy(source: Path, target: Path) -> str:
    shutil.copytree(source, target)
    return "copied"


def preferred_methods(target: InstallTarget, mode: str) -> list[str]:
    if mode == "copy":
        return ["copy"]
    if mode == "link":
        return ["link"]
    if target.scope == "project":
        return ["copy"]
    return ["link", "copy"]


def install_one(target: InstallTarget, mode: str, force: bool) -> dict[str, str]:
    target.root.mkdir(parents=True, exist_ok=True)
    destination = target.root / SKILL_NAME

    if destination.exists() or destination.is_symlink():
        same_link = destination.is_symlink() and destination.resolve() == SOURCE_SKILL_DIR.resolve()
        if same_link and not force:
            return {
                "agent": target.agent,
                "scope": target.scope,
                "destination": str(destination),
                "status": "unchanged",
                "method": "linked",
            }
        if not force:
            raise SystemExit(
                f"Destination already exists: {destination}. Re-run with --force to replace it."
            )
        remove_existing(destination)

    method_order = preferred_methods(target, mode)
    last_error: Exception | None = None
    for method in method_order:
        try:
            installed_as = install_with_symlink(SOURCE_SKILL_DIR, destination) if method == "link" else install_with_copy(SOURCE_SKILL_DIR, destination)
            return {
                "agent": target.agent,
                "scope": target.scope,
                "destination": str(destination),
                "status": "installed",
                "method": installed_as,
            }
        except OSError as exc:
            last_error = exc
            if destination.exists() or destination.is_symlink():
                remove_existing(destination)
            if mode != "auto" or len(method_order) == 1:
                raise

    if last_error is not None:
        raise SystemExit(f"Failed to install {target.agent} skill at {destination}: {last_error}")
    raise SystemExit(f"Failed to install {target.agent} skill at {destination}")


def main() -> int:
    args = parse_args()
    ensure_skill_source()

    agents = expand_agents(args.agent or ["all"])
    project_root = Path(args.project_root).resolve()
    targets = dedupe_targets(build_targets(agents, args.scope, project_root))
    results = [install_one(target, args.mode, args.force) for target in targets]

    if args.json:
        print(json.dumps({"source": str(SOURCE_SKILL_DIR), "results": results}, ensure_ascii=False, indent=2))
        return 0

    print(f"Installed {SKILL_NAME} from {SOURCE_SKILL_DIR}")
    for result in results:
        print(
            f"- {result['agent']} ({result['scope']}): {result['status']} via {result['method']} -> {result['destination']}"
        )
    print("")
    print("Restart the target agent if the skill does not appear immediately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
