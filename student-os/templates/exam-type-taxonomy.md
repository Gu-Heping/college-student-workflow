---
type: exam-type-taxonomy
course: {{course_name}}
status: draft
created: {{date}}
updated: {{date}}
tags: [course/{{course_slug}}, review, exam-census]
review_scope: exam-census
exam_scope: {{exam_scope}}
---

# {{course_name}} · {{exam_scope}} · 题型枚举说明

Human-readable companion to `.student-os/state/exam-census/.../taxonomy.yaml`.

## How To Build

1. Read 2–3 representative paper sidecars (`.pdf.md`).
2. List recurring problem families with stable `id` values.
3. Write / update `taxonomy.yaml` (append-only for existing ids).
4. Keep aliases and keywords short enough for later agents to match wording.

## Type Catalog

| id | name | aliases | keywords | notes |
| --- | --- | --- | --- | --- |
| {{type_id}} | {{type_name}} |  |  |  |

## Stability Rules

- Never rename an existing `id` after annotations exist.
- New question families get new ids.
- Prefer course-pack language when a pack exists.
