#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SKILL_NAME = "student-os"
MANIFEST_FILENAME = ".student-os-install.json"
LOCAL_OVERRIDE_NAMES = [".student-os-local-overrides", ".student-os-install.local.json"]
DEFAULT_SOURCE_REPO = "https://github.com/Gu-Heping/college-student-workflow.git"
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
    parser.add_argument(
        "--source-repo",
        default=None,
        help="Override the recorded update source repository for the installed manifest.",
    )
    parser.add_argument(
        "--source-ref",
        default=None,
        help="Override the recorded update source ref for the installed manifest.",
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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_output(*args: str, cwd: Path = REPO_ROOT) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def discover_source_ref() -> str:
    ref = git_output("rev-parse", "--abbrev-ref", "HEAD")
    if not ref or ref == "HEAD":
        return "main"
    return ref


def discover_source_repo() -> str:
    remote = git_output("config", "--get", "remote.origin.url")
    if remote:
        return remote
    return str(REPO_ROOT.resolve())


def discover_source_commit() -> str:
    return git_output("rev-parse", "HEAD")


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def should_skip_snapshot(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if rel.name == MANIFEST_FILENAME:
        return True
    if rel.parts and rel.parts[0] in LOCAL_OVERRIDE_NAMES:
        return True
    return False


def snapshot_skill_files(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    if not root.exists():
        return snapshot
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if should_skip_snapshot(path, root):
            continue
        snapshot[path.relative_to(root).as_posix()] = hash_file(path)
    return snapshot


def build_install_manifest(
    *,
    destination: Path,
    agent: str,
    scope: str,
    install_method: str,
    used_symlink: bool,
    source_repo: str | None = None,
    source_ref: str | None = None,
    installed_commit: str | None = None,
    linked_source_path: str = "",
) -> dict[str, object]:
    return {
        "manifest_version": 1,
        "skill_name": SKILL_NAME,
        "source_repo": source_repo or discover_source_repo(),
        "source_ref": source_ref or discover_source_ref(),
        "installed_commit": installed_commit or discover_source_commit(),
        "installed_at": utc_now_iso(),
        "install_method": install_method,
        "agent": agent,
        "scope": scope,
        "target_path": str(destination.resolve()),
        "used_symlink": used_symlink,
        "linked_source_path": linked_source_path,
        "local_override_paths": LOCAL_OVERRIDE_NAMES,
        "tracked_files": snapshot_skill_files(destination),
    }


def write_manifest(destination: Path, manifest: dict[str, object]) -> Path:
    manifest_path = destination / MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def same_link_install(destination: Path) -> bool:
    if destination.is_symlink() and destination.resolve() == SOURCE_SKILL_DIR.resolve():
        return True
    skill_link = destination / "SKILL.md"
    return destination.exists() and skill_link.is_symlink() and skill_link.resolve() == (SOURCE_SKILL_DIR / "SKILL.md").resolve()


def sync_linked_entries(destination: Path, source: Path) -> list[str]:
    if destination.is_symlink():
        return []
    created: list[str] = []
    for child in sorted(source.iterdir(), key=lambda item: item.name):
        if child.name == MANIFEST_FILENAME or child.name in LOCAL_OVERRIDE_NAMES:
            continue
        target_child = destination / child.name
        if target_child.exists() or target_child.is_symlink():
            continue
        target_child.symlink_to(child.resolve(), target_is_directory=child.is_dir())
        created.append(child.name)
    return created


def install_with_symlink(source: Path, target: Path) -> str:
    target.symlink_to(source.resolve(), target_is_directory=True)
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


def install_one(
    target: InstallTarget,
    mode: str,
    force: bool,
    *,
    source_repo: str | None,
    source_ref: str | None,
) -> dict[str, str]:
    target.root.mkdir(parents=True, exist_ok=True)
    destination = target.root / SKILL_NAME

    if destination.exists() or destination.is_symlink():
        if same_link_install(destination) and not force:
            sync_linked_entries(destination, SOURCE_SKILL_DIR)
            manifest_path = ""
            if not destination.is_symlink():
                manifest = build_install_manifest(
                    destination=destination,
                    agent=target.agent,
                    scope=target.scope,
                    install_method="linked",
                    used_symlink=True,
                    source_repo=source_repo,
                    source_ref=source_ref,
                    linked_source_path=str(SOURCE_SKILL_DIR.resolve()),
                )
                manifest_path = str(write_manifest(destination, manifest))
            return {
                "agent": target.agent,
                "scope": target.scope,
                "destination": str(destination),
                "status": "unchanged",
                "method": "linked",
                "manifest": manifest_path,
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
            manifest = build_install_manifest(
                destination=destination,
                agent=target.agent,
                scope=target.scope,
                install_method=installed_as,
                used_symlink=installed_as == "linked",
                source_repo=source_repo,
                source_ref=source_ref,
                linked_source_path=str(SOURCE_SKILL_DIR.resolve()) if installed_as == "linked" else "",
            )
            manifest_path = write_manifest(destination, manifest)
            return {
                "agent": target.agent,
                "scope": target.scope,
                "destination": str(destination),
                "status": "installed",
                "method": installed_as,
                "manifest": str(manifest_path),
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
    source_repo = args.source_repo or discover_source_repo()
    source_ref = args.source_ref or discover_source_ref()

    agents = expand_agents(args.agent or ["all"])
    project_root = Path(args.project_root).resolve()
    targets = dedupe_targets(build_targets(agents, args.scope, project_root))
    results = [
        install_one(
            target,
            args.mode,
            args.force,
            source_repo=source_repo,
            source_ref=source_ref,
        )
        for target in targets
    ]

    if args.json:
        print(
            json.dumps(
                {
                    "source": str(SOURCE_SKILL_DIR),
                    "source_repo": source_repo,
                    "source_ref": source_ref,
                    "source_commit": discover_source_commit(),
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(f"Installed {SKILL_NAME} from {SOURCE_SKILL_DIR}")
    for result in results:
        print(
            f"- {result['agent']} ({result['scope']}): {result['status']} via {result['method']} -> {result['destination']}"
        )
        print(f"  Manifest: {result['manifest']}")
    print("")
    print("Restart the target agent if the skill does not appear immediately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
