# Academic Workflow

Use this reference for course pages, note capture, homework, labs, reviews, and progress-linked academic updates.

## Default course layout

For a new course, prefer:
- `courses/<course-slug>/index.md`
- `courses/<course-slug>/notes/`
- `courses/<course-slug>/homework/`
- `courses/<course-slug>/reviews/`
- `courses/<course-slug>/references/`

## Common task patterns

### Add a new course

- Create the course folder tree.
- Create `index.md` from `templates/course-home.md`.
- Add an entry to the course index.
- If the repository tracks tasks, create milestone or exam placeholders.

### Add lecture notes

- Use a date-based filename when the class meeting is date-bound.
- Keep the note short, source-aware, and link back to the course home page.
- Update `updated` in the frontmatter.

### Add homework

- Create a course-local homework page from `templates/homework.md`.
- Create or update a related task page when the assignment has a deadline.
- Link the homework page from the course home page or course dashboard.

### Build review material

- Write final artifacts under `reviews/` or the mapped legacy path.
- Link back to the originating course and source pages.
- Separate "review digest" from "raw note dump".

## Frontmatter expectations

Examples:

```yaml
type: homework
course: Analog Electronics
status: active
created: 2026-07-02
updated: 2026-07-02
tags: [course/analog-electronics, homework]
```

## Quality rules

- Keep source attribution visible when summarizing from class notes, homework, or textbooks.
- Prefer one artifact per task or class session over giant append-only files.
- Do not fabricate grades, due dates, or coverage scope.
- If a course already uses a different internal structure, respect it and record the mapping.
