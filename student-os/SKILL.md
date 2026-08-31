---
name: student-os
description: Git-first student knowledge base operating system for Claude Code, Codex, OpenCode, and similar agents. Use when an agent needs to initialize or govern a markdown-first knowledge repository; create course spaces, semester overviews, lecture notes, homework pages, review sheets, lab reports, weekly plans, inbox tasks, dashboards, and learning summaries; import or transform PDF, DOCX, XLSX, and PPTX materials into the repository; route work across coordinator, course tutor, project helper, review coach, planning assistant, file operator, and feedback operator roles; inspect git status and separate task-specific changes from pre-existing dirty work; prepare branch names, commit messages, and grouped change summaries for day-to-day student workflows; safely update the installed student-os skill itself without touching the managed vault; or turn structured local feedback into privacy-checked GitHub issue drafts.
---

# Student OS

Run this skill as the single entry point for a university knowledge repository. Treat the target vault as a git-backed working tree where every academic or planning task should leave a clear markdown trail and a reviewable change set.

## Hard boundaries

- The **learning vault** is a directory the user names (Obsidian vault / Markdown notes). It is **never** the `college-student-workflow` skill source checkout unless the user explicitly says they want to develop the skill itself.
- **Install / update** of this skill must not modify vault notes, courses, or feedback content. Allowed exception: `--scope project` may write only into agent skill directories inside the current project (for example `.codex/skills/student-os`, `.claude/skills/student-os`, `.opencode/skills/student-os`, `.dsh/skills/student-os`). Prefer `--scope user` for ordinary students.
- Any workflow that writes files must **inspect Git status first** and must not auto-commit unless the user explicitly asks.
- Any text destined for a **public** GitHub Issue / PR review / comment must pass privacy checks first (`prepare_github_issue.py --stdin` / `--check-only`, or `sanitize_and_post.py`). If the check fails or raises a privacy warning, **do not call `gh`**: keep a draft, redact, and wait for explicit human confirmation before publishing.

## Agent runtime context boundary

Use `references/agent-runtime-context.md` before workflows that depend on prior conversation, feedback, exam-prep quality standards, or examples from outside the current vault.

The runtime agent may rely only on the current user request, current conversation, user-provided files/images, files it can actually read in the target vault, this installed skill's docs/scripts, and tool outputs it has produced. Do not assume access to maintainer-only context such as hidden analysis, previous development sessions, external transcript files, GitHub review state, or private example vaults unless the user explicitly provides them or points to readable files.

## Intent → workflow routing

| User intent (examples) | Route |
| --- | --- |
| Install / update / upgrade `student-os` | Skill maintenance → `references/update-workflow.md` + `commands/update.md` |
| Check vault / Git status / what to commit | Repo governance → `references/vault-governance.md` + `scripts/group_git_changes.py` |
| New course / homework / notes / lab / review sheet | Academic → `references/academic-workflow.md` + `commands/study.md` / `review.md` |
| Import PDF/DOCX/PPTX/XLSX/images/legacy Office | File-handler → `references/file-handler.md` + `commands/import-file.md` / `materials-convert.md` |
| Repair imported markdown | File-handler repair → `scripts/repair_markdown_import.py` or `materials_convert.py --repair`; automatic repair means `repair_status: auto-repaired`, not human verified |
| Fill missing `.pdf.md` YAML frontmatter | File-handler → `scripts/ensure_frontmatter.py` (dry-run first, then `--apply`) |
| Build exam prep material / 整理历年卷 / 构建期中期末备考包 / 高质量题型解析 | AI-first exam prep → `commands/exam-prep-build.md` |
| Exam type census / frequency statistics / 题型普查 / 题型频率 / explicit `/exam-census` | Legacy/auxiliary exam-census → `references/exam-census-workflow.md` + `commands/exam-census.md`; not the default route for high-quality study packs |
| Record a local problem about student-os | Feedback → `references/feedback-ops.md` + `commands/feedback.md` |
| Publish to GitHub Issue | GitHub feedback → `references/github-feedback.md` + `commands/report-issue.md` |
| Sanitize text before any public post | `scripts/prepare_github_issue.py --stdin` / `--check-only` (+ `sanitize_and_post.py`) |

`materials_convert.py` takes the **source file or folder** as its only positional argument — **not** the vault path. Outputs default to sidecars beside the source (`<name>.<ext>.md`) unless `--output-root` is set.

## Core workflow

