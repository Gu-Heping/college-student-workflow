---
type: student-os-reference
scope: exam-prep
status: active
---

# Exam Prep Gold Standard

This is the agent-facing standard for building exam prep material. It is distilled from mature vault material patterns, but it must not copy private vault content into generated public artifacts.

## Core Principle

Exam prep pages are written by the agent as a tutoring teacher, not assembled by scripts.

Scripts may initialize folders, list candidate sources, record state, and run mechanical tripwires. They must not generate lecture body text, worked solutions, self-test answers, or type explanations.

Subagents can write drafts when they receive a precise contract: target reader, output file, required sources, source citation format, no machine refs in正文, no template prose, and a self-read checklist. Drafts are not finished material until the main agent reads them from disk, audits them, and makes any needed local edits.

`issue_count: 0` means only that the tripwire did not catch obvious mechanical garbage. It is never a delivery standard.

## Target Reader

Assume the student:

- did not attend most lectures;
- did not finish the homework;
- has little time before the exam;
- needs to know what to click first, what to memorize, how to start a problem, and how to check an answer.

Write for this student. A page that is complete but unreadable is a failed page.

## Default Loop

For broad requests, do not generate a whole package at once. Complete one small loop first:

1. Inspect the vault and identify available papers, answers, textbook, lecture notes, homework, and existing high-quality references.
2. Consolidate canonical exams: one real exam gets one deep dive and paper-card; answer/review/combined sidecars are evidence roles, not extra papers.
3. Choose one high-value type or one representative paper.
4. Open the actual sources.
5. Write one useful page by hand in Markdown.
6. Read the page as a student.
7. Edit the page until it teaches.
8. Run mechanical tripwire checks.
9. Only then expand to the next page or batch.

## Page Shapes

### Entry Page

The top of the entry page must answer:

- I have 1 hour. What do I open first?
- I have 1 day. What order do I study in?
- I have 3 days. What is the route?
- Which P0/P1 type page should I read first?
- How do I use each type page: speed card, worked example, self-test, answer check?

Provide two paths: a beginner follows necessary concepts, a concrete calculation, method choice, examples and self-tests; a revision reader jumps to the speed card. Put purpose and both links on the first screen, not a prerequisite demand to memorize compressed formulas. Use the same prerequisite-based order in all entry/guide/speed pages; stable type IDs are not learning-order numbers.

Do not deliver an entry page that is only a file list, frequency table, or artifact inventory.

### Type Analysis Page

Each type page is a tutoring handout. It must contain:

The items below are responsibilities, not a mandatory eleven-section skeleton. Organize for the actual topic: recognition signal → necessary concept → operation and reason → minimal demonstration → past-paper problem → transfer. A shared foundations page is useful, but explain first-use essentials briefly and link it; avoid circular prerequisites and copied universal introductions.

- what this type tests in the exam;
- textbook or lecture concepts rewritten into exam actions;
- symbols and concepts used later on the page;
- 30-second recognition card;
- 2-minute first-writing template;
- method choice rules;
- common variants;
- full past-paper worked examples;
- complete worked solutions;
- non-overlapping past-paper self-tests;
- separate self-test answers;
- pitfalls, checks, and scoring strategy.

Do not use `paper-card` refs as a substitute for problem text. Machine refs such as `2024-final.json#一` belong in `.student-os/state/` and type-dossier JSON. Human-facing Markdown should use readable citations such as `2018-2019 第二学期 · 一.2`. The student must be able to do the problem from the page.

### Worked Example

Each worked example must include:

- source;
- complete usable problem statement;
- why this example belongs to this type;
- what to notice first;
- each key step and why it is valid;
- intermediate formulas or computations;
- final answer;
- check or verification;
- which method or variant it trains.

Use the rhythm:

```markdown
### Example N: short label

**Source**: ...

**Problem**: ...

**First look**: ...

**Solution**:
1. Action sentence.
   Formula or computation.
   Short reason.
2. Action sentence.
   Formula or computation.
   Short reason.

**Answer**: ...

> **Check**: ...

**Transfer**: ...
```

### Self-Test

Self-tests must come from past papers and must not repeat worked examples.

Before writing, allocate the available past-paper pool against core methods and variants for both teaching examples and independent tests. A different solution to the same question does not make it a different question. If examples consume the entire pool, move some to self-tests or reduce counts and record the coverage gap; never manufacture tests. Small concept demonstrations are permitted when labelled as demonstrations, not historical exam questions.

Each self-test needs:

- source;
- complete usable problem statement;
- method or variant trained;
- hint;
- answer in a separate answer section;
- concrete key steps or final result.

