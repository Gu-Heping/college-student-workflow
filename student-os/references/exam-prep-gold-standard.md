---
type: student-os-reference
scope: exam-prep
status: active
---

# Exam Prep Gold Standard

This is the agent-facing standard for building exam prep material. It is distilled from mature vault material patterns, but it must not copy private vault content into generated public artifacts.

Use the [subject-neutral handout writing reference](../templates/exam-type-handout.md) and, when needed, [entry reference](../templates/exam-prep-entry.md). They are neither fixed forms nor ready-made course material. Adapt the teaching approach to the actual task: calculation, proof, argument, evidence interpretation and experimental design need not share a formula-driven lesson structure. When feedback changes the desired structure or depth, edit the actual teaching page and carry that choice through the remaining relevant pages. Do not substitute a new rule or feedback record for the requested revision.

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

Attendance, submitted homework and copied answers are separate from demonstrated understanding. Do not infer mastery from files or completion labels. When the user asks for material, finish the teaching work rather than tell them to practice before you will improve it. Practice advice belongs in the material as an optional next step, not as a substitute for missing explanations.

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

Start teaching from a real exam problem: what is given, what is requested, what to notice, and the first executable step. Explain the minimum concept when it becomes necessary. This is problem-led teaching, not forcing an unprepared student to solve before seeing an explanation. A foundations page is optional support, not a prerequisite detour through all missed lectures. Do not create a parallel lecture-note series for an exam-prep request without an explicit request for that output.

Condense the guide, formula card and priorities from the completed analyses, not the reverse. If only a sample is done, deliver it as a sample and say which content remains unwritten; folder scaffolds and reachable README stubs do not make a usable pack. Continue the authorized work in manageable batches without repeatedly requiring the user to approve each internal stage.

## Page Shapes

### Entry Page

The top of the entry page must identify the first useful type page and a coherent prerequisite-based reading sequence. When the user requests time-budget routes, it may also answer:

- I have 1 hour. What do I open first?
- I have 1 day. What order do I study in?
- I have 3 days. What is the route?
- Which P0/P1 type page should I read first?
- How do I use each type page: speed card, worked example, self-test, answer check?

Provide two paths where useful: a beginner follows necessary concepts, a concrete calculation, method choice, examples and self-tests; a revision reader jumps to the speed card. Put purpose and the first useful destination on the first screen, not a prerequisite demand to memorize compressed formulas. Use the same prerequisite-based order across pages. Preserve stable IDs by default; if the user explicitly requests renumbering/restructuring, coordinate an old-to-new mapping and update links after writers hand off. Do not confuse a learning sequence with an invented calendar or mandatory practice schedule.

Prefer one maintained explanation to several parallel copies. If the user requests self-contained type pages, integrate prerequisites and quick-reference content there; keep an entry for navigation and facts, and separate evidence archives only when useful. Merge carefully, preserve unique material and update links before removing redundant files. Do not generalize one course's preferred file count into every user's required layout.

Do not deliver an entry page that is only a file list, frequency table, or artifact inventory.

### Type Analysis Page

Each type page is a tutoring handout. It must contain:

The items below are responsibilities, not a mandatory eleven-section skeleton. Organize for the actual topic: recognition signal → necessary concept → operation and reason → minimal demonstration → past-paper problem → transfer. A shared foundations page is useful, but explain first-use essentials briefly and link it; avoid circular prerequisites and copied universal introductions.

A symbol or terminology table is a lookup aid, not a concept explanation. At the first use that matters, explain what the term represents, the relevant assumptions or conventions, why the reasoning holds and how to use it. Distinguish definitions, derived conclusions and rules with conditions. Do not turn a request for direct methods into a compliance rubric: give a useful starting point, the conditions selecting the method and the subsequent reasoning or operations, not instructions to pass arbitrary checkpoints. Known essentials belong on the page; source locations belong in the evidence record and may supplement readable source references, never replace the explanation with "see sidecar lines".

Test the first difficult operation by actually following the page without supplying your own background knowledge. A formula table saying "use partial fractions" does not teach how to find its coefficients; a heading saying "from zero" does not explain a shifted argument or an integral limit. Show the operation and why it applies, then connect it to a complete past-paper solution. If the student reports poor readability, rewrite that content in place before adding new navigation or prerequisites. Adopt a reference's teaching logic, not its exact nine/eleven sections or decorative markers.

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

### Method Clarity and Transfer Audit

A method name or list of steps is not a teachable method. Explain the recognition conditions, limits, starting action, executable reasoning, reasons for difficult transitions, how to answer every requested part, and an appropriate way to check the result. Compare competing methods where the choice matters. Use the reasoning form appropriate to the subject, not a mandatory formula-and-calculation format.