1. Identify the request type using the routing table above: repository governance, daily academic work, project work, planning, review work, file ingestion, exam-census, knowledge operations, feedback operations, skill maintenance, or git review.
2. Inspect the target repository before editing anything.
3. Choose the primary role and any supporting roles from the companion layer.
4. Resolve the target paths and templates that will be touched.
5. Make or propose the knowledge-base updates.
6. Summarize file changes and, when git is relevant, produce commit guidance without auto-committing unless the user explicitly asks.

## Inspect first

Before writing:
- Confirm the target path is the user's learning vault, not this skill's source repository (unless developing the skill).
- Detect whether the target directory is already a git repository.
- Inspect for pre-existing dirty files, conflict files, generated caches, and binary-heavy areas.
- Detect whether the repository already resembles the standard contract or needs a mapping layer.
- Read `.student-os/repo-profile.md` if it exists before making structural decisions.

Script appendix for task-specific use. Do not read or run this list wholesale. For content-writing workflows, open the relevant sources first; scripts initialize, inspect, convert, or check only when the routed workflow asks for them.
- `scripts/inspect_repo.py` for repository shape, git state, and conflict detection.
- `scripts/scaffold_repo.py` for creating the standard contract in a new or existing repository.
- `scripts/scaffold_course.py` for setting up a new course space and starter artifacts.
- `scripts/scaffold_homework.py` for creating homework, linked task artifacts, and basic backlinks.
- `scripts/pdf_probe.py` for PDF file facts such as page count and metadata.
- `scripts/pdf_to_markdown.py` for PDF import in generic or MinerU-style mode.
- `scripts/materials_convert.py` for batch conversion of mixed materials folders into markdown sidecars, including content-aware routing (MinerU API/OCR, PyMuPDF, pandoc) plus MinerU auto-split for large PDFs.
- `scripts/probe_materials.py` for per-file conversion probes used by `--method auto` and `--probe-only`.
- `scripts/token_loader.py` for shared MinerU token lookup from CLI args, process env, and skill/cwd `.env` files.
- `scripts/repair_markdown_import.py` for conservative cleanup of imported markdown plus repair summaries.
- `scripts/ensure_frontmatter.py` for batch-prepending YAML frontmatter onto `.pdf.md` sidecars that lack it (default dry-run; `--apply` to write; UTF-8 only; never overwrites existing frontmatter).
- `scripts/docx_to_md.py` for DOCX import into markdown reference drafts.
- `scripts/xlsx_to_md.py` for XLSX import into markdown table summaries.
- `scripts/pptx_to_md.py` for PPTX import into slide summaries.
- `scripts/log_feedback.py` for structured feedback capture into the repository.
- `scripts/triage_feedback.py` for classifying and moving feedback into the triaged queue.
- `scripts/resolve_feedback.py` for recording the shipped fix and closing the loop.
- `scripts/summarize_feedback.py` for feedback summaries, open issues, and recent resolutions.
- `scripts/prepare_github_issue.py` for privacy-checked GitHub issue drafts from local feedback entries, including `--stdin` / `--check-stdin` sanitization for arbitrary issue/PR/comment bodies.
- `scripts/sanitize_and_post.py` for sanitize-then-post wrappers around `gh` so held-back privacy checks cannot create empty issue/review/comment bodies.
- `scripts/publish_github_issue.py` for optional `gh issue create` publishing after explicit approval.
- `scripts/update_student_os.py` for installed-skill update checks, safe apply, and rollback guidance.
- `scripts/build_week_plan.py` for weekly plans, near-term deadlines, and exam countdown material.
- `scripts/build_review_indexes.py` for homework and review indexes.
- `scripts/init_exam_census.py` for scanning paper sidecars and writing exam-census manifests.
- `scripts/build_exam_type_stats.py` for question-type frequency reports and ranked analysis skeletons.
- `scripts/fill_type_analysis.py` for Phase A fill queues after Aggregate.
- `scripts/review_type_analysis.py` for Phase B structural quality gates.
- `scripts/build_multi_dim_stats.py` for Phase C multi-dimensional analysis drafts.
- `scripts/init_exam_deep_dive.py` for Phase D representative paper deep-dive scaffolds.
- `scripts/cross_validate_exam_census.py` for Phase E coverage / traceability checks.
- `scripts/exam_prep_build.py` for initializing AI-first exam prep workspaces from messy past papers.
- `scripts/exam_prep_check.py` for tripwire-only mechanical evidence/structure/render checks on AI-written exam prep packages; passing does not mean the material is readable or complete.
- `scripts/install_exam_census_adapters.py` for copying Claude/Cursor/OpenCode/GitHub exam-census adapters into a vault.
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
- high-quality exam prep packs from messy past papers — use **AI-first exam prep** below and `commands/exam-prep-build.md`
- exam census packs (type frequency, type analyses, prep guide) — for the full Phase A–E census pipeline use the **Exam census** section below and `references/exam-census-workflow.md`
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
Command entry points: `commands/import-file.md`, `commands/materials-convert.md`, `commands/pdf-to-md.md`, `commands/tabular-summary.md`.

