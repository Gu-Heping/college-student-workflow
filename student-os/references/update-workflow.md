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

Use the repository updater:

```bash
python scripts/update_student_os.py --check
python scripts/update_student_os.py --apply --target /path/to/installed/student-os
```

Useful options:
- `--target PATH`
- `--repo URL`
- `--ref REF`
- `--json`
- `--force`

## Expected final response

When the update workflow runs, the final response should include:
- installed target path
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

- copy install: restore from the generated backup using `scripts/update_student_os.py --restore-backup ...`
- git or symlink install: checkout the previously reported commit in the source repository if the user explicitly wants to roll back
