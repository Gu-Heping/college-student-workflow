# Exam Census Workflow

Use this reference for large-scale past-paper censuses: question-type taxonomy, parallel annotation, frequency aggregation, and exam-prep pack generation.

## Preconditions

- Papers already exist as markdown sidecars (usually `*.pdf.md`) under a course `references/` tree or another explicit papers directory.
- Prefer running `materials_convert.py` with `--repair` before annotation when OCR/import quality is uneven.
- Final readable artifacts land under `courses/<course-key>/reviews/<exam-scope-key>/`.
- Machine state lands under `.student-os/state/exam-census/<course-key>/<exam-scope-key>/`.

## Directory contract

```text
courses/<course-key>/reviews/<exam-scope-key>/
├── 题型频率统计.md
├── 题型解析/
│   ├── 01-<type-id>.md
│   └── ...
├── analysis/
│   ├── 题型关联分析.md
│   ├── 分题型频率统计.md
│   ├── 题型难度分级.md
│   ├── 卷源可靠性分级.md
│   ├── 质量门禁.md
│   └── 覆盖率检查.md
├── 备考指南.md
├── 公式总卡.md
├── 答题模板速查.md
└── 考前1小时清单.md

.student-os/state/exam-census/<course-key>/<exam-scope-key>/
├── taxonomy.yaml
├── manifest.json
├── annotations/
│   └── <relative-paper-id>.json
├── fill-queue.json
├── quality-reviews.json
└── cross-validation.json
```

`<course-key>` is the course path under `courses/` (for example `linear-algebra` or `2026-fall/cs-101`), so semester-nested courses do not collide.
`<exam-scope-key>` is the slugified exam-scope label (for example `期中` or `midterm`). Raw labels must not contain path separators (`/`, `\\`, `:`).
State and reviews share the same `exam-scope-key`.
Annotation filenames are derived from each paper's path relative to `--papers-dir`, with `/` flattened to `__` (for example `2019/paper.pdf.md` → `annotations/2019__paper.json`).

## Data contracts

### `taxonomy.yaml`

```yaml
version: 1
course: 线性代数
exam_scope: 期中
types:
  - id: matrix-rank
    name: 矩阵的秩
    aliases: [秩, rank]
    keywords: [秩, 行阶梯, 极大无关组]
```

Rules:
- Treat existing `id` values as append-only after annotations exist.
- Prefer stable English-ish ids; keep display names in the course language.
- Optional human companion page: `templates/exam-type-taxonomy.md`.

### `annotations/<paper>.json`

```json
{
  "source": "courses/linear-algebra/references/exams/2019-期中-A.pdf.md",
  "exam_label": "2019 期中 A",
  "types_present": ["matrix-rank", "eigen-decomp"],
  "type_counts": {"matrix-rank": 2, "eigen-decomp": 1},
  "confidence": "high",
  "notes": "optional free-form notes"
}
```

Aggregation uses `types_present` for paper appearance counts and `type_counts` for question totals. Ranking prefers **paper appearance**, not raw question repeats.

## Phases

### Phase 0 — Prepare sidecars

1. Convert source PDFs with `materials_convert.py`.
2. Repair low-quality imports when needed.
3. Keep sidecars out of `reviews/` until distillation.

### Phase 0b — Initialize census state

```bash
python student-os/scripts/init_exam_census.py /path/to/vault \
  --course linear-algebra \
  --exam-scope 期中 \
  --papers-dir courses/linear-algebra/references/exams \
  --pattern "**/*.pdf.md"
```

Creates:
- `manifest.json` with paper list and annotation batches
- empty `annotations/`
- stub `taxonomy.yaml` if missing
- `reviews/<exam-scope>/题型解析/`

Re-run with `--overwrite` only when intentionally replacing the manifest.

### Phase 1 — Taxonomy

1. Coordinator/review-coach selects 2–3 typical papers from the manifest.
2. Draft or expand `taxonomy.yaml`.
3. Optionally mirror the catalog with `templates/exam-type-taxonomy.md`.

### Phase 2 — Parallel annotation

1. Use `manifest.batches` (default batch size 6).
2. Assign one agent per batch; each agent only writes its own `annotations/*.json` files.
3. Skip existing annotation files unless the user requests overwrite.
4. Mark uncertain papers with `"confidence": "low"` rather than inventing types.