Handle:
- PDF to markdown import
- mixed materials folder conversion, with MinerU API preferred for scans, images, and legacy Office files when a token is configured
- imported markdown repair
- missing YAML frontmatter on existing `.pdf.md` sidecars (`ensure_frontmatter.py`)
- DOCX to markdown reference drafts
- XLSX to markdown summaries
- PPTX to slide summaries
- routing imported artifacts back into courses, references, reviews, or dashboards

`materials_convert.py` CLI reminder:
- positional arg = **source file/dir only** (not vault)
- `--method auto` (default) probes and routes; `--method local` forces local converters; `--method api` requires a MinerU token

When already-imported `.pdf.md` sidecars lack YAML frontmatter (common before exam-census):
- run `ensure_frontmatter.py <path> --dry-run` first, then `--apply` after confirmation
- do not overwrite existing frontmatter; always use UTF-8

Import repair governance:
- Treat `repair_status: auto-repaired` as machine cleanup only; it does not mean the source has been checked against the original PDF/material.
- Only mark `verify_status: verified` after a human checks the relevant source content. AI-assisted edits should leave `verify_status: unverified` unless the user explicitly confirms human verification.
- Files with `repair_risk: needs-human-review` or repair summary risk items must be reviewed before being used as trusted exam/course material.
- `materials_convert.py --repair-only` skips `verify_status: verified` files by default; use `--include-verified` only when intentionally reprocessing verified material.

AI-assisted import repair:
- Inspect Git with a compact, task-specific preflight; for import repair prefer `scripts/group_git_changes.py <vault> --compact-json` or the DSH `student_os_group_changes` tool. Do not run a full-vault hygiene scan or `glob **/*.pdf.md` unless the user asked for broad inventory.
- If the user points to a file, screenshot, line, or course folder, start there. For vague “repair this batch” requests, select one valuable problem file and repair that file's localized Obsidian-visible issues until focused mechanical check passes or the remaining issues are evidence-blocked.
- Read the smallest useful local section, edit the target `.md` directly, then run `scripts/repair_import_check.py <file-or-folder> --json` or DSH `student_os_repair_import_check`. For one local edit, take a baseline first or use `--focus-lines`/`--focus-range` so old unrelated file risks become backlog, not this turn's failure.
- Complex semantic fixes are agent work: you may directly repair missing stems, answer/order mismatches, broken explanations, matrix formulas, and Obsidian reading structure when grounded in visible markdown, raw import text, PDF text, OCR evidence, or a user-provided screenshot. The scripts do not prove semantic correctness.
- Mechanical checks are mandatory after edits. Fix every `blocking_errors` item before reporting success. If the check cannot pass, revert the local edit or leave a clear risk note.
- Student OS managed Markdown is UTF-8 with LF line endings. Do not convert repaired Obsidian notes back to CRLF just to match old git history; treat EOL-only diffs as their own cleanup category.
- Treat Obsidian preview showing literal TeX as a real failure. Do not debug KaTeX/MathJax packages or byte-level escapes unless the user explicitly asks for renderer debugging.
- Inline math must be `$x$`, not `$ x $`; display math delimiters must each be alone on their own line. Long `array`/matrix formulas should be display blocks, and array column specs must match row cells, e.g. `{ccc|cc}` for a 3+2 augmented matrix.
- Do not write `.fixed` files, debug scripts, trace scripts, or vault-local temporary repair scripts. Use focused edits and the mechanical check output.
- Keep AI/script repairs as `repair_status: auto-repaired` and `verify_status: unverified`. Say “review passed” or “自动审查通过”, never “verified”, unless the user explicitly confirms human source verification.
- Use `repair_import_run.py` only when you want a deterministic one-step render cleanup. Use queue/case/proposal only for optional audit records, batch planning, or broad repairs where the user wants a preserved proposal trail.

