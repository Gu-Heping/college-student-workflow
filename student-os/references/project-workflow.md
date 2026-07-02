# Project Workflow

Use this reference for course projects, personal projects, research prototypes, and learning-by-building work.

This iteration keeps project support intentionally narrower than course, review, and planning support.

## Default project layout

- `projects/<project-slug>/index.md`
- `projects/<project-slug>/journal/`
- `projects/<project-slug>/milestones/`
- `projects/<project-slug>/references/`

## Standard actions

### Create a project

- Scaffold the project page from `templates/project.md`.
- Record owner course if the project belongs to a course.
- Create the first milestone if the request has a clear deliverable.

### Log implementation progress

- Prefer dated journal entries for substantial work sessions.
- Record blockers, decisions, and next steps.
- Link implementation notes back to coursework when relevant.

### Prepare a project review

- Summarize completed milestones.
- List unresolved risks.
- Propose the next branch or work package if git is in play.

## Git guidance

Suggested branch names:
- `project/<slug>-setup`
- `project/<slug>-milestone-1`
- `project/<slug>-review`

Suggested commit prefixes:
- `project:`
- `ops:` for repository-only support changes

## Quality rules

- Keep project goals explicit.
- Do not mix unrelated coursework and project changes in one summary when they should be reviewed separately.
- Prefer small milestone artifacts over long free-form diaries.
