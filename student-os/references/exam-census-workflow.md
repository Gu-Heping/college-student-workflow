# Exam Census Workflow

Use this reference for large-scale past-paper censuses: question-type taxonomy, parallel annotation, frequency aggregation, and exam-prep pack generation.

## Preconditions

- Papers already exist as markdown sidecars (usually `*.pdf.md`) under a course `references/` tree or another explicit papers directory.
- Prefer running `materials_convert.py` with `--repair` before annotation when OCR/import quality is uneven.
- Final readable artifacts land under `courses/<course>/reviews/<exam-scope>/`.
- Machine state lands under `.student-os/state/exam-census/<course-slug>/<exam-scope-slug>/`.

## Directory contract

```text
courses/<course>/reviews/<exam-scope>/
├── 题型频率统计.md
├── 题型解析/
│   ├── 01-<type-id>.md
│   └── ...
├── 备考指南.md
├── 公式总卡.md
├── 答题模板速查.md
└── 考前1小时清单.md

.student-os/state/exam-census/<course-slug>/<exam-scope-slug>/
├── taxonomy.yaml
├── manifest.json
└── annotations/
    └── <paper-stem>.json
```

`<exam-scope>` keeps the human label (for example `期中`). The state path slugifies that label.

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

`--validate` exits nonzero when annotations are missing or reference unknown type ids.

### Phase 4 — Fill type analyses

1. Work in frequency order (filename rank).
2. Prefer `templates/exam-type-analysis.md`.
3. Link back to source sidecars listed in frontmatter / census signal.

### Phase 5 — Exam prep pack

Create or update:
- `备考指南.md` ← `templates/exam-prep-guide.md`
- `公式总卡.md` ← `templates/formula-cheat-sheet.md`
- `答题模板速查.md` ← `templates/answer-template-quickref.md`
- `考前1小时清单.md` ← `templates/pre-exam-one-hour-checklist.md`

Planning-assistant may help with day sequencing; review-coach owns content quality.

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
