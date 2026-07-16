#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from install_student_os import (  # noqa: E402
    DEFAULT_SOURCE_REPO,
    LOCAL_OVERRIDE_NAMES,
    MANIFEST_FILENAME,
    SKILL_NAME,
    build_install_manifest,
    snapshot_skill_files,
    write_manifest,
)


DEFAULT_REF = "main"
COMMON_TARGETS = [
    Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser() / "skills" / SKILL_NAME,
    Path.home() / ".codex" / "skills" / SKILL_NAME,
    Path.home() / ".claude" / "skills" / SKILL_NAME,
    Path.home() / ".config" / "opencode" / "skills" / SKILL_NAME,
]
BACKUP_DIRNAME = ".student-os-backups"


@dataclass(frozen=True)
class InstallInfo:
    target: Path
    manifest_path: Path
    manifest: dict[str, object]
    install_kind: str
    current_commit: str
    source_ref: str
    source_repo: str
    local_changes: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely self-update an installed student-os skill.")
    parser.add_argument("--check", action="store_true", help="Inspect the installed and remote versions without changing files.")
    parser.add_argument("--apply", action="store_true", help="Apply the update after validation.")
    parser.add_argument("--target", help="Explicit path to the installed student-os directory.")
    parser.add_argument("--ref", help="Source ref to inspect or apply. Defaults to main.")
    parser.add_argument("--repo", help="Source repo URL. Defaults to the public GitHub repo.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--force", action="store_true", help="Allow overwriting local installed-skill changes.")
    parser.add_argument("--restore-backup", help="Restore a previously created backup directory into --target.")
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_run(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def git_output(*args: str, cwd: Path | None = None) -> str:
    result = git_run(*args, cwd=cwd, check=False)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def absolute_path(path: Path | str) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(path))))


def path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def load_manifest(target: Path) -> tuple[Path, dict[str, object]]:
    manifest_path = target / MANIFEST_FILENAME
    if manifest_path.exists():
        return manifest_path, json.loads(manifest_path.read_text(encoding="utf-8"))
    return manifest_path, {}


def discover_target(explicit_target: str | None, *, allow_missing: bool = False) -> Path:
    if explicit_target:
        target = absolute_path(explicit_target)
        if not allow_missing and not path_exists(target):
            raise SystemExit(f"Installed skill directory was not found: {target}")
        return target

    existing = []
    for candidate in COMMON_TARGETS:
        candidate_path = absolute_path(candidate)
        if path_exists(candidate_path):
            existing.append(candidate_path)
    unique: list[Path] = []
    for candidate in existing:
        if candidate not in unique:
            unique.append(candidate)
    if not unique:
        raise SystemExit("Unable to locate an installed student-os skill. Pass --target explicitly.")
    if len(unique) > 1:
        joined = "\n".join(f"- {candidate}" for candidate in unique)
        raise SystemExit(f"Multiple installed student-os targets were found. Pass --target explicitly:\n{joined}")
    return unique[0]


def detect_install_kind(target: Path, manifest: dict[str, object]) -> str:
    install_method = manifest.get("install_method")
    if isinstance(install_method, str):
        normalized = install_method.lower()
        if normalized in {"copy", "copied"}:
            return "copy"
        if normalized in {"link", "linked"} and (target.is_symlink() or (target / "SKILL.md").is_symlink()):
            return "symlink"
    if target.is_symlink():
        return "symlink"
    skill_entry = target / "SKILL.md"
    if skill_entry.is_symlink():
        return "symlink"
    if (target / ".git").exists():
        return "git"
    if manifest.get("used_symlink"):
        return "symlink"
    if git_output("rev-parse", "--show-toplevel", cwd=target):
        return "git"
    return "copy"


def resolve_repo_root(target: Path, install_kind: str, manifest: dict[str, object]) -> Path | None:
    if install_kind == "symlink":
        if target.is_symlink():
            return target.resolve().parent
        linked_source = manifest.get("linked_source_path")
        if isinstance(linked_source, str) and linked_source:
            return Path(linked_source).expanduser().resolve().parent
        skill_entry = target / "SKILL.md"
        if skill_entry.is_symlink():
            return skill_entry.resolve().parent.parent
        return None
    if install_kind == "git":
        repo_root = git_output("rev-parse", "--show-toplevel", cwd=target)
        return Path(repo_root) if repo_root else None
    return None


def current_commit_for_install(target: Path, install_kind: str, manifest: dict[str, object]) -> str:
    repo_root = resolve_repo_root(target, install_kind, manifest)
    if repo_root is not None:
        commit = git_output("rev-parse", "HEAD", cwd=repo_root)
        if commit:
            return commit
    installed_commit = manifest.get("installed_commit")
    return installed_commit if isinstance(installed_commit, str) else ""


