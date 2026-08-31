# Feedback Ops

Use this reference when the user wants to record, organize, or summarize feedback about `student-os`.

## Goals

- Capture feedback in a durable, structured format.
- Preserve the user's actual complaint, not just a polished summary.
- Make feedback easy to triage into workflow, template, routing, import, git, quality, docs, course-pack, install, or other categories.
- Keep feedback separate from ordinary tasks and repository state caches.

## When to enter the feedback flow

Use the feedback flow when the user explicitly asks to:
- record feedback
- triage a feedback item
- resolve a feedback item
- save a problem for the developer
- report a feedback item to GitHub
- summarize recent student-os issues
- mark a previously recorded feedback item as resolved
- turn the current workflow failure, poor result, or user correction into a feedback item

For ordinary successful tasks, do not create feedback noise. When the user is dissatisfied or the agent observes workflow friction that should improve the skill, proactively create or offer a local feedback entry from the current conversation and output artifacts.

Default to extracting the failure from the active workflow context: the current conversation, command summaries, file paths, visible artifact snippets, and the user's corrections.

## Default storage

- `feedback/raw/` for newly captured feedback
- `feedback/triaged/` for categorized or implementation-ready items
- `feedback/resolved/` for closed loop items
- `feedback/summaries/` for rollups

## Classification rules

Use one `feedback_kind`:
- `workflow` for friction in task flow or repository process
- `template` for poor artifact structure or missing fields
- `routing` for wrong specialist or companion hand-off
- `import` for PDF, DOCX, XLSX, or PPTX issues
- `exam-prep` for exam material construction, type analysis, reader audit, or prep-pack quality failures
- `import-repair` for imported markdown repair loops, Obsidian render failures, or OCR sidecar cleanup issues
- `agent-routing` for wrong role selection, over-broad scans, subagent misuse, or missing main-agent review
- `quality-gate` for checker false passes, misleading checks, or tripwire coverage gaps
- `git` for branch, staging, commit, or grouping issues
- `quality` for weak output quality without a narrower fit
- `docs` for missing or misleading instructions
- `course-pack` for seed-course or specialization gaps
- `install` for installer or discovery issues
- `other` when nothing else fits

Use one `severity`:
- `low` for mild friction or polish issues
- `medium` for repeated friction or partial workflow failure
- `high` for broken, misleading, or unusable results

Use one `reproducibility`:
- `always`
- `sometimes`
- `one-off`
- `unclear`

## Writing rules

- Preserve the original complaint in `What Happened`.
- Translate vague complaints into factual expectations in `Expected Behavior`.
- Record evidence paths whenever relevant.
- Record related output paths when the failure was visible in generated material.
- Record the workflow area, agent failure mode, tool failure mode, user-visible impact, and candidate skill/tool improvement when the issue came from a Student OS workflow.
- Use `evidence_source_status: summarized` when the current conversation already provides enough evidence. `evidence_log` is a legacy field name only; it does not mean an exported log file is required.
- Keep likely causes tentative unless directly supported by repository evidence.
- Prefer one feedback file per issue, even when several complaints happened on the same day.
- Always keep a stable `feedback_id` once the item has been created.
- Add a short `Developer Summary` when the raw complaint is too long or too emotional to route efficiently.

## Status flow

- New feedback starts in `feedback/raw/` with `status: open`
- Triaged feedback lives in `feedback/triaged/` with `status: triaged`
- Resolved feedback lives in `feedback/resolved/` with `status: resolved`
- Archived feedback keeps `status: archived`

When moving an item between folders, update `status` and `updated` together.

## Lifecycle helpers

Use these scripts when the repository owner wants a tighter lifecycle:
- `scripts/log_feedback.py` to create a new raw entry
- `scripts/triage_feedback.py` to classify and move an item into `feedback/triaged/`
- `scripts/resolve_feedback.py` to move an item into `feedback/resolved/` or archive it with a fix summary
- `scripts/summarize_feedback.py` with `--audience developer` to create an issue-ready developer summary inside `feedback/summaries/`
- For **GitHub Issue** drafts and publishing, continue with `references/github-feedback.md` (`prepare_github_issue.py` / `publish_github_issue.py` / `sanitize_and_post.py`) — local developer summaries are not a substitute for the privacy-checked publish path

Recommended progression:
1. Capture the issue in `feedback/raw/`, using the current conversation as the default evidence source
2. Triage it once the problem and owner are clear
3. Prepare or publish a GitHub issue when the user wants a developer-visible report
4. Resolve it only after the workflow, docs, template, or script change exists
5. Reflect the shipped outcome in `CHANGELOG.md`

## Changelog relationship

- Feedback files are the developer-facing evidence trail.
- `CHANGELOG.md` should only record released fixes or product-facing changes.
- When a feedback item is addressed and shipped, summarize its user-visible outcome in `CHANGELOG.md` under `Added`, `Changed`, or `Fixed`.
