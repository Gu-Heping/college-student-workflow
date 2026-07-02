# Knowledge Ops

Use this reference for repository-wide summaries, dashboards, cross-course links, reference digests, and retrospectives.

## Dashboard outputs

Common outputs:
- course index
- project index
- task index
- recent activity
- weekly summary
- homework index
- review index
- cross-course topic page

## Standard actions

### Rebuild indexes

- Generate course, project, and task indexes from repository files.
- Keep them deterministic so later runs replace them cleanly.

### Summarize a week

- Use recent markdown activity as the source of truth.
- Group by course, project, and task outcomes.
- Keep the summary concise and link to source pages.
- Prefer storing weekly action planning separately from retrospective summaries.

### Build cross-course links

- Extract recurring topics, methods, or tools.
- Create one digest page per meaningful theme.
- Link out instead of duplicating entire notes.

### Build homework and review indexes

- Scan course-local homework and review directories.
- Emit both course-level and repository-level views when possible.
- Capture "homework -> solution -> review" relationships when files are present.
- Keep generated indexes separate from hand-written review sheets.

## Quality rules

- Prefer summaries over duplication.
- Keep generated knowledge pages clearly labeled as generated or curated.
- Preserve manual notes when refreshing generated pages by using dedicated generated sections or separate files.
- Distinguish between "study plan", "weekly review", and "review sheet"; they serve different tasks and should not share one template.
- A weekly review digest should mention source notes and homework artifacts, then distill them into action-oriented takeaways.