def diff_against_manifest(target: Path, manifest: dict[str, object]) -> list[str]:
    tracked = manifest.get("tracked_files")
    if not isinstance(tracked, dict):
        return []
    current = snapshot_skill_files(target)
    keys = sorted(set(tracked) | set(current))
    changes: list[str] = []
    for key in keys:
        before = tracked.get(key)
        after = current.get(key)
        if before == after:
            continue
        if before is None:
            changes.append(f"added:{key}")
        elif after is None:
            changes.append(f"removed:{key}")
        else:
            changes.append(f"modified:{key}")
    return changes


def remote_latest_commit(repo: str, ref: str) -> str:
    result = git_run("ls-remote", repo, ref, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        raise SystemExit(result.stderr.strip() or f"Unable to resolve {ref} from {repo}")
    return result.stdout.split()[0]


def build_install_info(target: Path, repo: str | None, ref: str | None) -> InstallInfo:
    manifest_path, manifest = load_manifest(target)
    source_repo = repo or DEFAULT_SOURCE_REPO
    source_ref = ref or DEFAULT_REF
    if repo is None and isinstance(manifest.get("source_repo"), str) and manifest["source_repo"]:
        source_repo = str(manifest["source_repo"])
    if ref is None and isinstance(manifest.get("source_ref"), str) and manifest["source_ref"]:
        source_ref = str(manifest["source_ref"])
    install_kind = detect_install_kind(target, manifest)
    current_commit = current_commit_for_install(target, install_kind, manifest)
    local_changes = diff_against_manifest(target, manifest)
    return InstallInfo(
        target=target,
        manifest_path=manifest_path,
        manifest=manifest,
        install_kind=install_kind,
        current_commit=current_commit,
        source_ref=source_ref,
        source_repo=source_repo,
        local_changes=local_changes,
    )


def compile_python_files(skill_root: Path) -> list[str]:
    compiled: list[str] = []
    with tempfile.TemporaryDirectory(prefix="student-os-validate-") as temp_dir:
        temp_root = Path(temp_dir)
        for path in sorted(skill_root.rglob("*.py")):
            relative = path.relative_to(skill_root)
            cfile = temp_root / relative.parent / f"{relative.stem}.pyc"
            cfile.parent.mkdir(parents=True, exist_ok=True)
            py_compile.compile(str(path), cfile=str(cfile), doraise=True)
            compiled.append(relative.as_posix())
    return compiled


def clone_source(repo: str, ref: str) -> tuple[tempfile.TemporaryDirectory[str], Path, str]:
    temp_dir = tempfile.TemporaryDirectory(prefix="student-os-update-")
    checkout_root = Path(temp_dir.name)
    git_run("clone", "--depth", "1", "--branch", ref, repo, str(checkout_root))
    commit = git_output("rev-parse", "HEAD", cwd=checkout_root)
    if not commit:
        temp_dir.cleanup()
        raise SystemExit(f"Unable to determine commit for {repo}@{ref}")
    skill_root = checkout_root / SKILL_NAME
    if not (skill_root / "SKILL.md").exists():
        temp_dir.cleanup()
        raise SystemExit(f"Fetched source is missing {SKILL_NAME}/SKILL.md")
    compile_python_files(skill_root)
    return temp_dir, checkout_root, commit


def ensure_clean_or_forced(info: InstallInfo, force: bool) -> None:
    if info.local_changes and not force:
        preview = ", ".join(info.local_changes[:5])
        if len(info.local_changes) > 5:
            preview += ", ..."
        raise SystemExit(
            "Installed skill has local modifications relative to its install manifest. "
            f"Re-run with --force to overwrite them. Changed files: {preview}"
        )


def copy_override_items(source: Path, destination: Path) -> list[str]:
    preserved: list[str] = []
    for name in LOCAL_OVERRIDE_NAMES:
        item = source / name
        if not item.exists():
            continue
        preserved.append(name)
        target = destination / name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
    return preserved


def create_backup(target: Path) -> Path:
    backup_root = target.parent / BACKUP_DIRNAME
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_path = backup_root / f"{target.name}-{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    shutil.copytree(target, backup_path, symlinks=True)
    return backup_path


def git_status_paths(repo_root: Path) -> list[str]:
    result = git_run("status", "--porcelain", "--untracked-files=all", cwd=repo_root, check=False)
    if result.returncode != 0:
        return []
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path_text = line[3:]
        if " -> " in path_text:
            before, after = path_text.split(" -> ", 1)
            paths.append(Path(before).as_posix())
            paths.append(Path(after).as_posix())
            continue
        paths.append(Path(path_text).as_posix())
    return paths


def split_dirty_paths(dirty_paths: list[str]) -> tuple[list[str], list[str]]:
    skill_prefix = f"{SKILL_NAME}/"
    skill_only: list[str] = []
    outside: list[str] = []
    for path in dirty_paths:
        if path == SKILL_NAME or path.startswith(skill_prefix):
            skill_only.append(path)
        else:
            outside.append(path)
    return skill_only, outside


def current_branch(repo_root: Path) -> str:
    return git_output("rev-parse", "--abbrev-ref", "HEAD", cwd=repo_root)


def latest_stash_ref(repo_root: Path) -> str:
    return git_output("stash", "list", "-1", "--format=%gd", cwd=repo_root)


def list_relative_files(root: Path) -> list[str]:
    files: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        files.append(path.relative_to(root).as_posix())
    return files


def rollback_command_for_git(repo_root: Path, commit: str, stash_ref: str = "") -> str:
    command = f"git -C \"{repo_root}\" checkout {commit}"
    if stash_ref:
        command += f" && git -C \"{repo_root}\" stash apply {stash_ref}"
    return command


def replace_copy_install(
    info: InstallInfo,
    *,
    force: bool,
    repo: str,
    ref: str,
    commit: str,
    source_skill_root: Path,
) -> dict[str, object]:
    ensure_clean_or_forced(info, force=force)
    backup_path = create_backup(info.target)
    staging_dir = info.target.parent / f".{info.target.name}.update-staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    shutil.copytree(source_skill_root, staging_dir)
    preserved = copy_override_items(info.target, staging_dir)
    existing_manifest = dict(info.manifest)
    manifest = build_install_manifest(
        destination=staging_dir,
        agent=str(existing_manifest.get("agent") or "unknown"),
        scope=str(existing_manifest.get("scope") or "user"),
        install_method="copied",
        used_symlink=False,
        source_repo=repo,
        source_ref=ref,
        installed_commit=commit,
        linked_source_path="",
    )
    write_manifest(staging_dir, manifest)
    replaced_files = list_relative_files(staging_dir)
    previous_dir = info.target.parent / f".{info.target.name}.previous"
    if previous_dir.exists():
        shutil.rmtree(previous_dir)
    info.target.rename(previous_dir)
    try:
        staging_dir.rename(info.target)
    except Exception:
        if info.target.exists():
            shutil.rmtree(info.target)
        previous_dir.rename(info.target)
        raise
    shutil.rmtree(previous_dir)
    return {
        "updated": True,
        "install_kind": "copy",
        "updated_files": replaced_files,
        "backup_path": str(backup_path),
        "preserved_override_paths": preserved,
        "stash_ref": "",
        "rollback_command": (
            f"{sys.executable} scripts/update_student_os.py --restore-backup "
            f"\"{backup_path}\" --target \"{info.target}\""
        ),
        "validation": {"compiled_python": True},
    }


def update_git_install(info: InstallInfo, *, force: bool) -> dict[str, object]:
    repo_root = resolve_repo_root(info.target, info.install_kind, info.manifest)
    if repo_root is None:
        raise SystemExit("Unable to resolve the source repository for the installed skill.")
    branch = current_branch(repo_root)
    if branch != info.source_ref:
        raise SystemExit(
            f"Installed git-backed skill is currently on branch '{branch}', not the configured update ref '{info.source_ref}'. "
            "Switch the source checkout to the configured branch before applying the update."
        )
    dirty_paths = git_status_paths(repo_root)
    skill_dirty, outside_dirty = split_dirty_paths(dirty_paths)
    if outside_dirty:
        preview = ", ".join(outside_dirty[:5])
        if len(outside_dirty) > 5:
            preview += ", ..."
        raise SystemExit(
            "Installed git-backed skill shares a repository with unrelated local changes outside student-os. "
            f"Resolve or stash those paths manually before updating: {preview}"
        )
    stash_ref = ""
    if skill_dirty:
        if not force:
            raise SystemExit(
                "Installed git-backed skill has local changes inside student-os. Re-run with --force to overwrite them."
            )
        git_run(
            "stash",
            "push",
            "--include-untracked",
            "--message",
            "student-os self-update",
            "--",
            SKILL_NAME,
            cwd=repo_root,
        )
        stash_ref = latest_stash_ref(repo_root)
    before = git_output("rev-parse", "HEAD", cwd=repo_root)
    temp_dir, checkout_root, validated_commit = clone_source(info.source_repo, info.source_ref)
    validated_files = list_relative_files(checkout_root / SKILL_NAME)
    try:
        git_run("fetch", info.source_repo, info.source_ref, cwd=repo_root)
        fetched_commit = git_output("rev-parse", "FETCH_HEAD", cwd=repo_root)
        if validated_commit and fetched_commit and validated_commit != fetched_commit:
            raise SystemExit(
                "Validation source and fetched source do not match. Aborting to avoid applying an unvalidated git-backed update."
            )
    finally:
        temp_dir.cleanup()
    after = fetched_commit or before
    updated_files = validated_files
    if before != after:
        git_run("merge", "--ff-only", "FETCH_HEAD", cwd=repo_root)
    compile_python_files(repo_root / SKILL_NAME)
    manifest = build_install_manifest(
        destination=info.target,
        agent=str(info.manifest.get("agent") or "unknown"),
        scope=str(info.manifest.get("scope") or "user"),
        install_method="linked" if info.install_kind == "symlink" else "git",
        used_symlink=info.install_kind == "symlink",
        source_repo=info.source_repo,
        source_ref=info.source_ref,
        installed_commit=after,
        linked_source_path=str((repo_root / SKILL_NAME).resolve()) if info.install_kind == "symlink" else "",
    )
    info.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "updated": before != after,
        "install_kind": info.install_kind,
        "updated_files": updated_files,
        "backup_path": "",
        "preserved_override_paths": [],
        "stash_ref": stash_ref,
        "rollback_command": rollback_command_for_git(repo_root, before, stash_ref=stash_ref),
        "validation": {"compiled_python": True},
    }


