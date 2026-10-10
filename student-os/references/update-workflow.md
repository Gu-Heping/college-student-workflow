# Update Workflow

Use this reference when the user asks to update, upgrade, refresh, or reinstall the installed `student-os` skill itself.

Natural language triggers:
- `update student-os`
- `更新 student-os`
- `upgrade the skill`
- `refresh the installed student-os`
- `reinstall student-os`

## Scope

This workflow is skill maintenance only.

- Update the installed `student-os` skill files.
- Do not migrate, rewrite, or inspect the user's managed vault unless the user separately asks for vault work.
- Do not treat this as a repository-governance task for the vault.

## Default behavior

1. Check before apply.
2. Identify the installed target path and install method.
3. Read `.student-os-install.json` when present.
4. Compare the installed commit with the latest commit from the configured source repo and ref.
5. Report whether an update is available.
6. Ask for confirmation before `--apply`.
7. Validate the fetched skill scripts before replacing copy installs or finalizing git-backed updates.
8. Report rollback guidance after the update.

## Safety rules

- Never modify the managed student vault during a skill update.
- Never use destructive git recovery commands such as `git reset --hard` or `git clean -fd`.
- For copy installs, preserve `.student-os-install.json` and documented local override files.
- For installs with local changes, refuse overwrite unless the user explicitly requests force.
- For symlink or git installs, prefer `git fetch` and `git pull --ff-only`.

## Command path

Run from the current workspace root (outside its agent skill directories), not by changing into an installed skill. Pass absolute updater/target paths; for a known multi-target set, pass each `--target` explicitly. Set the shell/tool's working directory outside **all** selected installs before invocation: the updater can release its own cwd, but not the parent shell's directory handle. In PowerShell, if the shell itself started inside an install, move outside and also set `[Environment]::CurrentDirectory = (Get-Location).ProviderPath`, or launch a fresh shell with an external working directory. This also lets older updater versions receive the fix safely.

Use the installed skill updater:

```bash
python /path/to/installed/student-os/scripts/update_student_os.py --check
python /path/to/installed/student-os/scripts/update_student_os.py --apply --target /path/to/installed/student-os
```

When developing from the source checkout, the repository-level wrapper remains available:

```bash
python scripts/update_student_os.py --check --target /path/to/installed/student-os
```

For a machine with multiple installed targets, use the multi-target wrapper. It discovers existing Codex, Claude Code, OpenCode, DSH, and project-scope installs, then checks or applies each target independently:

```bash
python /path/to/installed/student-os/scripts/update_all_student_os.py --check --json
python /path/to/installed/student-os/scripts/update_all_student_os.py --apply --json
```

Use repeated `--target PATH` arguments when you want to limit the run to a known set. If one target has local skill drift, the multi-target updater reports that failure and continues processing the remaining targets; use `--force` only when the user explicitly agrees to overwrite local installed-skill edits.

Copy update and backup restore automatically move the updater's own cwd outside a target being replaced, including when launched inside its `scripts/` directory. Results report `cwd_relocated`; the original working directory is restored if it still exists. Discovery and relative targets are resolved before this temporary move. If another shell or process still holds the directory on Windows, close that holder and retry from an external cwd. `--force` only authorizes local-change overwrite; it cannot release a file lock. Failed swaps retain the original install and clean staging when recovery succeeds.

For update verification, use each installed manifest, preserved override paths and compilation result. A DSH tool's `repo_commit` identifies its source checkout, not proof that an already running process hot-loaded new plugin code. Check its actual `skill_root`; new overlay/plugin configuration requires a DSH restart. Verify `.env` preservation with byte/hash comparisons without displaying its contents.

An update-only authorization does not permit writing vault feedback. Summarize encountered workflow defects in the current response; recording them under `feedback/` is a separate feedback task requiring the user's authorization. Do not scan vault notes or create feedback as a side effect of updating skills.

Useful options:
- `--target PATH`
- `--repo URL`
- `--ref REF`
- `--json`
- `--force`

## Expected final response

When the update workflow runs, the final response should include:
- installed target path
- whether the run targeted one install or multiple discovered installs
- install method
- current commit
- latest commit
- whether an update is available
- files updated or preserved
- validation result
- backup path when copy mode was used
- rollback command

## Rollback

Default rollback guidance depends on install type:

- copy install: restore from the generated backup using the installed updater, for example `/path/to/installed/student-os/scripts/update_student_os.py --restore-backup ...`
- git or symlink install: checkout the previously reported commit in the source repository if the user explicitly wants to roll back