Teach transfer by comparing actual problems: identify what changed, why that changes the method or a particular step, and what remains reusable. Do not substitute "apply the same method" for this explanation.

The main agent must walk every question in the selected type's known source pool against the taught methods. If a problem requires an unexplained operation, assumption or reasoning branch, improve the explanation or revise the classification. A question-to-method table is an optional planning aid, not proof of coverage. Explicitly retain gaps for unreadable or unresolved questions; never imply completeness beyond the inspected pool.

Audit the two pools separately: worked examples teach the core methods and major variants; disjoint self-tests independently exercise those same capabilities. One problem may exercise multiple methods only when its actual solution does so. If a method lacks enough distinct authentic questions for both pools, disclose the gap instead of duplicating a problem or inventing one. These are AI content judgments, not semantic claims a checker can establish from tags.

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

Good grounding translates source knowledge into usable reasoning: explain what the concept means, which problem conditions make it relevant, how to act on it, and what limits the conclusion. Depending on the course, this may mean selecting a relation to calculate, constructing a proof, evaluating evidence, comparing interpretations or designing an experiment. Do not impose one discipline's operations on another.

If textbook evidence is missing, write `textbook_grounding: missing` or state in the page that the concept explanation is exam-experience grounded and needs a source.

Do not cite a broad chapter as proof. Prefer subsection, theorem, figure, problem diagram, example number, lecture slide, or homework source.

Grounding means reading authoritative material and then explaining it. Precise locations may live in the associated source map (`page_grounding` keyed by stable type ID), dossier (`textbook_refs`), or source appendix. A structured record has a readable vault-relative `path` and precise `locator`. A global textbook folder is not a page-specific record. Body citations remain compatible but are not compulsory. A link cannot replace the explanation or demonstration of an operation. Answer keys ground solutions, not definitions.

## Evidence Reconciliation

Give a current teacher announcement/correction priority over historical guesses about this exam. Preserve its exact force: "重点", "主要来自" and a complete exclusive scope are different claims. Track teacher-listed items, observed past-paper questions and optional extensions separately. An item count is not a score percentage; a few copied/recalled papers do not establish the entire question bank. Omit unsupported frequency, score and rubric claims rather than fill template fields. If the user stops investigating an uncertainty, park it with its evidence status unchanged; "not pursuing" does not prove the textbook wrong. New contrary evidence must still reopen the conclusion.

Integrating new sources is more than adding an example or a link. Read the relevant explanation, figure, counterexample or correction; decide which concept, applicability condition, method branch and solution must change. A coverage claim should point to the taught content, not just an index entry. If the user explicitly includes textbook/teacher exercises in the task, preserve those source roles instead of labelling them past papers; do not silently override a continuing past-paper-only constraint.

Inspect source contents before declaring a chapter, answer set or topic missing. Keyword counts are discovery hints, not a taxonomy or frequency verdict. Count independent exams/questions only after examining their roles and readable content; disclose unreadable cases and distinguish a known occurrence count from a full denominator. Zero detected hits does not establish that a topic is excluded from the current exam.

Keep three questions separate: what the source actually says, whether the derivation is sound under those givens, and whether the student's requested topic is covered. Agreement with a known answer does not prove an unreadable angle, sign or condition in the source; do not reconstruct a question backward from its answer.

When OCR conflicts with a derivation, first inspect the relevant original PDF page/crop or supplied image if accessible and the model can view it. Compare the textbook explanation, diagram, answer key and lecture source as needed. A second generated page copying the same OCR is not independent evidence. If visual inspection is unavailable, record that limitation and the conflicting readings locally; do not imply you saw the original. Request human help only for the unresolved, consequential detail, not for every item labelled unverified. AI source comparison stays unverified; it does not require a paper book when a readable original is already available.

When a source reading changes an input, time shift, sign, scale or symbol, inspect that original region yourself before adopting a consequential delegated correction if vision is available. Use a legible alternate copy and derivation as crosschecks, not proof that one blurry glyph must be a particular symbol. Record what the main agent inspected, what only a subagent inspected and what remains unresolved. Do not call AI image inspection "human-level verification" or claim all sources were read after sampling a few images. Resolve accessible uncertainties during writing rather than accumulate generic human-review warnings; keep `verify_status: unverified` even after AI source review.

For overlap/repeat analysis, distinguish identical questions, changed parameters, additional requirements, same-method variants and concept coverage. Name the observed denominator and known duplicate/uncertain sources. Do not promote a tiny historical sample to "the entire future question pool" or invent a current exam's score/format from old papers. A partial paper crop cannot establish the total question count; check the full layout before changing that fact.

