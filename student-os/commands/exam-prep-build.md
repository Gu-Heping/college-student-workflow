# exam-prep-build

Intent: build high-quality exam review material from messy past papers.

Use when the user asks to:
- 整理历年试卷为期中/期末复习资料
- 构建考试备考包、真题精析、题型解析、公式卡、答题模板
- turn uneven `.pdf.md` sidecars into teaching-oriented review material

Default route:
- primary role: `review-coach`
- work mode: editing teacher, not batch executor
- scripts initialize workspace/state and run tripwire checks only
- AI personally reads sources, writes Markdown body text, judges readability, revises, and reports reader audit
- subagents may draft正文 only from explicit task contracts; main agent must read back,审稿, and locally edit those drafts before delivery

Do **not** start with mechanical statistics, keyword parsing, or full-package generation. For messy papers, the default order is:

```text
阶段 0：读取 gold standard → 资料盘点 → quality-standard.md → source-map.json
阶段 1：AI 亲自写一份试卷精析样板 + 一份题型解析 gold page → tripwire check → reader audit
第一轮：逐卷精析 v0 → 题目卡
第二轮：跨卷聚类/复现分析 → 回填精析 v1
备课轮：type-dossiers 题型备课卡 → 题型解析讲义页
收束轮：分析报告 → 四层备考包 → tripwire check → reader audit
```

Before any content work, read `references/exam-prep-gold-standard.md`. Treat it as the writing standard.
Also read `references/agent-runtime-context.md` when using feedback, examples, or prior conversation as evidence. Do not assume access to hidden maintainer context, exported logs, or private sample vaults unless the user provides readable files.

The core rule is simple: every explanation, worked solution, self-test answer, guide route, and type page paragraph must be written by the agent after reading source material. Do not use scripts, loops, state JSON, paper-cards, or dossiers to assemble body prose.

Before paper writing, use the manifest's canonical exam grouping. One real exam gets one `试卷精析` and one paper-card; paper sidecars, answer sidecars, combined paper+answer files, review versions, PDFs, and text-layer repairs are evidence roles for that canonical exam, not separate exams.

## Start

Initialize the AI-first workspace:

```bash
python student-os/scripts/exam_prep_build.py /path/to/vault \
  --course <course-key> \
  --exam-scope <期中|期末> \
  --papers-dir <papers-dir> \
  --json
```

This creates task/state files under `.student-os/state/exam-prep/...` and starter artifact locations under `courses/<course>/reviews/<scope>/`. These files are scaffolding and evidence/state holders, not finished study material.

## Stage 0 And Gold Sample

Before bulk generation, read the course sources and create a concrete local standard:

- `quality-standard.md`: target reader, source priority, page style, examples/self-tests rules, textbook grounding rules, and sample gate.
- `.student-os/state/exam-prep/<course>/<scope>/source-map.json`: papers, textbook/lecture/homework sources, answer sources, and known high-quality references.
- `.student-os/state/exam-prep/<course>/<scope>/gold-sample-task.json`: the first representative sample task.

Then write exactly one representative `试卷精析` sample and one representative `题型解析` gold page. The default student has not attended lectures or done homework, so the sample must teach concepts before using them, include full past-paper problem text, and show full reasoning. The agent must open the actual paper, answer evidence, and textbook/lecture source before writing.

Check the sample before expanding:

```bash
python student-os/scripts/exam_prep_check.py /path/to/vault \
  --course <course-key> \
  --exam-scope <期中|期末> \
  --stage gold-sample \
  --json
```

If this fails, revise the sample. If it passes, perform reader audit before expanding. Do not generate dozens of files to hide a weak sample.

Reader audit for the gold sample must answer:

- Can a student tell what to open first?
- Is the worked example a complete, usable problem?
- Does the solution respond to that exact problem?
- Is the textbook concept explained as an exam action?
- Is the self-test answer concrete enough to check?
- What did the agent edit after noticing weak spots?

## Round 1: Paper v0

For each paper:

1. Read the canonical problem source and its source roles in the manifest: original paper first, combined paper+answer second, answer/review text only as checking evidence.
2. Write `试卷精析/<paper>.md` as a v0 teaching walkthrough, not a raw transcript.
3. Write the matching `paper-cards/<paper>.json` with `question_id`, `prompt_summary`, `solution_summary`, `initial_type`, `evidence_refs`, `confidence`, `repeat_status`, and notes.
4. Use `low` / `needs-review` when source evidence is unclear.
5. In v0, set repeat status to `unknown-pending-cross-paper-analysis` or `needs-review`; do not assert 原题复现 yet.

Check v0:

```bash
python student-os/scripts/exam_prep_check.py /path/to/vault \
  --course <course-key> \
  --exam-scope <期中|期末> \
  --stage paper-v0 \
  --json
```

## Round 2: Synthesis And Backfill

After paper-v0 passes:

1. Cluster question types in `taxonomy.json`.
2. Write cross-paper analysis, especially `分析/01-题型频率统计.md`, `分析/02-跨年原题重复记录.md`, and `分析/05-近年趋势与教考分离.md`.
3. Backfill each `试卷精析/<paper>.md` with a cross-paper relationship section: type links, original-repeat/close-variant/same-type status, related years/questions, and review priority.

Check synthesis:

```bash
python student-os/scripts/exam_prep_check.py /path/to/vault \
  --course <course-key> \
  --exam-scope <期中|期末> \
  --stage synthesis \
  --json
```

## Type Dossier Before Type Analysis

Do not write `题型解析/*.md` from a blank template. For each taxonomy type:

1. Read the matching paper-card question refs, cross-paper analysis, and v1 `试卷精析`.
2. Create `.student-os/state/exam-prep/<course>/<scope>/type-dossiers/<type-id>.json`.
3. Create `reviews/<scope>/题型备课卡/<type-id>.md`.
4. The dossier must include recognition cues, variants, method cards, formula cards, pitfalls, source question refs, worked example candidates, self-test candidates, confidence, and insufficient-evidence notes.
5. Worked examples and self-tests must all come from past-paper question refs in the dossier. Those machine refs stay in state/dossier JSON; human-facing Markdown cites the same source as readable text such as `2018-2019 第二学期 · 一.2`. They must be disjoint. Do not use 自编题、模拟题、改编题, or invented examples.

Check dossiers:

```bash
python student-os/scripts/exam_prep_check.py /path/to/vault \
  --course <course-key> \
  --exam-scope <期中|期末> \
  --stage type-dossier \
  --json
```

Then write `题型解析/*.md` as tutoring handout pages from the dossier. The dossier is preparation, not page prose:

- Open the dossier and the referenced past-paper questions first.
- Open the relevant textbook/lecture material before explaining concepts.
- Start with cross-paper value: frequency, score band, difficulty, repeat/variant status, representative years, and review priority.
- Include 30 秒速记、符号和概念表、课本知识点与精确依据、2 分钟下笔模板、方法选择、核心概念、核心方法、例题精讲、自测题、自测答案、抢分技巧、易错点.
- Put the actual past-paper problem text in the page. Source links alone are not enough.
- Explain textbook grounding precisely enough to study from it: prefer textbook/lecture subsection, figure number, problem diagram, or chapter anchor. Do not use answer keys as concept authority.
- Use "action sentence + formula + short note": what to judge first, what to write next, how to substitute, how to check, and what to answer.
- Default target: at least 5 worked examples and 4 self-tests. If past-paper evidence is insufficient, write `quality: needs-review` and explain `证据不足，需人工补充`.
- Every example/self-test must cite a readable past-paper source such as `2024-2025 第二学期 · 一.2`; example sources and self-test sources must not overlap. Keep `.json#` refs out of human-facing Markdown.
- Choose examples and self-tests to cover the method cards and common variants in the dossier, not just to fill a count. This coverage judgment is AI work: each worked example should name the method/variant it teaches, explain what to notice first, and include a transfer cue; each self-test should state which method/variant it trains. The checker only verifies source refs, de-duplication, required sections, and whether training targets are labeled.
- Do not copy a universal worked-solution paragraph across examples. Each solution must name the exact givens, the exact first relation, the exact computation, and the exact check for that problem.

## Check

Final check:

```bash
python student-os/scripts/exam_prep_check.py /path/to/vault \
  --course <course-key> \
  --exam-scope <期中|期末> \
  --stage final \
  --json --write-report
```

Passing means the package passed tripwire evidence/structure/render checks. It does **not** prove readability, teaching quality, or mathematical correctness. Before reporting completion, run reader audit from `references/exam-prep-gold-standard.md` and include the audit in your final message.

## Hard Rules

- Do not deliver only `题型频率统计.md`.
- Do not treat `issue_count: 0` as proof of teaching quality; it is only mechanical acceptance.
- Do not report a broad exam-prep request as complete without a concrete reader audit.
- Do not use batch scripts or loops to generate lecture body text, example explanations, self-test answers, or guide prose.
- Do not use batch regex scripts to patch teaching prose after tripwire failures; open the page, read the context, and edit the local paragraph/solution/answer yourself.
- Do not bulk-generate the whole pack before a gold sample passes.
- Do not invent examples or self-tests; all examples and self-tests must come from past papers.
- Do not cite only paper-card refs without including usable problem text.
- Do not reuse the same past-paper question as both a worked example and a self-test.
- Do not write a type-analysis page before the matching type dossier exists.
- Do not use vague textbook grounding such as only "§2"; cite the usable section, figure, problem diagram, or lecture location when available.
- Do not mark AI output as human verified.
- Do not let scripts decide complex semantics.
- Do not let subagent drafts enter the final pack without main-agent reader audit and local edits where needed.
- If source format is chaotic, spend effort on `试卷精析` and `paper-cards` first.
- If a generated page feels unreadable, fix the prose and examples directly; do not hide behind a passing tripwire report.
