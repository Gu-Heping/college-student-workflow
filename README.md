# College Student Workflow

`college-student-workflow` is a repository for building a git-first student knowledge base workflow that can be operated by modern coding agents.

The first artifact in this repo is [`student-os`](./student-os/), a cross-agent skill designed for `Codex`, `Claude Code`, `OpenCode`, and similar tools. Its job is to help an agent treat a note vault as a markdown-first working repository for course work, homework, reviews, projects, planning, and repository hygiene.

Recent notable changes are tracked in [CHANGELOG.md](./CHANGELOG.md).

## Multi-Semester Support

`student-os` can support both single-semester and multi-semester repositories.

- Simple repositories can keep using `courses/<course>/`
- Semester-aware repositories can use `courses/<semester>/<course>/`
- Shared semester overviews live under `semesters/<semester>/`
- `.student-os/repo-profile.md` starts with `semesters.enabled: false` and flips to `true` when you scaffold semester-tagged courses

Example:

```bash
python student-os/scripts/scaffold_course.py /path/to/repo "Analog Electronics" --semester "2026 Spring"
python student-os/scripts/rebuild_indexes.py /path/to/repo
```

## Feedback Loop

`student-os` now supports a repository-native feedback loop for structured workflow improvement.

- Feedback entries live under `feedback/`
- New feedback defaults to `feedback/raw/`
- Triaged feedback lives in `feedback/triaged/`
- Resolved feedback lives in `feedback/resolved/`
- Rollups live in `feedback/summaries/`
- Each feedback item keeps a stable `feedback_id` from capture through resolution
- Developer-facing handoff summaries can be generated without binding the repo to GitHub Issues

You can capture feedback through the skill itself or by using the helper scripts directly:

```bash
python student-os/scripts/log_feedback.py /path/to/repo --title "PDF import lost diagram context"
python student-os/scripts/triage_feedback.py /path/to/repo feedback/raw/2026-07-03-pdf-import-lost-diagram-context.md
python student-os/scripts/resolve_feedback.py /path/to/repo feedback/triaged/2026-07-03-pdf-import-lost-diagram-context.md --resolution-summary "Adjusted image placeholder retention in repaired markdown."
python student-os/scripts/summarize_feedback.py /path/to/repo --title "Weekly feedback review"
python student-os/scripts/summarize_feedback.py /path/to/repo --title "Developer handoff" --audience developer
```

When a feedback item turns into a shipped improvement, summarize the user-visible outcome in [CHANGELOG.md](./CHANGELOG.md) instead of copying the full feedback entry.

## One-command install

`student-os` now ships with a cross-agent installer.

On Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

On macOS or Linux:

```bash
bash ./install.sh
```

By default this installs the skill for these user-level locations:

- Codex: `$CODEX_HOME/skills/student-os` or `~/.codex/skills/student-os`
- Claude Code: `~/.claude/skills/student-os`

OpenCode can consume the same skill from `~/.claude/skills`, so the default install avoids creating a duplicate `student-os` entry under both Claude and OpenCode.

The installer targets the native discovery path for each tool. User-scoped installs try a symlink first, then fall back to a copy if symlinks are unavailable. Project-scoped installs default to copy so the installed skill stays portable with the repository.

Useful variants:

```bash
python scripts/install_student_os.py --agent codex
python scripts/install_student_os.py --agent claude --scope project
python scripts/install_student_os.py --agent opencode
python scripts/install_student_os.py --agent opencode --scope both --force
python scripts/install_student_os.py --agent all --json
```

## Why this repo exists

Most student note systems are either:

- good at storing notes, but weak at structured execution
- good at task tracking, but disconnected from learning materials
- good at AI assistance, but poor at long-term version control

This repository is meant to close that gap. The goal is to make a student knowledge base:

- easy for humans to read and maintain
- easy for agents to inspect and update
- safe to manage with Git
- broad enough to support real student workflows instead of only note-taking

## What `student-os` does

`student-os` is a repository operating skill, not just a note template pack.

It helps an agent:

- initialize or standardize a student knowledge repository
- manage course notes, homework, reviews, and reports
- track tasks, deadlines, and weekly planning
- organize project work and milestone notes
- rebuild indexes and summarize recent activity
- inspect git status and separate task-specific changes from unrelated dirty work
- prepare branch suggestions, commit messages, and review-friendly change summaries

## Design goals

The current design follows a few core principles:

- Markdown first: core knowledge should stay readable without proprietary tooling
- Git friendly: changes should be reviewable, grouped, and safe to commit
- Agent friendly: rules, templates, and scripts should help an agent act consistently
- Legacy tolerant: existing vaults should be mappable instead of force-renamed
- Reproducible: generated indexes and state should be easy to rebuild