def restore_backup(target: Path, backup_path: Path) -> dict[str, object]:
    if not backup_path.exists():
        raise SystemExit(f"Backup path does not exist: {backup_path}")
    restore_stage = target.parent / f".{target.name}.restore-staging"
    if restore_stage.exists():
        shutil.rmtree(restore_stage)
    shutil.copytree(backup_path, restore_stage, symlinks=True)
    previous_dir = target.parent / f".{target.name}.before-restore"
    if previous_dir.exists():
        shutil.rmtree(previous_dir)
    if target.exists():
        target.rename(previous_dir)
    restore_stage.rename(target)
    if previous_dir.exists():
        shutil.rmtree(previous_dir)
    return {
        "restored": True,
        "target": str(target),
        "backup_path": str(backup_path),
    }


def summarize_check(info: InstallInfo, latest_commit: str) -> dict[str, object]:
    return {
        "target_path": str(info.target),
        "install_kind": info.install_kind,
        "source_repo": info.source_repo,
        "source_ref": info.source_ref,
        "current_commit": info.current_commit,
        "latest_commit": latest_commit,
        "update_available": bool(info.current_commit and latest_commit and info.current_commit != latest_commit),
        "local_changes": info.local_changes,
        "manifest_path": str(info.manifest_path),
    }


