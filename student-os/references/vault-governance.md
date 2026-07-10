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
- unknown archives
- generated caches
- local environment files

## Safety rules

- Never force-rename legacy folders just to match the standard contract.
- Never overwrite conflict files in place.
- When a path is ambiguous, store a mapping instead of guessing.
- When restructuring existing notes, keep backlinks or redirect notes if needed.
