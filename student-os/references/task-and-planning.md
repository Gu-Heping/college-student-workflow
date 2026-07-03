# Task And Planning

Use this reference for DDL tracking, reminders, weekly planning, exam countdowns, and study scheduling.

## Default task layout

- `tasks/inbox/`
- `tasks/deadlines/`
- `tasks/weekly/`
- `tasks/routines/`
- `dashboards/weekly/`

## Standard actions

### Add a deadline

- Create a markdown task from `templates/task.md`.
- Include due date, linked course or project, and completion status.
- Link from a weekly or dashboard page when appropriate.

### Capture inbox items

- Use `templates/inbox-task.md`.
- Keep inbox items lightweight and easy to triage later.
- Promote them into deadline or routine tasks only after classification.

### Build a weekly plan

- Prefer one page per week.
- Prefer `templates/weekly-plan.md`.
- Group by course, project, and personal admin work.
- Link to the underlying tasks instead of copying large amounts of content.
- Separate overdue carryover from genuinely upcoming work.
- Include deadlines in the next 7 days and exams in the next 14 days when known.
- Pull in course review artifacts when they are the most relevant next-step study target.
- Pull in imported references or slides when they need to be curated into notes or reviews.
- Generate or refresh a weekly dashboard view when the repository uses `dashboards/weekly/`.

### Track exam countdowns

- Maintain a dashboard page or dedicated task entries.
- Use factual dates only; do not infer an exam date without evidence.

## Status conventions

- `draft`
- `active`
- `done`
- `archived`

## Quality rules

- Keep due dates concrete.
- Keep checklists actionable and short.
- Do not silently mark work as done unless the user or source files indicate completion.
- Weekly plans should link back to task files instead of duplicating large task bodies.
- Weekly dashboards should expose a fast snapshot: overdue count, upcoming count, inbox count, exam count, and import triage count.