def print_human_check(summary: dict[str, object]) -> None:
    print(f"student-os target: {summary['target_path']}")
    print(f"Install kind: {summary['install_kind']}")
    print(f"Current commit: {summary['current_commit'] or 'unknown'}")
    print(f"Latest commit: {summary['latest_commit']}")
    print(f"Update available: {'yes' if summary['update_available'] else 'no'}")
    if summary["local_changes"]:
        print("Local installed-skill changes:")
        for item in summary["local_changes"]:
            print(f"- {item}")
    else:
        print("Local installed-skill changes: none detected")


def print_human_apply(result: dict[str, object]) -> None:
    print(f"student-os target: {result['target_path']}")
    print(f"Current commit: {result['current_commit'] or 'unknown'}")
    print(f"Latest commit: {result['latest_commit']}")
    print(f"Files updated: {len(result['updated_files'])}")
    print(f"Validation: {'passed' if result['validation'].get('compiled_python') else 'failed'}")
    print(f"Backup path: {result['backup_path'] or 'not needed'}")
    if result.get("stash_ref"):
        print(f"Saved local skill changes: {result['stash_ref']}")
    print(f"Rollback command: {result['rollback_command']}")


def main() -> int:
    args = parse_args()
    if bool(args.check) == bool(args.apply) and not args.restore_backup:
        raise SystemExit("Choose exactly one of --check or --apply.")

    if args.restore_backup:
        if not args.target:
            raise SystemExit("--restore-backup requires --target.")
        target = discover_target(args.target, allow_missing=True)
        result = restore_backup(target, Path(args.restore_backup).expanduser().resolve())
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"Restored student-os from backup: {result['backup_path']}")
            print(f"Target: {result['target']}")
        return 0

    target = discover_target(args.target)

    info = build_install_info(target, args.repo, args.ref)
    latest_commit = remote_latest_commit(info.source_repo, info.source_ref)

    if args.check:
        summary = summarize_check(info, latest_commit)
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print_human_check(summary)
        return 0

    ensure_clean_or_forced(info, args.force)
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

    summary = {
        "target_path": str(info.target),
        "install_kind": info.install_kind,
        "current_commit": info.current_commit,
        "latest_commit": latest_commit,
        **apply_result,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print_human_apply(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