After correcting a source fact, revisit its downstream uses: problem text, derivation, answer, type page, formula card, priority table and entry. Replace contradicted statements rather than leave an old statement beside a new correction. Reconcile counts and learning routes across those pages before delivery.

## Delegation And Integration

Subagents may write useful prose, but give them the same source and teaching constraints as the main agent. A compact contract names the exact output/write ownership, target reader, required problem/textbook/answer sources, reserved worked-example and self-test identities, human-readable citations and uncertainties. Do not quietly replace a past-paper-only self-test pool with textbook exercises; when the independent pool is insufficient, explain the gap or ask about a labelled supplementary exercise set.

Give actual source and output locations instead of guessed relative-link rules. Each writer resolves links relative to the file being written, including spaces/parentheses, and checks the destination. The coordinator owns shared entry pages while writers own disjoint drafts; coordinate handoff before either edits the other's file. Share corrected source facts and citations with the affected writers, not only in the final response.

Do not pre-patch a page another writer is still rewriting. Wait for its handoff and reread the saved version before editing. Tell writers to preserve source-backed givens and report conflicts, not to freeze every existing answer as an immutable fact: the old draft may contain the very mistake being repaired. Avoid blind global backslash normalization; a LaTeX row break followed by a letter can be valid. Inspect the affected formula and its file diff rather than replace every matching token.

Draft delivery includes sources actually read, specific doubts and changed paths, not just file size or heading count. Main-agent integration requires reading the draft's problem, full solution and self-test answer from disk, resolving reported conflicts where possible, and checking it against neighboring pages. A subagent's self-audit is useful evidence, not the main agent's reader audit.

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
- for a targeted replacement, select the complete paragraph, table row or math block, not a prefix ending mid-sentence; include enough unchanged context to disambiguate the edit. Read back that whole unit and its neighbors afterward. A successful literal match can still leave the old tail attached to new prose.

Use native literal edit/write tools for authored Markdown. If preparing a local edit through JavaScript, do not pass Markdown as a `String.replace` replacement string: `$$`, `$&` and `$1` have replacement semantics. A callback such as `text.replace(old, () => replacement)` returns literal replacement text; this is transport safety, not permission to batch-generate prose. Inspect the saved delimiters and formula, not only the string in your program.

Python non-raw strings can likewise turn `\theta`, `\vec` or `\rvert` into tabs, control characters or line breaks. Prefer native literal edits rather than another repair script. Read the complete changed table/formula and surrounding text after deleting a row: a leftover blank line can split a table even when the remaining rows individually look valid. Do not claim that every renderer rejects quoted tables or every command inside `\text{}`; for a demonstrated compatibility failure, use a plain table/display block and keep mathematical expressions outside prose labels.

A paginated/truncated read is not the complete file. Before a whole-file rewrite, obtain all pages through the actual end; otherwise edit only the fully observed local span. Check the final unchanged tail after writing. If content was lost, do not blindly restore from HEAD, which may omit newer user/other-agent edits; compare the task's pre-edit snapshot and current diff first and restore only the lost span with known provenance.

Example counts are secondary to method coverage, source quality and independent self-tests. Never keep a known duplicate as a differently named "minimal solution" to satisfy a minimum, or append weak problems merely to clear a report. Remove duplicates, repair the source allocation, and explicitly report genuine evidence gaps; do not claim completion while the selected problems fail to teach or test the methods.

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

Read the final entry table, one full guided solution and its independent test as a continuous learning route, not only file heads or grep matches. After a merge, reread the joins and repeated concepts: appending a slide-summary table is not teaching integration if the explanation the student needs is still absent. Check diagram dependencies and method conditions, not just algebra; a compressed catalogue of formulas cannot stand in for the first usable example. Record concrete corrections, not "links all reachable, therefore ready" or unsupported percentages of readiness.

Check that each mathematical witness is meaningful under the definitions: a distribution is not an ordinary number to evaluate at a point, and a quick rule is not a substitute for testing the actual system or method's conditions. Do not protect a wrong argument because its final verdict agrees with another page. Read back after the last correction, including the file tail; presence of numbered sections or preserved numeric tokens cannot prove completeness or consistency.

Formatting-only repairs still need a mathematical read-back: rederive ratios, signs, units and conditions rather than merely checking that a formula renders. For example, a frequency and its reciprocal period cannot use the same coefficient ratio. Check whether a mismatch comes from coordinate orientation, the chosen material point/reference frame, or a different physical event before declaring a source misprint.

Keep substantive mathematical checks, but adapt their presentation to the requested voice. If the reader rejects homework-style "自检/验算 ✓" badges, explain the useful consistency fact in ordinary prose and keep the AI's checking process in the audit. Do not delete the reasoning or reinsert compulsory labels just to satisfy a checker. Source-reading and AI audit remain distinct from human verification.

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