## Repository layout

```text
student-os/
  SKILL.md
  agents/
  references/
  scripts/
  templates/
```

## Inside `student-os`

- [student-os/SKILL.md](./student-os/SKILL.md): main skill entry point, operating rules, and output contract
- [student-os/agents/openai.yaml](./student-os/agents/openai.yaml): UI-facing metadata for environments that support skill discovery
- [student-os/references](./student-os/references): workflow guides for repository governance, academic work, planning, projects, and knowledge operations
- [student-os/scripts](./student-os/scripts): helper scripts for scaffolding, inspection, index rebuilding, and activity summaries
- [student-os/templates](./student-os/templates): reusable markdown templates for courses, homework, tasks, projects, reviews, and repo profile setup

## Standard knowledge base contract

`student-os` defaults to this markdown-first structure for a managed repository:

```text
courses/
projects/
tasks/
reviews/
references/
dashboards/
.student-os/
```

Inside `.student-os/`, the skill expects:

- `repo-profile.md`: repository rules and path mappings
- `index/`: generated markdown indexes
- `state/`: regenerable machine-readable state

If a repository already uses a different structure, the skill is designed to map it instead of forcing a rename.

## Quick start

Install the file-ingestion helper dependencies before using the PDF, DOCX, XLSX, or PPTX scripts:

```bash
pip install -r requirements.txt
```

If you want the skill to be discoverable by your agents before working in a repository, run the installer above first.

### 1. Inspect an existing vault

```bash
python student-os/scripts/inspect_repo.py /path/to/repo
```

Use this first when you want to understand whether a target directory is already a git repo, how many markdown files it has, and whether conflict files or dirty files exist.

### 2. Scaffold a new student repository

```bash
python student-os/scripts/scaffold_repo.py /path/to/repo
```

This creates the default directory contract, a starter `.gitignore`, and `.student-os/repo-profile.md`.

### 3. Rebuild indexes

```bash
python student-os/scripts/rebuild_indexes.py /path/to/repo
```

This regenerates course, project, task, and recent-activity indexes.

### 4. Summarize recent activity

```bash
python student-os/scripts/summarize_activity.py /path/to/repo --days 7
```

This prints a short markdown-oriented activity summary for recent repository work.

## Examples and smoke tests

This repository now includes generated example student knowledge bases and a repeatable smoke-test runner.

- `examples/single-semester-demo/` shows the default `courses/<course>/` layout.
- `examples/single-semester-demo/` also exercises the feedback lifecycle from raw capture to resolved summary.
- `examples/multi-semester-demo/` shows semester-aware course scaffolding and semester overviews.
- `examples/legacy-layout-demo/` keeps a legacy-style course folder without a generated course home so fallback discovery stays covered.

Run the smoke tests:

```bash
python scripts/run_smoke_tests.py
```

Refresh the checked-in examples from the real scripts:

```bash
python scripts/run_smoke_tests.py --refresh-examples
```

## Example use cases

Typical agent requests this skill is meant to support:

- "Turn this note directory into a student knowledge base repo"
- "Add a new course and create its note, homework, and review folders"
- "Create this week's homework page and link it to a deadline task"
- "Summarize what changed this week and prepare a commit message"
- "Check which current changes are safe to commit and which ones should be ignored"
- "Map my existing Obsidian vault into the standard contract without renaming everything"

## Current status

This repository currently contains the initial version of the `student-os` skill and its supporting scripts, references, and templates.

What already exists:

- one top-level cross-agent skill
- five workflow reference areas
- starter templates for common student artifacts
- helper scripts for repository setup and reporting
- a repository-native feedback lifecycle with triage, resolution, and developer-handoff summaries

What is still likely to evolve:

- richer migration support for legacy vaults
- more structured Git workflow helpers
- stronger automation around dashboards, summaries, and review generation
- broader end-to-end regression coverage for imports and multi-role collaboration

## Roadmap

Planned directions for the next iterations:

1. Add more robust legacy-vault detection and mapping rules.
2. Expand templates for labs, weekly plans, and course dashboards.
3. Add safer Git grouping helpers for mixed dirty worktrees.
4. Expand the example repositories and smoke tests into broader end-to-end regression coverage, especially for imports and multi-role collaboration.

## Notes

This repository is intentionally focused on text-first, version-controlled workflows. Binary-heavy assets can still exist in downstream repositories, but they are not the primary design target of the initial `student-os` workflow.
