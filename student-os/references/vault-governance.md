# Vault Governance

Use this reference when the request is about repository setup, path mapping, index maintenance, or git hygiene.

## Goals

- Make the repository usable as a markdown-first student knowledge base.
- Preserve existing structure when possible.
- Keep generated state reproducible and easy to ignore or rebuild.

## Standard contract

Preferred directories:
- `courses/`
- `semesters/`
- `projects/`
- `tasks/`
- `reviews/`
- `references/`
- `dashboards/`
- `.student-os/index/`
- `.student-os/state/`

Core repository files:
- `.student-os/repo-profile.md`
- `.gitignore`

## Legacy vault mapping

When the repository already has a custom structure:
- keep the original folders
- record canonical-to-legacy mappings in `repo-profile.md`
- keep future generated content consistent with the mapping

Example mapping:

```yaml
paths:
  courses: legacy/courses
  tasks: legacy/tasks
  projects: legacy/projects
  references: legacy/references
```

## Git hygiene

Use `scripts/inspect_repo.py` before restructuring or preparing a commit. Its snapshot should help the agent distinguish:
- canonical repository directories
- dirty git paths
- sync-conflict copies
- generated cache files
- local-only workspace or environment files
- temporary files under `tmp/` or `temp/`
- unexpectedly large files such as OCR dumps or bulky exports
- binary-heavy areas such as imported source documents or media folders

Default ignore candidates:
- `*.sync-conflict-*`
- `__pycache__/`
- `.DS_Store`
- `Thumbs.db`
- `node_modules/`
- `.obsidian/workspace*.json`
- `tmp/`
- `temp/`
- `*.log`

Default review candidates:
- newly created markdown pages
- updated dashboards
- `.student-os/repo-profile.md`
- generated index markdown

Default holdbacks:
- large media folders
- unexpectedly large exports or text dumps
- unknown archives
- generated caches
- local environment files

## Shared worktree commits

Commit/push only with user authorization. Separate sessions in the same worktree share the index and HEAD, even when they edit different files. Distinct branches in that worktree do not isolate staging. Coordinate one Git writer at a time; separate worktrees provide separate indexes when isolation is needed.

Before committing, review `git status --short`, `git diff`, `git diff --cached`, and `git rev-parse HEAD`. Keep an explicit list of approved task paths and the expected HEAD. Do not clear, stash, reset or unstage someone else's work to obtain a clean index. If a file contains mixed ownership, agree on its changes first; a path-limited commit cannot separate contributions within that file.

For whole-file changes already reviewed, use an explicit path-limited commit, for example:

```bash
git add -- ':(literal)courses/example/reviews/page.md'
git commit --only -m "review: improve page" -- ':(literal)courses/example/reviews/page.md'
```

Use repo-relative literal paths (quoted for the current shell), not a broad directory, wildcard, `git add .`, `commit -a`, or `--include`. List both old and new paths for a rename, and include deleted paths. Stage new files before committing them. Review all selected files immediately before the commit: `--only` takes their current working-tree contents, not just the hunks previously staged. It leaves unrelated staged paths out of the commit. For deliberately partial/hunk commits, use a coordinated, reviewed index instead; do not use `--only` as a staged-hunk isolation mechanism.

Recheck HEAD before the write; if it changed, stop and review the intervening commit instead of blindly proceeding. This is a drift check, not an atomic lock. Without agreement that other sessions have paused Git writes, do not claim exclusive ownership. After the commit, capture its SHA and inspect its file list/diff (for example `git show --format=fuller --stat <sha>` and `git diff-tree --no-commit-id --name-status -r <sha>`); confirm its parent, scope and that unrelated staged changes remain. An unexpected result is a reason to stop before push, not to auto-amend.

### Amend and recovery

Prefer a follow-up commit for corrections. Permission to commit or push does not authorize amend, reset or force-push. If the user explicitly wants amend, identify the exact commit SHA being amended, confirm it is still HEAD and belongs to this task, check whether it was published, review the index again, and coordinate exclusive Git writes through completion. A branch name or matching author is not proof of ownership.

Even a message-only ordinary `git commit --amend` includes staged changes. In a coordinated message-only rewrite, `git commit --amend --only -m "corrected message"` excludes unrelated staged changes; for content changes, use explicitly reviewed paths as above. Verify the resulting commit's parent, tree/diff and message. A check of HEAD before and after the command does not eliminate the race between the check and the rewrite; if exclusivity cannot be established, do not amend.

If another commit was accidentally included or rewritten, stop Git writes and preserve the current SHAs, status and reflog evidence. Do not automatically run `amend -C`, reset or force-push: `-C` copies a message and authorship, not the original tree/history, and targets the current HEAD. Explain what changed and agree on recovery with the affected writer/user. Keep private evidence local; publishing feedback is separately authorized.

## Safety rules

- Never force-rename legacy folders just to match the standard contract.
- Never overwrite conflict files in place.
- When a path is ambiguous, store a mapping instead of guessing.
- When restructuring existing notes, keep backlinks or redirect notes if needed.
