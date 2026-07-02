---
name: student-os
description: Git-first student knowledge base operating system for Claude Code, Codex, OpenCode, and similar agents. Use when an agent needs to initialize or govern a markdown-first knowledge repository; manage course notes, homework, reviews, reports, tasks, projects, and dashboards; inspect git status and separate task-specific changes from pre-existing dirty work; prepare branch names and commit messages; map an existing vault into a standardized repository contract without forcing a rename; or produce weekly summaries, progress snapshots, and cross-course knowledge links.
---

# Student OS

Run this skill as the single entry point for a university knowledge repository. Treat the target vault as a git-backed working tree where every academic or planning task should leave a clear markdown trail and a reviewable change set.

## Core workflow

1. Identify the request type: repository governance, daily academic work, project work, planning, knowledge operations, or git review.
2. Inspect the target repository before editing anything.
3. Resolve the target paths and templates that will be touched.
4. Make or propose the knowledge-base updates.
5. Summarize file changes and, when git is relevant, produce commit guidance without auto-committing unless the user explicitly asks.

## Inspect first

Before writing:
- Detect whether the target directory is already a git repository.
- Inspect for pre-existing dirty files, conflict files, generated caches, and binary-heavy areas.
- Detect whether the repository already resembles the standard contract or needs a mapping layer.
- Read `.student-os/repo-profile.md` if it exists before making structural decisions.

Use these scripts when helpful:
- `scripts/inspect_repo.py` for repository shape, git state, and conflict detection.
- `scripts/scaffold_repo.py` for creating the standard contract in a new or existing repository.
- `scripts/rebuild_indexes.py` for regenerating course/project/task/activity indexes.
- `scripts/summarize_activity.py` for weekly summaries and recent activity reports.

## Repository contract

Default to this markdown-first structure unless the repository already has a stable alternative:
- `courses/`
- `projects/`
- `tasks/`
- `reviews/`
- `references/`
- `dashboards/`
- `.student-os/`

Inside `.student-os/`, maintain:
- `repo-profile.md` for repository rules and path mappings
- `index/` for generated indexes
- `state/` for regenerable JSON state

Do not force a legacy vault to rename folders. If the repository already has a meaningful structure, map it in `repo-profile.md` and continue operating through that mapping.

## Standard behavior by request type

### Repository governance

Use `references/vault-governance.md`.

Handle:
- repository initialization
- `.gitignore` guidance
- path mapping for legacy vaults
- index rebuilds
- detection of sync-conflict files, temp outputs, and binary-heavy zones

### Academic workflow

Use `references/academic-workflow.md`.

Handle:
- course creation
- lecture notes
- homework pages
- lab/report scaffolds
- review artifacts
- progress-linked course updates

### Project workflow

Use `references/project-workflow.md`.

Handle:
- project pages
- milestones
- course-to-project links
- implementation journals
- project review summaries

### Task and planning

Use `references/task-and-planning.md`.

Handle:
- deadlines
- reminders
- weekly plans
- exam countdowns
- study schedules

### Knowledge operations

Use `references/knowledge-ops.md`.

Handle:
- weekly summaries
- dashboards
- cross-course links
- reference digests
- learning retrospectives

## File conventions

Default every managed markdown artifact to YAML frontmatter with at least:

```yaml
type: course-note | homework | review | task | project | report | reference
course:
status: draft | active | done | archived
created:
updated:
tags: []
```

Prefer ISO dates in filenames when the artifact is date-bound.

## Git-first rules

- Inspect the working tree before and after the task.
- Keep "pre-existing dirty changes" separate from "changes created for this request".
- Do not stage or commit conflict files, caches, generated noise, or unknown binary blobs by default.
- Suggest a branch name when the task is large enough to deserve isolation.
- Suggest a commit title and body whenever the task changes repository-tracked files.
- Ask before any commit, push, reset, or history rewriting operation.

Default naming:
- branch prefixes: `task/`, `course/`, `review/`, `project/`, `ops/`
- commit prefixes: `notes:`, `course:`, `review:`, `project:`, `tasks:`, `ops:`

## Output contract

When responding after work, prefer this order:
1. `request_type`
2. `paths_touched` or `paths_planned`
3. `files_created_or_updated`
4. `change_summary`
5. `git_guidance`, when relevant:
   - `staged_candidates`
   - `ignored_candidates`
   - `suggested_branch_name`
   - `suggested_commit_title`
   - `suggested_commit_body`
   - `risks_or_holdbacks`

## Templates

Use these templates when creating new artifacts:
- `templates/course-home.md`
- `templates/homework.md`
- `templates/task.md`
- `templates/project.md`
- `templates/weekly-review.md`
- `templates/repo-profile.md`

## Validation mindset

When creating or updating a repository:
- favor readable markdown over hidden state
- keep generated state reproducible
- avoid irreversible migrations
- preserve user-authored files
- generate summaries that help a later agent understand what changed