When the request involves scanned PDFs, image-heavy materials, or legacy `.doc` / `.ppt` / `.xls` files:
- check whether `MINERU_TOKEN` or `MINERU_API_TOKEN` is configured before defaulting to local conversion
- if no token is configured, tell the user that `materials_convert.py --method auto` will fall back locally and that adding a MinerU token enables higher-fidelity API parsing

### AI-first exam prep

Use `commands/exam-prep-build.md` when the user wants a real study package from past papers: 真题精析、题型解析、公式总卡、答题模板、考前清单、期末/期中备考指南.

Default to this route for messy or inconsistent paper sidecars. Before writing, read `references/exam-prep-gold-standard.md`. Enter editing-teacher mode, not batch-executor mode: the agent must personally open sources, understand the questions, write Markdown body text, read its own output as a student, and edit again. Subagents may write draft prose when given a tight task contract, but the main agent must read the draft from disk,审稿, and make any needed local edits before delivery. Scripts only initialize directories, list sources, record state, and run tripwire checks. They must not generate lecture body text, worked solutions, self-test answers, or type explanations.

Broad requests must not immediately bulk-generate a complete pack. First initialize with `scripts/exam_prep_build.py`, then read the canonical exam manifest: multiple sidecars for the same exam (paper, answer, review version, combined paper+answer) are one exam, not separate `试卷精析` pages. Create/check the local quality standard, source map, and exactly one gold loop: one representative `试卷精析` plus one representative `题型解析` that the agent wrote by hand after reading actual paper/textbook/answer evidence. Run `exam_prep_check.py --stage gold-sample`, then perform a reader audit. Expand only after both pass. Then run the staged loop in small batches: v0 canonical paper deep dives plus paper-card JSONs with `repeat_status: unknown-pending-cross-paper-analysis`; after `--stage paper-v0` passes, synthesize cross-paper type/repeat/trend analysis and backfill each paper deep dive with cross-paper relationships; then create type-dossier JSONs plus `题型备课卡/` before writing `题型解析/` lecture pages and the prep pack. AI owns semantic understanding, type clustering, teaching explanations, readability, and prep strategy.

The target reader may have skipped lectures and homework and needs short-term catch-up. For `题型解析`, do not fill a blank template. Open the matching type dossier and its past-paper refs first, then write a tutoring handout: teach the textbook/lecture concepts before using them, include a symbol/concept table, give a 30-second memory card, a 2-minute writing template, method-choice rules, variants, full past-paper problem text, full worked solutions, self-tests, answers, checks, and pitfalls. Keep machine refs such as `2024-final.json#一` inside `.student-os/state/` and type-dossier JSON only; human-facing Markdown should cite readable sources such as `2018-2019 第二学期 · 一.2`. Examples and self-tests must be disjoint. Choose them to cover the dossier's method cards and common variants so a student can learn the method from examples and then self-test the same coverage. This coverage judgment is AI work; the checker only enforces source refs in state, human-readable citations in pages, de-duplication, required sections, problem/answer presence, textbook grounding, and mechanical render safety. If the past-paper pool is too small, mark the page `quality: needs-review` and write `证据不足，需人工补充` instead of inventing 自编题、模拟题、改编题.

When a checker flags missing fields or weak prose in teaching pages, open the affected page and edit the local Markdown by hand. Do not write batch regex scripts or loops to patch `题型解析`, worked examples, self-test answers, `First look`, `Answer`, `Check`, `Transfer`, or similar正文 sections; that pattern has caused broken joins such as LaTeX glued into headings.

After AI writes artifacts, run `scripts/exam_prep_check.py --stage gold-sample` before expansion, `--stage synthesis` before backfill, `--stage type-dossier` before type pages, `--stage type-analysis-sample` when drafting the first type page, then `--stage final --json --write-report`. Passing means only that tripwire structure/evidence/render checks passed. It does not mean mathematical content is human verified, and `issue_count: 0` is not proof that the material is useful to study.

Reader audit is mandatory before any "completed" report. Open and read the entry page, every subagent draft claimed as finished, at least one type-analysis page, one paper deep dive, one worked example, and one self-test answer. Report concrete fields: `subagent_drafts_reviewed`, `mechanical_tripwire_passed`, `reader_audit_passed`, `math_human_verified:false`, sampled files, blockers found, edits made, and remaining risks. If a blocker remains, keep editing or report blocked; do not claim completion.

### Exam census

Use `references/exam-census-workflow.md` and `references/exam-census-quality.md`.
Command entry: `commands/exam-census.md`.

