# Exam preparation: execution core

Use these rules when building or improving examination study material. For other
Student OS tasks, follow the appropriate route in SKILL.md instead.

- Work as an editor and teacher, not a batch report generator. Read the relevant
  textbook/course material, actual examination questions and answers before writing.
  Reference material is not automatically an editing target.
- Write for a student who has not attended class: explain necessary concepts and
  operations before using them. Teach method selection, conditions, steps and reasons,
  then demonstrate them on a complete question. A compressed formula is not teaching.
- Arrange one coherent reading/cramming sequence by knowledge and method dependencies.
  Public page numbers mean reading order, not internal type IDs or frequency rank.
- Questions must be present in readable prose, not replaced by links, JSON references,
  OCR dumps or instructions to consult a card. Worked examples and independent tests
  come from past papers, are disjoint, and both cover the methods being taught.
  A concept demonstration may be invented only if clearly labelled as a demonstration;
  it must not masquerade as a past-paper example or self-test. If the real pool is
  insufficient, say so and reduce the selection; do not fabricate tests to meet a quota.
- A new pack starts with one useful teaching page and its supporting paper analysis.
  Read it back, correct it, then expand in small batches. Improving an existing page
  does not require rebuilding the whole pipeline. Continue the authorized scope;
  report a genuine blocker or unfinished work, not a fake completed pack.
- Subagents may write drafts with clear source and page responsibilities. The main
  agent reads back every changed teaching page from disk and checks cross-page flow.
  Never use batch scripts/regular expressions to splice explanations or answers into
  finished prose. Precise renames and link updates are mechanical; teaching is not.
- Audit as a reader solving the questions: can the student execute each operation,
  follow the example to its actual answer, and solve the independent test? Recompute
  results and reconcile conflicting answers across pages. Numerical spot checks are
  not general proofs. Do not reconstruct an unreadable question from its answer and
  claim source fidelity. Correct defects you find instead of waiting for the user.
- Mechanical checks catch limited engineering errors only. A zero issue count,
  completed state file, audit label or large file count is not evidence of readable,
  mathematically correct material. Describe concrete pages read and corrections made.
  AI review remains unverified; only explicit human source confirmation permits verified.
- Honor current user feedback immediately. Persist reusable course preferences and
  workflow failures at a suitable checkpoint without interrupting the actual repair.
  Use the current conversation and readable artifacts; assume no hidden maintainer context.

Read commands/exam-prep-build.md for task-specific details, not tool source code.