Never write answers like "check against the source", "use the same template", or "calculate by the paper-card".

## Textbook Grounding

The agent must read the textbook, lecture, or course notes before explaining concepts when those sources exist.

Good grounding translates theory into exam actions:

- "rank" becomes how to read rank from row-echelon form;
- "linear dependence" becomes how to build a matrix and solve homogeneous equations;
- "adjugate matrix" becomes when to use `AA^*=|A|E`;
- a circuit model becomes what node or equivalent circuit to write first;
- a physics law becomes which scene condition permits the formula.

If textbook evidence is missing, write `textbook_grounding: missing` or state in the page that the concept explanation is exam-experience grounded and needs a source.

Do not cite a broad chapter as proof. Prefer subsection, theorem, figure, problem diagram, example number, lecture slide, or homework source.

Grounding means reading authoritative material and then explaining it. Precise locations may live in the associated source map (`page_grounding` keyed by stable type ID), dossier (`textbook_refs`), or source appendix. A structured record has a readable vault-relative `path` and precise `locator`. A global textbook folder is not a page-specific record. Body citations remain compatible but are not compulsory. A link cannot replace the explanation or demonstration of an operation. Answer keys ground solutions, not definitions.

For Yuque or other export targets, keep the Obsidian source intact; convert only an export copy. Do not hunt for a KaTeX installation or rewrite every matrix to satisfy an unrelated renderer.

## Writing Style

Use short, teachable blocks:

- one paragraph, one idea;
- action first, explanation second;
- formulas serve a decision or computation;
- every first-use symbol is defined;
- no generic encouragement;
- no universal filler copied across pages;
- no "source link only" examples;
- no OCR dump pasted into a handout without editing.
- no batch regex or loop-based prose patching in teaching sections after a checker failure; open the page and edit the paragraph, example, answer, or `Transfer` block directly.
- no broken joins such as LaTeX commands glued to `**Answer**`, `**Check**`, or `**Transfer**`.

Worked solutions should use "action sentence + formula + short note":

1. what to judge;
2. what to write;
3. how to substitute;
4. how to check;
5. what to answer.

## Reader Audit

Use `exam-prep-reader-audit-examples.md` to calibrate the teaching judgment with synthetic counterexamples; it is not a template to paste into course prose.

Before reporting completion, the agent must personally read at least:

- the entry page;
- every subagent draft being claimed as finished;
- one type analysis page;
- one paper deep dive;
- one worked example;
- one self-test answer.

Also read **every changed teaching page**, including all subagent drafts, from disk after the last edit. Walk an actual solution as the student: are symbols defined, operations executable, applicability conditions clear, intermediate steps sufficient, and tests independently doable? Correct gaps and read the edits again. Distinguish a proof from an exact calculation and from a numerical spot check; the last cannot establish a general theorem. Recheck incomplete OCR against sources rather than inventing a question backwards from its answer.

Update the existing `reader-audit.md` for this round with reviewed paths, current page hashes or revision identifiers, specific findings, fixes and remaining risks. Preserve prior rounds as history; an old audit does not approve changed pages. These records support AI accountability, not automated proof of readability or human verification.

At phase closure, persist explicit reusable user corrections in the course quality standard. Group repeated workflow/tool defects into existing local feedback records while retaining the user's wording, affected outputs and changes made. Use only the active conversation and readable files; fix the task first, do not interrupt it for feedback collection, and do not publish without separate authorization/privacy review.

The final report must include a concrete reader audit:

```yaml
reader_audit:
  reviewed_files:
    - path: ...
      current_revision_or_hash: ...
      concrete_findings_and_fixes: ...
  sampled_files:
    - path: ...
      checked_for: ...
  blockers_found:
    - ...
  edits_made:
    - ...
  remaining_risks:
    - ...
  student_start_here: ...
  subagent_drafts_reviewed: true|false
  mechanical_tripwire_passed: true|false
  reader_audit_passed: true|false
  math_human_verified: false
```

If the audit finds a blocker, keep editing. Do not report completion.

Blockers include:

- no complete problem statement;
- worked solution does not respond to the actual problem;
- self-test has no concrete answer;
- textbook citation does not explain the concept;
- entry page does not tell the student where to start;
- repeated generic explanation appears under multiple examples;
- formulas do not render in Obsidian.

## Expansion Rule

After one page passes reader audit and tripwire checks, use it as the gold page for the next few pages. Do not bulk-generate dozens of pages from state files.

When expanding:

- open the gold page;
- open the new source questions;
- write the new page directly;
- self-audit against the gold page;
- run tripwire checks;
- record remaining risks honestly.