Exam-census is a legacy/auxiliary machine-census path for type inventory, frequency statistics, and compatibility with older adapters. It is not the default route for high-quality study packs, tutoring handouts, or "整理历年卷 / 构建备考包" requests. Route those to AI-first exam prep unless the user explicitly asks for `/exam-census`, 题型普查, or frequency statistics.

Claude Code vault adapters (recommended): install with `install_exam_census_adapters.py --platforms claude`, then run `/exam-census` or ask in natural language. The installed `.claude/skills/exam-census/SKILL.md` is a full runbook the model executes directly — do **not** use the Workflow tool or custom `.claude/workflows/*.js` (experimental opt-in only).

Short phase map (details in the reference):
- **Prepare** — convert papers to `.pdf.md` sidecars (+ repair)
- **Init / taxonomy / annotate / aggregate** — manifest, type catalog, per-paper JSON, frequency + skeletons
- **Phase A** — fill type-analysis pages (`fill_type_analysis.py`)
- **Phase B** — structural quality gate (`review_type_analysis.py`)
- **Phase C** — multi-dimensional drafts (`build_multi_dim_stats.py`)
- **Phase D** — representative paper deep-dives (`init_exam_deep_dive.py`)
- **Prep pack** — 备考指南 / 公式总卡 / 答题模板 / 考前清单
- **Phase E** — coverage / traceability (`cross_validate_exam_census.py`)

Inspect Git before each writing phase; announce output paths before starting the next phase.

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
Use `references/github-feedback.md` when the user wants developer-facing or GitHub-facing publication.

Handle:
- recording one feedback entry
- turning the current unsatisfying workflow or user correction into a feedback entry
- triaging one feedback entry
- triaging feedback for later implementation
- marking feedback as resolved
- generating periodic feedback summaries
- preparing a GitHub issue draft from feedback
- publishing a GitHub issue after explicit confirmation

When a Student OS workflow fails, wastes time, produces unusable output, or the user gives a concrete correction, extract feedback from the active conversation and related artifacts. Treat the current conversation, commands, and generated files as the evidence source. For exam-prep and import-repair failures, prefer `feedback_kind: exam-prep`, `import-repair`, `agent-routing`, or `quality-gate` over a vague `other`. Local feedback may be created as part of workflow closure; GitHub publication still requires privacy checks and explicit confirmation.

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
- `references/import-repair-examples.md`
- `references/agent-runtime-context.md`
- `references/exam-prep-gold-standard.md`
- `references/docx-workflow.md`
- `references/xlsx-workflow.md`
- `references/pptx-workflow.md`
- `commands/exam-prep-build.md`
- `references/exam-census-workflow.md`
- `references/exam-census-quality.md`
- `integrations/claude/skills/exam-census/SKILL.md` (Claude Code skill entry; recommended)
- `integrations/claude/commands/exam-census.md` (Claude Code `/exam-census` command)
- `integrations/claude/workflows/exam-census.js` (experimental Claude workflow; opt-in install only)
- `integrations/cursor/rules/exam-census.mdc` (Cursor rule template)

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
- `commands/exam-prep-build.md`
- `commands/exam-census.md`
- `commands/plan-week.md`
- `commands/inbox.md`
- `commands/import-file.md`
- `commands/materials-convert.md`
- `commands/pdf-to-md.md`
- `commands/tabular-summary.md`
- `commands/feedback.md`
- `commands/report-issue.md`
- `commands/update.md`

Default routing:
- `study` -> `coordinator` with `course-tutor` as the usual primary specialist
- `project` -> `coordinator` with `project-helper`
- `review` -> `coordinator` with `review-coach`
- `exam-census` -> `coordinator` with `review-coach` (batch annotation orchestration)
- `plan-week` -> `coordinator` with `planning-assistant`
- `inbox` -> `coordinator` with `planning-assistant`
- `import-file` -> `coordinator` with `file-operator`
- `materials-convert` -> `coordinator` with `file-operator`
- `pdf-to-md` -> `coordinator` with `file-operator`
- `tabular-summary` -> `coordinator` with `file-operator` and `planning-assistant` when the result is a planning or dashboard artifact
- `feedback` -> `coordinator` with `feedback-operator`
- `report-issue` -> `coordinator` with `feedback-operator`
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

## GitHub feedback contract

When the user asks to report a `student-os` issue to the developer or GitHub:
- first capture or locate the feedback entry
- prepare an issue draft before any public posting
- run a privacy check and surface warnings clearly
- require explicit confirmation before calling `gh issue create` or sharing public issue content
- never include private vault content, secrets, personal files, or raw course material without explicit approval

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
