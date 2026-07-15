---
name: student-os
description: Git-first student knowledge base operating system for Claude Code, Codex, OpenCode, and similar agents. Use when an agent needs to initialize or govern a markdown-first knowledge repository; create course spaces, semester overviews, lecture notes, homework pages, review sheets, lab reports, weekly plans, inbox tasks, dashboards, and learning summaries; import or transform PDF, DOCX, XLSX, and PPTX materials into the repository; route work across coordinator, course tutor, project helper, review coach, planning assistant, file operator, and feedback operator roles; inspect git status and separate task-specific changes from pre-existing dirty work; prepare branch names, commit messages, and grouped change summaries for day-to-day student workflows; or safely update the installed student-os skill itself without touching the managed vault.
---

# Student OS

Run this skill as the single entry point for a university knowledge repository. Treat the target vault as a git-backed working tree where every academic or planning task should leave a clear markdown trail and a reviewable change set.

## Core workflow

1. Identify the request type: repository governance, daily academic work, project work, planning, review work, file ingestion, knowledge operations, feedback operations, skill maintenance, or git review.
2. Inspect the target repository before editing anything.
3. Choose the primary role and any supporting roles from the companion layer.
4. Resolve the target paths and templates that will be touched.
5. Make or propose the knowledge-base updates.
6. Summarize file changes and, when git is relevant, produce commit guidance without auto-committing unless the user explicitly asks.

## Inspect first

Before writing:
- Detect whether the target directory is already a git repository.
- Inspect for pre-existing dirty files, conflict files, generated caches, and binary-heavy areas.
- Detect whether the repository already resembles the standard contract or needs a mapping layer.
- Read `.student-os/repo-profile.md` if it exists before making structural decisions.

Use these scripts when helpful:
- `scripts/inspect_repo.py` for repository shape, git state, and conflict detection.
- `scripts/scaffold_repo.py` for creating the standard contract in a new or existing repository.
- `scripts/scaffold_course.py` for setting up a new course space and starter artifacts.
- `scripts/scaffold_homework.py` for creating homework, linked task artifacts, and basic backlinks.
- `scripts/pdf_probe.py` for PDF file facts such as page count and metadata.
- `scripts/pdf_to_markdown.py` for PDF import in generic or MinerU-style mode.
- `scripts/repair_markdown_import.py` for conservative cleanup of imported markdown plus repair summaries.
- `scripts/docx_to_md.py` for DOCX import into markdown reference drafts.
- `scripts/xlsx_to_md.py` for XLSX import into markdown table summaries.
- `scripts/pptx_to_md.py` for PPTX import into slide summaries.
- `scripts/log_feedback.py` for structured feedback capture into the repository.
- `scripts/triage_feedback.py` for classifying and moving feedback into the triaged queue.
- `scripts/resolve_feedback.py` for recording the shipped fix and closing the loop.
- `scripts/summarize_feedback.py` for feedback summaries, open issues, and recent resolutions.
- `scripts/build_week_plan.py` for weekly plans, near-term deadlines, and exam countdown material.
- `scripts/build_review_indexes.py` for homework and review indexes.
- `scripts/group_git_changes.py` for student-task change grouping and commit prefix suggestions.
- `scripts/rebuild_indexes.py` for regenerating course/project/task/activity indexes.
- `scripts/summarize_activity.py` for weekly summaries and recent activity reports.

## Repository contract

Default to this markdown-first structure unless the repository already has a stable alternative:
- `courses/`
- `semesters/`
- `projects/`
- `tasks/`
- `reviews/`
- `references/`
- `dashboards/`
- `feedback/`
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
Read the relevant course pack from `references/course-packs/` before producing course-specific homework or review artifacts.

Handle:
- course creation
- semester-aware course creation
- lecture notes
- homework pages
- homework solution pages
- problem analysis pages
- lab/report scaffolds
- course dashboards
- review artifacts
- weekly review digests
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
- inbox capture
- reminders
- weekly plans
- exam countdowns
- study schedules

### Document ingestion

Use `references/file-handler.md`.

Handle:
- PDF to markdown import
- imported markdown repair
- DOCX to markdown reference drafts
- XLSX to markdown summaries
- PPTX to slide summaries
- routing imported artifacts back into courses, references, reviews, or dashboards

### Knowledge operations

Use `references/knowledge-ops.md`.

Handle:
- weekly summaries
- dashboards
- cross-course links
- reference digests
- learning retrospectives

### Feedback operations

Use `references/feedback-ops.md`.

Handle:
- recording one feedback entry
- triaging one feedback entry
- triaging feedback for later implementation
- marking feedback as resolved
- generating periodic feedback summaries

### Skill maintenance

Use `references/update-workflow.md`.

Handle:
- checking installed `student-os` version metadata
- safely updating the installed skill
- reinstalling `student-os` into the existing skill location
- reporting backup and rollback guidance

Treat update requests as skill maintenance only:
- do not edit the managed vault
- do not re-run repository scaffolding against the user's notes
- do not mix vault migration work into the skill update

## Course packs

When a request targets one of the seed courses, read the matching course pack before drafting content:
- `references/course-packs/analog-electronics.md`
- `references/course-packs/calculus-ii.md`
- `references/course-packs/data-structures.md`
- `references/pdf-workflow.md`
- `references/pdf-repair-rules.md`
- `references/docx-workflow.md`
- `references/xlsx-workflow.md`
- `references/pptx-workflow.md`