### Phase 3 — Aggregate

```bash
python student-os/scripts/build_exam_type_stats.py /path/to/vault \
  --course linear-algebra \
  --exam-scope 期中 \
  --validate \
  --overwrite
```

Produces:
- `题型频率统计.md`
- ranked skeletons under `题型解析/NN-<type-id>.md`

`--validate` exits nonzero when annotations are missing, reference unknown type ids, have unknown/unmatched `type_counts` keys, or have invalid `type_counts` values (non-object, non-positive integer). On validation failure the frequency report is still refreshed, but skeleton write/reconcile/retire is skipped.

### Phase 4 — Fill type analyses (Phase A)

1. Run `fill_type_analysis.py` to write `fill-queue.json` (ranked skeletons + source papers + required sections).
2. Assign one agent per type analysis (pipeline with Phase B preferred: fill → review immediately).
3. Fill using `templates/exam-type-analysis.md` and `references/exam-census-quality.md` (content standard v2 + zero-foundation entry).
4. Assign every annotated past-paper instance of the type to 例题精讲 or 自测题.

### Phase 4b — Quality gate (Phase B)

```bash
python student-os/scripts/review_type_analysis.py /path/to/vault \
  --course linear-algebra \
  --exam-scope 期中
```

Writes `quality-reviews.json` and `analysis/质量门禁.md`. Exit code 1 means at least one file needs revision (max 2 agent rounds, then `quality: needs-review`).

### Phase 4c — Multi-dimensional analysis (Phase C)

```bash
python student-os/scripts/build_multi_dim_stats.py /path/to/vault \
  --course linear-algebra \
  --exam-scope 期中
```

Writes drafts under `reviews/<exam-scope-key>/analysis/` (co-occurrence, format roll-up, difficulty/reliability seeds). Agents refine difficulty stars and 选择/填空/计算 buckets.

### Phase 4d — Deep-dive papers (Phase D)

```bash
python student-os/scripts/init_exam_deep_dive.py /path/to/vault \
  --course linear-algebra \
  --exam-scope 期中 \
  --limit 2
```

Scaffolds 1–2 representative paper walkthroughs under `reviews/<exam-scope-key>/真题精析/` (links each annotated type back to `题型解析/`). Agents then fill prompts and solutions; template: `templates/exam-paper-deep-dive.md`.

### Phase 4e — Cross-validation (Phase E)

```bash
python student-os/scripts/cross_validate_exam_census.py /path/to/vault \
  --course linear-algebra \
  --exam-scope 期中
```

Writes `cross-validation.json` and `analysis/覆盖率检查.md` (missing skeletons, empty type lists, prep-guide link gaps).

### Phase 5 — Exam prep pack

Create or update:
- `备考指南.md` ← `templates/exam-prep-guide.md`
- `公式总卡.md` ← `templates/formula-cheat-sheet.md` (prefer extracting from type-analysis formula tables)
- `答题模板速查.md` ← `templates/answer-template-quickref.md` (prefer extracting from 2分钟下笔模板)
- `考前1小时清单.md` ← `templates/pre-exam-one-hour-checklist.md`

Planning-assistant may help with day sequencing; review-coach owns content quality. Re-run Phase E after the prep pack exists.

## Parallelism and failure handling

- Do not let two agents rewrite the same annotation file.
- A failed paper stays missing in validate output; continue other papers.
- Low OCR quality → repair sidecar or mark `confidence: low`.
- Never silently invent taxonomy ids during aggregation.

## Git guidance

Suggested split:
1. `.student-os/state/exam-census/**` (taxonomy, manifest, annotations)
2. `courses/**/reviews/<exam-scope>/**` (frequency report + prep pack)

`group_git_changes.py` maps exam-census state and exam-census review types into the `review` / `ops` groups as configured.

## Role routing

- `exam-census` command → primary `review-coach`
- coordinator batches Phase 2 and verifies Phase 3 coverage
- `file-operator` only for missing/broken imports
- escalate to coordinator when papers are missing, taxonomy is contested, or the user actually wants a single chapter review instead of a census
