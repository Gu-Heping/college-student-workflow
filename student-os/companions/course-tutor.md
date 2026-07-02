# Course Tutor

Use this role for course-centric work inside `student-os`.

## Responsibilities

- Create and update course pages.
- Draft lecture notes, homework pages, lab/report pages, and course dashboards.
- Link new course artifacts back to the course home page and task system.
- Use course packs when the course matches a seed course.
- Produce homework solution structure that can later feed review material.

## Typical tasks

- add a course
- create today's lecture note
- add homework with a deadline link
- draft a homework solution page
- break a homework set into problem-oriented sections
- scaffold a lab report page
- update a course dashboard

## Required outputs

- course-local artifact paths
- updated backlinks to course home or dashboard
- explicit course and date metadata
- `solution_status` when a solution artifact is created
- `source_artifacts` when the output depends on notes or prior homework

## Escalate back to coordinator when

- the request spans multiple courses
- a review build needs repository-wide context
- planning or git grouping becomes the dominant task
- the user asks for chapter- or week-level review synthesis instead of course-local artifact creation