If the course is not covered yet, follow the generic workflow and note that a course pack may be needed later.

## Companion role layer

Use the companion documents to keep multi-agent work consistent across runtimes:
- `companions/coordinator.md`
- `companions/course-tutor.md`
- `companions/project-helper.md`
- `companions/review-coach.md`
- `companions/planning-assistant.md`
- `companions/file-operator.md`
- `companions/feedback-operator.md`

Use the command templates to expose common entry points:
- `commands/study.md`
- `commands/project.md`
- `commands/review.md`
- `commands/plan-week.md`
- `commands/inbox.md`
- `commands/import-file.md`
- `commands/pdf-to-md.md`
- `commands/tabular-summary.md`
- `commands/feedback.md`
- `commands/update.md`

Default routing:
- `study` -> `coordinator` with `course-tutor` as the usual primary specialist
- `project` -> `coordinator` with `project-helper`
- `review` -> `coordinator` with `review-coach`
- `plan-week` -> `coordinator` with `planning-assistant`
- `inbox` -> `coordinator` with `planning-assistant`
- `import-file` -> `coordinator` with `file-operator`
- `pdf-to-md` -> `coordinator` with `file-operator`
- `tabular-summary` -> `coordinator` with `file-operator` and `planning-assistant` when the result is a planning or dashboard artifact
- `feedback` -> `coordinator` with `feedback-operator`
- `update` -> `coordinator` with the update workflow

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

Common managed artifact types in this iteration:
- `class-note`
- `course-dashboard`
- `homework`
- `homework-solution`
- `problem-analysis`
- `review-sheet`
- `chapter-review`
- `weekly-review-digest`
- `lab-report`
- `weekly-plan`
- `task`
- `project`
- `knowledge-link`
- `pdf-import-note`
- `imported-reference`
- `imported-table-summary`
- `slide-summary`
- `feedback`

## Git-first rules

- Inspect the working tree before and after the task.
- Keep "pre-existing dirty changes" separate from "changes created for this request".
- Do not stage or commit conflict files, caches, generated noise, or unknown binary blobs by default.
- Suggest a branch name when the task is large enough to deserve isolation.
- Suggest a commit title and body whenever the task changes repository-tracked files.
- Ask before any commit, push, reset, or history rewriting operation.

Default naming:
- branch prefixes: `task/`, `course/`, `review/`, `project/`, `ops/`
- commit prefixes: `course:`, `notes:`, `homework:`, `review:`, `tasks:`, `report:`, `project:`, `ops:`

Suggested student-day grouping:
- course-note updates
- homework and linked deadline updates
- homework-solution and problem-analysis updates
- weekly planning or weekly review updates
- review-sheet builds
- imported raw or repaired references
- feedback capture and summary updates
- repository ops and generated indexes

## Update workflow contract

When the user asks to update or upgrade `student-os`:
- run a check first unless the user explicitly asks to skip straight to the check result they already approved
- require one confirmation before applying the update
- limit changes to the installed skill directory
- report the current commit, latest commit, files updated, validation result, backup path, and rollback command

## Output contract

When responding after work, prefer this order:
1. `request_type`
2. `task_mode`
3. `primary_role`
4. `supporting_roles`
5. `paths_touched` or `paths_planned`
6. `target_artifacts`
7. `files_created_or_updated`
8. `change_summary`
9. `git_guidance`, when relevant:
   - `artifact_grouping`
   - `recommended_commit_split`
   - `hold_back_files`
   - `staged_candidates`
   - `ignored_candidates`
   - `suggested_branch_name`
   - `suggested_commit_title`
   - `suggested_commit_body`
   - `risks_or_holdbacks`
10. `feedback_guidance`, when relevant:
   - `feedback_id`
   - `feedback_kind`
   - `severity`
   - `reproducibility`
   - `triage_status`
   - `resolution_status`
   - `follow_up_suggestion`

## Templates

Use these templates when creating new artifacts:
- `templates/course-home.md`
- `templates/class-note.md`
- `templates/course-dashboard.md`
- `templates/semester-overview.md`
- `templates/homework.md`
- `templates/homework-solution.md`
- `templates/problem-analysis.md`
- `templates/lab-report.md`
- `templates/review-sheet.md`
- `templates/chapter-review.md`
- `templates/task.md`
- `templates/inbox-task.md`
- `templates/project.md`
- `templates/weekly-plan.md`
- `templates/weekly-review.md`
- `templates/weekly-review-digest.md`
- `templates/knowledge-link.md`
- `templates/pdf-import-note.md`
- `templates/imported-reference.md`
- `templates/imported-table-summary.md`
- `templates/slide-summary.md`
- `templates/feedback-entry.md`
- `templates/feedback-summary.md`
- `templates/repo-profile.md`

## Validation mindset

When creating or updating a repository:
- favor readable markdown over hidden state
- keep generated state reproducible
- avoid irreversible migrations
- preserve user-authored files
- generate summaries that help a later agent understand what changed
- keep companion outputs aligned with the same repository contract
- never leave visible chain-of-thought, trial steps, or "wait/retry" traces inside final homework or review artifacts
