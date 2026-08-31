# Academic Workflow

Use this reference for course pages, note capture, homework, labs, reviews, and progress-linked academic updates.

Before producing course-specific homework or review outputs, read the relevant course pack when one exists.

## Default course layout

For a new course, prefer:
- `courses/<course-slug>/index.md`
- `courses/<course-slug>/dashboard.md`
- `courses/<course-slug>/notes/`
- `courses/<course-slug>/homework/`
- `courses/<course-slug>/reviews/`
- `courses/<course-slug>/labs/`
- `courses/<course-slug>/references/`

If the repository actively tracks multiple semesters, or `.student-os/repo-profile.md` sets `semesters.enabled: true`, prefer:
- `courses/<semester-slug>/<course-slug>/index.md`
- `courses/<semester-slug>/<course-slug>/dashboard.md`
- `semesters/<semester-slug>/overview.md`
- `semesters/<semester-slug>/courses.md`

Slug notes:
- Keep readable Unicode slugs when the course or semester is named in Chinese or another non-ASCII script.
- Keep combining marks attached to adjacent letters so scripts like Hindi remain readable instead of breaking into separator-heavy slugs.
- Normalize whitespace and punctuation into `-`, but do not force Chinese course names into generic ASCII fallbacks like `course` or `semester`.

## Common task patterns

### Add a new course

- Create the course folder tree.
- When a semester label is known, prefer a semester-aware course path and link it from the semester overview.
- Create `index.md` from `templates/course-home.md`.
- Create `dashboard.md` from `templates/course-dashboard.md`.
- Add an entry to the course index.
- If the repository tracks tasks, create milestone or exam placeholders.

### Add lecture notes

- Use a date-based filename when the class meeting is date-bound.
- Prefer `templates/class-note.md`.
- Keep the note short, source-aware, and link back to the course home page.
- Update `updated` in the frontmatter.

### Add homework

- Create a course-local homework page from `templates/homework.md`.
- Create a solution page from `templates/homework-solution.md` when the request includes solving, derivation, or answer organization.
- Create or update a related task page when the assignment has a deadline.
- Link the homework page from the course home page and course dashboard.
- Preserve problem numbering and source metadata.

### Build homework solutions

- Use `templates/homework-solution.md` for the main solution artifact.
- Use `templates/problem-analysis.md` when one problem needs a deeper standalone explanation.
- Add `solution_status` to distinguish between derived, reference-backed, and needs-review work.
- Never leave visible retry traces, half-correct derivations, or internal self-corrections in the final artifact.
- If a step is uncertain, keep the artifact readable and mark the uncertain area for review.

### Build review material

- Write final artifacts under `reviews/` or the mapped legacy path.
- Prefer `templates/review-sheet.md`.
- Use `templates/chapter-review.md` for chapter-level consolidation.
- Use `templates/weekly-review-digest.md` for week-level synthesis.
- Link back to the originating course and source pages.
- Separate "review digest" from "raw note dump".
- Extract concepts, methods, pitfalls, and practice targets instead of merely rearranging source text.

### Build AI-first exam prep material

- Use when the user wants high-quality study material from past papers: 整理历年卷、构建期中/期末备考包、真题精析、题型解析、公式卡、答题模板、考前清单.
- Follow `commands/exam-prep-build.md` and `references/exam-prep-gold-standard.md`.
- The agent must read sources, write Markdown body text, and perform reader audit. Scripts initialize state and run tripwire checks only.
- Do not use legacy exam-census templates or skeletons as the default source for tutoring handouts.

### Build legacy exam census material

- Use only when the user explicitly wants type frequencies, 题型普查, or `/exam-census`.
- Follow `references/exam-census-workflow.md` and the `exam-census` command.
- Keep annotations and taxonomy under `.student-os/state/exam-census/<course-key>/<exam-scope-key>/`.
- Write legacy/auxiliary reports under `courses/<course-key>/reviews/<exam-scope-key>/`.
- Prefer these templates:
  - `templates/exam-type-taxonomy.md`
  - `templates/exam-type-frequency-report.md`
  - `templates/exam-type-analysis.md`
  - `templates/exam-paper-deep-dive.md`
  - `templates/exam-prep-guide.md`
  - `templates/formula-cheat-sheet.md`
  - `templates/answer-template-quickref.md`
  - `templates/pre-exam-one-hour-checklist.md`
- Rank study effort by paper appearance rate from `build_exam_type_stats.py`, not gut feel.
- After Aggregate, follow Phase A–E in `references/exam-census-quality.md` before treating the legacy census pack as structurally complete. Do not treat it as high-quality study material without AI-first source reading, rewriting, and reader audit.

### Add lab or report work

- Use `templates/lab-report.md`.
- Keep the report linked to the course home page and related task if a due date exists.
- Separate experiment setup, observations, and final write-up sections.

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

Optional fields for this iteration:

```yaml
source_artifacts:
  - courses/analog-electronics/notes/2026-09-01.md
solution_status: derived | reference-backed | needs-review
review_scope: chapter | week | topic | problem | exam-census
exam_scope: midterm | final | 期中 | 期末 | custom-label
exam_type_id: matrix-rank
```

## Quality rules

- Keep source attribution visible when summarizing from class notes, homework, or textbooks.
- Imported references from PDF, DOCX, XLSX, or PPTX should stay traceable through `source_file` or `derived_from_import`.
- Prefer one artifact per task or class session over giant append-only files.
- Do not fabricate grades, due dates, or coverage scope.
- If a course already uses a different internal structure, respect it and record the mapping.
- When creating course-local artifacts, update at least one backlink from the course home page or dashboard.
- Homework solutions must not contain trial traces such as "wait", "retry", "wrong", or other process artifacts.
- Review artifacts must explain what was distilled, not just list source filenames.
