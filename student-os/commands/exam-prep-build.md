# exam-prep-build

Intent: build high-quality exam review material from messy past papers.

Use when the user asks to:
- 整理历年试卷为期中/期末复习资料
- 构建考试备考包、真题精析、题型解析、公式卡、答题模板
- turn uneven `.pdf.md` sidecars into teaching-oriented review material

Default route:
- primary role: `review-coach`
- scripts manage workspace/state/mechanical checks only
- AI owns paper reading, question understanding, type clustering, method writing, and prep strategy

Do **not** start with mechanical statistics or keyword parsing. For messy papers, the default order is:

```text
阶段 0：资料盘点 → quality-standard.md → source-map.json
阶段 1：一份试卷精析样板 + 一份题型解析样板 → gold-sample check
第一轮：逐卷精析 v0 → 题目卡
第二轮：跨卷聚类/复现分析 → 回填精析 v1
备课轮：type-dossiers 题型备课卡 → 题型解析讲义页
收束轮：分析报告 → 四层备考包 → 机械验收
```

## Start

Initialize the AI-first workspace:

```bash
python student-os/scripts/exam_prep_build.py /path/to/vault \
  --course <course-key> \
  --exam-scope <期中|期末> \
  --papers-dir <papers-dir> \
  --json
```

This creates task/state files under `.student-os/state/exam-prep/...` and readable artifacts under `courses/<course>/reviews/<scope>/`.

## Stage 0 And Gold Sample

Before bulk generation, read the course sources and create a concrete local standard:

- `quality-standard.md`: target reader, source priority, page style, examples/self-tests rules, textbook grounding rules, and sample gate.
- `.student-os/state/exam-prep/<course>/<scope>/source-map.json`: papers, textbook/lecture/homework sources, answer sources, and known high-quality references.
- `.student-os/state/exam-prep/<course>/<scope>/gold-sample-task.json`: the first representative sample task.

Then write exactly one representative `试卷精析` sample and one representative `题型解析` sample. The default student has not attended lectures or done homework, so the sample must teach concepts before using them, include full past-paper problem text, and show full reasoning.

Check the sample before expanding:

```bash
python student-os/scripts/exam_prep_check.py /path/to/vault \
  --course <course-key> \
  --exam-scope <期中|期末> \
  --stage gold-sample \
  --json
```

If this fails, revise the sample. Do not generate dozens of files to hide a weak sample.

## Round 1: Paper v0

For each paper:

1. Read the `.pdf.md` sidecar and nearby answer/source evidence.
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
5. Worked examples and self-tests must all come from past-paper `paper-card.json#question_id` refs. They must be disjoint. Do not use 自编题、模拟题、改编题, or invented examples.

Check dossiers:

```bash
python student-os/scripts/exam_prep_check.py /path/to/vault \
  --course <course-key> \
  --exam-scope <期中|期末> \
  --stage type-dossier \
  --json
```

Then write `题型解析/*.md` as tutoring handout pages from the dossier:

- Open the dossier and the referenced past-paper questions first.
- Start with cross-paper value: frequency, score band, difficulty, repeat/variant status, representative years, and review priority.
- Include 30 秒速记、符号和概念表、课本知识点与精确依据、2 分钟下笔模板、方法选择、核心概念、核心方法、例题精讲、自测题、自测答案、抢分技巧、易错点.
- Put the actual past-paper problem text in the page. Source links alone are not enough.
- Explain textbook grounding precisely enough to study from it: prefer textbook/lecture subsection, figure number, problem diagram, or chapter anchor. Do not use answer keys as concept authority.
- Use "action sentence + formula + short note": what to judge first, what to write next, how to substitute, how to check, and what to answer.
- Default target: at least 5 worked examples and 4 self-tests. If past-paper evidence is insufficient, write `quality: needs-review` and explain `证据不足，需人工补充`.
- Every example/self-test must cite a machine-readable past-paper ref such as `2024-final.json#一`; example refs and self-test refs must not overlap.
- Choose examples and self-tests to cover the method cards and common variants in the dossier, not just to fill a count. This coverage judgment is AI work: each worked example should name the method/variant it teaches, explain what to notice first, and include a transfer cue; each self-test should state which method/variant it trains. The checker only verifies source refs, de-duplication, required sections, and whether training targets are labeled.

## Check

Final check:

```bash
python student-os/scripts/exam_prep_check.py /path/to/vault \
  --course <course-key> \
  --exam-scope <期中|期末> \
  --stage final \
  --json --write-report
```

Passing means the package meets mechanical evidence/structure/render checks. It does **not** prove all math is semantically correct.

## Hard Rules

- Do not deliver only `题型频率统计.md`.
- Do not treat `issue_count: 0` as proof of teaching quality; it is only mechanical acceptance.
- Do not bulk-generate the whole pack before a gold sample passes.
- Do not invent examples or self-tests; all examples and self-tests must come from past papers.
- Do not cite only paper-card refs without including usable problem text.
- Do not reuse the same past-paper question as both a worked example and a self-test.
- Do not write a type-analysis page before the matching type dossier exists.
- Do not use vague textbook grounding such as only "§2"; cite the usable section, figure, problem diagram, or lecture location when available.
- Do not mark AI output as human verified.
- Do not let scripts decide complex semantics.
- If source format is chaotic, spend effort on `试卷精析` and `paper-cards` first.
