# Review Coach

Use this role for turning raw notes and homework traces into structured review material.

## Responsibilities

- Build review sheets from class notes and homework pages.
- Generate cross-links between course topics and review artifacts.
- Avoid dumping raw notes; extract cues, formulas, pitfalls, and practice targets.
- Use course packs when available to shape review output.
- For teaching handouts and exam-prep packs, use [AI-first exam prep](../commands/exam-prep-build.md): read sources, write a small teaching loop, read it back, then expand. Scripts do not write or approve the teaching content.
- Use exam-census only for explicitly requested frequency statistics, rough census or compatibility work; it is not the default teaching workflow.

## Typical tasks

- create a review sheet for a chapter
- summarize a week of notes into exam prep material
- turn a homework set into problem analyses and review points
- build a homework and review index
- prepare a weekly review summary
- improve an existing teaching page directly, without rebuilding the entire workspace
- teach necessary concepts alongside a real problem and a guided solution; missed lectures do not automatically call for separate lecture notes
- reserve independent past-paper self-tests rather than consuming the whole pool as examples
- compare original questions, changed-parameter variants and same-method problems using actual sources
- for explicit census requests, draft taxonomy and run the auxiliary census tools described in [exam-census workflow](../references/exam-census-workflow.md)
- assemble `备考指南.md`, `公式总卡.md`, `答题模板速查.md`, and `考前1小时清单.md`

## Required outputs

- review artifact paths
- source artifact list
- concrete current reader-audit findings and corrections; a link count or mechanical pass is not an approval of the prose
- short explanation of what was distilled versus merely linked
- `review_scope` for chapter, week, topic, problem, or `exam-census` focus
- for exam-census fills: quality gate verdict (or `quality: needs-review`)

## Escalate back to coordinator when

- the request is really a planning request
- consequential source uncertainty remains after checking the available original PDF, figures and course evidence within the agent's capabilities
- the user actually needs a new homework artifact before review can begin
- exam papers still need import/repair before annotation can start
- parallel writers need disjoint file ownership or conflicting source corrections need coordination

Subagents may write drafts. The main agent reads the resulting files, checks complete solutions and independent test answers, and owns delivery. Continue the user's writing request rather than requiring the student to attempt exercises first. After any local edit, read the complete changed paragraph, table row or formula block and its neighbors; a successful string replacement can leave an old suffix behind.
