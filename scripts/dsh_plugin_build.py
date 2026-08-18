from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "integrations" / "dsh"
PLUGIN_ENTRY = PLUGIN_ROOT / "dist" / "index.js"
STAMP_PATH = PLUGIN_ROOT / "dist" / ".student-os-build-stamp.json"
LOCK_DIR = PLUGIN_ROOT / "dist" / ".student-os-build.lock"
LOCK_TIMEOUT_SECONDS = 120.0

BUILD_INPUT_GLOBS = (
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "src/**/*.ts",
)
DEPENDENCY_INPUTS = ("package.json", "package-lock.json")


def json_safe_path(path: Path) -> str:
    return str(path.resolve())


def find_node_exe(path: str | None = None) -> str:
    node_exe = shutil.which("node.exe", path=path) or shutil.which("node", path=path)
    if node_exe is None:
        raise RuntimeError("Node.js executable was not found on PATH")
    return node_exe


def find_npm_exe(path: str | None = None) -> str:
    npm_exe = shutil.which("npm.cmd", path=path) or shutil.which("npm", path=path)
    if npm_exe is None:
        raise RuntimeError("npm executable was not found on PATH")
    return npm_exe


def input_files(plugin_root: Path = PLUGIN_ROOT) -> list[Path]:
    files: set[Path] = set()
    for pattern in BUILD_INPUT_GLOBS:
        for path in plugin_root.glob(pattern):
            if path.is_file():
                files.add(path.resolve())
    return sorted(files)


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(plugin_root: Path = PLUGIN_ROOT) -> dict[str, Any]:
    plugin_root = plugin_root.resolve()
    inputs: dict[str, str] = {}
    for path in input_files(plugin_root):
        inputs[path.relative_to(plugin_root).as_posix()] = digest_file(path)
    digest = hashlib.sha256()
    for relative, file_hash in sorted(inputs.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\0")
    return {"algorithm": "sha256", "digest": digest.hexdigest(), "inputs": inputs}


def dependency_fingerprint(plugin_root: Path = PLUGIN_ROOT) -> str:
    plugin_root = plugin_root.resolve()
    digest = hashlib.sha256()
    for relative in DEPENDENCY_INPUTS:
        path = plugin_root / relative
        if not path.exists():
            raise RuntimeError(f"integrations/dsh/{relative} is required for npm ci")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(digest_file(path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def read_stamp(stamp_path: Path = STAMP_PATH) -> dict[str, Any] | None:
    try:
        return json.loads(stamp_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_stamp(stamp_path: Path, build_fingerprint: dict[str, Any], dependency_hash: str) -> None:
    stamp_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "fingerprint": build_fingerprint,
        "dependency_fingerprint": dependency_hash,
        "entry": json_safe_path(stamp_path.parent / "index.js"),
    }
    stamp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def log_command(argv: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    log_path = env.get("STUDENT_OS_DSH_BUILD_LOG")
    if not log_path:
        return
    with Path(log_path).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps({"cwd": json_safe_path(cwd), "argv": argv}, ensure_ascii=False) + "\n")


def run_checked(argv: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    log_command(argv, cwd=cwd, env=env)
    try:
        return subprocess.run(
            argv,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise RuntimeError(detail) from exc


def dependencies_installed(
    plugin_root: Path,
    *,
    npm_exe: str,
    dependency_hash: str,
    stamp: dict[str, Any] | None,
    env: dict[str, str],
) -> bool:
    if not (plugin_root / "node_modules").is_dir():
        return False
    if not stamp or stamp.get("dependency_fingerprint") != dependency_hash:
        return False
    result = subprocess.run(
        [npm_exe, "ls", "--depth=0", "--json"],
        cwd=plugin_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    return result.returncode == 0


class BuildLock:
    def __init__(self, lock_dir: Path = LOCK_DIR, *, timeout_seconds: float = LOCK_TIMEOUT_SECONDS) -> None:
        self.lock_dir = lock_dir
        self.timeout_seconds = timeout_seconds
        self.acquired = False

    def __enter__(self) -> "BuildLock":
        self.lock_dir.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                self.lock_dir.mkdir()
                self.acquired = True
                try:
                    (self.lock_dir / "owner.json").write_text(
                        json.dumps({"pid": os.getpid(), "time": time.time()}, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                except Exception:
                    self.lock_dir.rmdir()
                    self.acquired = False
                    raise
                return self
            except FileExistsError:
                if time.monotonic() >= deadline:
                    owner = self.lock_dir / "owner.json"
                    detail = ""
                    try:
                        detail = f"; owner={owner.read_text(encoding='utf-8').strip()}"
                    except OSError:
                        pass
                    raise RuntimeError(f"Timed out waiting for DSH plugin build lock: {self.lock_dir}{detail}")
                time.sleep(0.2)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if not self.acquired:
            return
        try:
            owner = self.lock_dir / "owner.json"
            if owner.exists():
                owner.unlink()
            try:
                self.lock_dir.rmdir()
            except FileNotFoundError:
                pass
        finally:
            self.acquired = False


def ensure_dsh_plugin_build(
    *,
    plugin_root: Path = PLUGIN_ROOT,
    plugin_entry: Path | None = None,
    stamp_path: Path | None = None,
    lock_dir: Path | None = None,
    lock_timeout_seconds: float = LOCK_TIMEOUT_SECONDS,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    plugin_root = plugin_root.resolve()
    plugin_entry = (plugin_entry or plugin_root / "dist" / "index.js").resolve()
    stamp_path = (stamp_path or plugin_root / "dist" / ".student-os-build-stamp.json").resolve()
    lock_dir = (lock_dir or plugin_root / "dist" / ".student-os-build.lock").resolve()
    build_env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        **(env or {}),
    }

    find_node_exe(build_env.get("PATH"))
    npm_exe = find_npm_exe(build_env.get("PATH"))

    with BuildLock(lock_dir, timeout_seconds=lock_timeout_seconds):
        current_fingerprint = fingerprint(plugin_root)
        current_dependency_fingerprint = dependency_fingerprint(plugin_root)
        stamp = read_stamp(stamp_path)
        deps_ready = dependencies_installed(
            plugin_root,
            npm_exe=npm_exe,
            dependency_hash=current_dependency_fingerprint,
            stamp=stamp,
            env=build_env,
        )
        fingerprint_matches = bool(
            stamp
            and stamp.get("fingerprint", {}).get("digest") == current_fingerprint["digest"]
            and stamp.get("dependency_fingerprint") == current_dependency_fingerprint
        )

        ran_npm_ci = False
        ran_build = False
        if not deps_ready:
            run_checked([npm_exe, "ci", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=plugin_root, env=build_env)
            ran_npm_ci = True
            stamp = read_stamp(stamp_path)
            deps_ready = dependencies_installed(
                plugin_root,
                npm_exe=npm_exe,
                dependency_hash=current_dependency_fingerprint,
                stamp={
                    **(stamp or {}),
                    "dependency_fingerprint": current_dependency_fingerprint,
                },
                env=build_env,
            )
            if not deps_ready:
                raise RuntimeError("npm ci completed but integrations/dsh/node_modules is still invalid")

        if not plugin_entry.exists() or not fingerprint_matches or ran_npm_ci:
            run_checked([npm_exe, "run", "build"], cwd=plugin_root, env=build_env)
            ran_build = True

        if not plugin_entry.exists():
            raise RuntimeError(f"Plugin build did not create {plugin_entry}")

        write_stamp(stamp_path, current_fingerprint, current_dependency_fingerprint)
        return {
            "built": True,
            "reused": not ran_npm_ci and not ran_build,
            "npm_ci": ran_npm_ci,
            "build": ran_build,
            "source": json_safe_path(plugin_root),
            "entry": json_safe_path(plugin_entry),
            "fingerprint": current_fingerprint["digest"],
        }
