# Exam Census Workflow

Use this reference for legacy/auxiliary large-scale past-paper censuses: question-type taxonomy, parallel annotation, and frequency aggregation.

This is not the default route for high-quality study packs, tutoring handouts, or requests such as "整理历年卷 / 构建期中期末备考包 / 高质量题型解析". For those, use AI-first exam prep (`commands/exam-prep-build.md`). Exam-census outputs can support that workflow as evidence or rough statistics, but they must not replace agent-written study material.

## Platform entry points

Orchestration adapters live under `integrations/` in the skill and must be **installed into the learning vault** (not into the skill directory):

```bash
python student-os/scripts/install_exam_census_adapters.py /path/to/vault \
  --platforms claude,cursor,opencode,github
```

| Platform | Vault path | Invoke |
| --- | --- | --- |
| Claude Code | `.claude/skills/exam-census/SKILL.md` + `.claude/commands/exam-census.md` | `/exam-census vault="…" course="…" examScope="…"` |
| Cursor | `.cursor/rules/exam-census.mdc` | Natural language exam-census request or `@exam-census` |
| OpenCode | `.opencode/exam-census.md` | Ask OpenCode to run exam-census with vault/course/scope |
| GitHub Copilot | `.github/copilot-exam-census.md` | Optional merge into `.github/copilot-instructions.md` |

### Claude Code 推荐运行方式

安装 adapter：

```bash
python student-os/scripts/install_exam_census_adapters.py /path/to/vault --platforms claude
```

然后在 Claude Code 中使用 slash command 或自然语言：

```text
/exam-census vault="/path/to/vault" course="linear-algebra" examScope="期中"
```

```text
请对 vault="/path/to/vault" 的线性代数期中真题做 exam-census 题型普查
```

Claude 端默认入口是 **skill/command runbook**（`.claude/skills/exam-census/SKILL.md`）：由模型直接按阶段跑 Python 脚本与填写产物。不要使用 Workflow 工具，也不要依赖 `.claude/workflows/*.js`（该文件仅实验性 opt-in，且自定义 workflow 发现不稳定）。若 vault 里仍留有旧版默认安装的 workflow JS，默认重装会将其备份为 `.bak` 并移除。

Adapters only orchestrate; all durable work still goes through the Python scripts below and `references/exam-census-quality.md`.

Without adapters, follow the Phases in this document (or `commands/exam-census.md`) and run the scripts manually / via the skill command.

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
├── skeleton-fingerprints.json
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

One-screen map (agents should announce artifact paths before each step):

| Step | What | Main script / owner |
| --- | --- | --- |
| Prepare | PDF → `.pdf.md` sidecar (+ repair) | `materials_convert.py` / file-operator |
| Init | Manifest + taxonomy stub | `init_exam_census.py` |
| Taxonomy | Draft type catalog from sample papers | review-coach |
| Annotate | Per-paper `annotations/*.json` | batched agents |
| Aggregate | Frequency report + type-analysis skeletons | `build_exam_type_stats.py --validate` |
| **A** Fill | Raise skeletons to full 题型解析 | `fill_type_analysis.py` + agents |
| **B** Quality | Structural gate, ≤2 revision rounds | `review_type_analysis.py` |
| **C** Multi-dim | Co-occurrence / difficulty drafts | `build_multi_dim_stats.py` |
| **D** Deep-dive | 1–2 representative paper walkthroughs | `init_exam_deep_dive.py` |
| **5** Legacy prep pack | L1–L4 compatibility pack（须在 Phase B 通过后；not the high-quality default） | templates + review-coach |
| **E** Cross-val | Coverage + prep-pack 四层完整性（prep pack 后再跑） | `cross_validate_exam_census.py` |

Current entry points: this file, `commands/exam-census.md`, and `references/exam-census-quality.md` (content standard). Prefer those over inventing a parallel checklist.

### Phase 0 — Prepare sidecars

1. Convert source PDFs with `materials_convert.py`.
2. Repair low-quality imports when needed.
3. If existing `.pdf.md` sidecars lack YAML frontmatter, run `ensure_frontmatter.py` (dry-run first, then `--apply`) before census init.
4. Keep sidecars out of `reviews/` until distillation.

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

If `--papers-dir` points at a scope root with no `.pdf.md` but a `文本/` / `text/` / `markdown/` / `md/` child has sidecars, init uses that child and reports it in JSON `papers_dir`.

Re-run with `--overwrite` only when intentionally replacing the manifest.

### Phase 1 — Taxonomy

1. Coordinator/review-coach selects 2–3 typical papers from the manifest.
2. Draft or expand `taxonomy.yaml`.
3. Optionally mirror the catalog with `templates/exam-type-taxonomy.md`.

### Phase 2 — Parallel annotation

1. Use `manifest.batches` (default batch size 6).
2. Assign one agent per batch; each agent only writes files named exactly as `paper.annotation` (usually `annotations/<stem>.json`, not `<stem>.pdf.md.json`).
3. Set `source` to the manifest `path` (include `文本/` when that is where the sidecar lives).
4. `confidence` must be one of: `high`, `medium`, `low`, `uncertain`, `needs-review`.
5. Skip existing annotation files unless the user requests overwrite.
6. Mark uncertain papers with `"confidence": "low"` / `"uncertain"` rather than inventing types.

### Phase 3 — Aggregate

```bash
python student-os/scripts/build_exam_type_stats.py /path/to/vault \
  --course linear-algebra \
  --exam-scope 期中 \
  --validate \
  --overwrite
```

Aggregate reads papers from the manifest (not a fresh directory scan). Optional `--papers-dir` is accepted only for comparison/warning and is otherwise ignored.

Produces:
- `题型频率统计.md`
- ranked skeletons under `题型解析/NN-<type-id>.md`
- machine-only `skeleton-fingerprints.json` under census state (not in page frontmatter)

题型解析 skeleton frontmatter 只保留短字段（含 `quality` / `source_summary`），**不**写入 `source_artifacts` 长路径数组或 `generated_fingerprint`。详细试卷列表放在频率统计或正文「来源依据」。

`--validate` exits nonzero when annotations are missing, reference unknown type ids, have unknown/unmatched `type_counts` keys, or have invalid `type_counts` values (non-object, non-positive integer). On validation failure the frequency report is still refreshed, but skeleton write/reconcile/retire is skipped.

### Phase 4 — Fill type analyses (Phase A)

1. Run `fill_type_analysis.py` to write `fill-queue.json` (ranked skeletons + `source_papers` / `source_instances` + `concept_sources` textbook candidates + required sections + fill instructions).
2. Assign one agent per type analysis (pipeline with Phase B preferred: fill → review immediately).
3. Before writing 核心概念, open `concept_sources` when present. Sources include course `references/` (excluding exam subdirs), vault `references/textbooks/`, and course-local lecture-material dirs: `教材课件/`, `课件/`, `教材/`, `slides/`, `lectures/`. Cite `参考：…` or write `基于考纲整理，未参考指定教材`.
4. Fill using `templates/exam-type-analysis.md` and `references/exam-census-quality.md` (**content standard v3** + zero-foundation entry).
5. Assign every annotated past-paper instance of the type to 例题精讲 or 自测题.
6. Defaults: **≥5 例题** + **≥4 自测**；每题标注 `来源：...`；例题标难度星；自测答案独立成章；禁止编造；禁止引用块内表格与 `<details>` 内 `$$`；考前速记含 ASCII `├` 决策树。

### Phase 4b — Quality gate (Phase B)

```bash
python student-os/scripts/review_type_analysis.py /path/to/vault \
  --course linear-algebra \
  --exam-scope 期中
```

Writes `quality-reviews.json` and `analysis/质量门禁.md`. Exit code 1 means at least one file needs revision (max 2 agent rounds, then `quality: needs-review`).

Phase B also flags Issue #51 / #63 / #65 output defects: bulky `source_artifacts` / `generated_fingerprint` in frontmatter, missing required short fields, broken Markdown tables from bare `|`, English residue in user-facing analysis reports (`Seeded from`, `Paper | Reliability`, `unspecified`), insufficient worked examples / self-tests (`≥5` / `≥4`), missing concrete 来源, render-unsafe Markdown (`> |` tables / `$$` inside `<details>`), weak teaching scaffolding, and v3 soft gaps（核心概念须教材引用或「未参考指定教材」 / 核心方法 / 快速得分技巧 / 易错对比表 / 难度星 / 自测答案分章 / 填空模板）.

`quality-reviews.json` separates `type_needs_revision`（题型解析）and `analysis_needs_revision`（`analysis/*.md`）。Run the gate again after Phase C so multi-dim drafts are covered.

Agents filling pages: 中文优先；像辅导老师讲义（为什么 / 选方法 / 易错对比 / 验算）；表格中行列式用 `$\lvert A\rvert$`；低频证据不足写「证据不足，需人工补充」并设 `quality: needs-review`。

### Phase 4c — Multi-dimensional analysis (Phase C)

```bash
python student-os/scripts/build_multi_dim_stats.py /path/to/vault \
  --course linear-algebra \
  --exam-scope 期中
```

Writes drafts under `reviews/<exam-scope-key>/analysis/` (co-occurrence, format roll-up, difficulty/reliability). User-facing Markdown is Chinese-first（表头「试卷 / 可靠性」等；枚举显示为「答案卷 / 复习版 / 回忆版 / 未标注」）。Agents refine difficulty stars and 选择/填空/计算 buckets.

After writing analysis drafts, re-run `review_type_analysis.py` and fix any `analysis_needs_revision` entries. After those revisions, run the gate once more and stop if analysis failures remain.

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

Writes `cross-validation.json` and `analysis/覆盖率检查.md` (missing skeletons, empty type lists, prep-guide link gaps, **Prep pack 四层结构**).

**Preferred:** run Phase E **after Phase 5**, so L1/L3/L4 files exist and `ok` can be true.

Optional early diagnostic after Aggregate/A–D is fine for skeleton coverage, but expect `ok: false` / nonzero exit until prep-pack files are created — do not treat that as a hard stop before Phase 5.

### Phase 5 — Legacy prep pack 四层资料包

This phase is a compatibility/auxiliary output for the exam-census pipeline. Do not use it as the default answer to "build a high-quality exam prep package". AI-first exam prep must own teaching prose, reader audit, source reading, and gold-page expansion.

**前置：** Phase B 题型解析质量门禁已通过（`review_type_analysis.py` 无 blocking `needs-revision`）。不要在门禁失败时硬写备考包。

四层契约：

| 层级 | 文件 | 用途 |
| --- | --- | --- |
| L1 | `备考指南.md` | 全局规划：考什么、优先级、时间分配、如何使用整套资料 |
| L2 | `题型解析/*.md` | 逐题型深入（content standard v3；本阶段只汇总链接，不重写正文） |
| L3 | `公式总卡.md` + `答题模板速查.md` | 速查：公式/适用场景/易错；2分钟下笔模板/填空骨架/抢分句式 |
| L4 | `考前1小时清单.md` | 最后 60 分钟冲刺（精确到分钟） |

先读取：
- `题型频率统计.md`
- `题型解析/*.md`
- `quality-reviews.json`
- `cross-validation.json`（若已有）

然后生成/更新（模板 → 产物）：
- L1 `备考指南.md` ← `templates/exam-prep-guide.md`
- L3 `公式总卡.md` ← `templates/formula-cheat-sheet.md`
- L3 `答题模板速查.md` ← `templates/answer-template-quickref.md`
- L4 `考前1小时清单.md` ← `templates/pre-exam-one-hour-checklist.md`

生成规则：
- 备考指南必须链接所有 P0/P1 题型解析，并链接 L3/L4。
- 公式总卡必须从题型解析公式表提取，不要编造公式；回链 `题型解析/`。
- 答题模板速查必须从「2分钟下笔模板 / 快速得分技巧」提取；含 `[条件]` / `[表达式]` / `[答案]` 等填空占位符。
- 考前1小时清单必须链接备考指南、公式总卡、答题模板速查和高频题型解析；含 60-45 / 45-30 / 30-15 / 15-5 / 5-0。
- 证据不足时写「证据不足，需人工补充」，不要强行补内容。
- **不要**为过门禁把自然语言硬塞进破表格；不做「90% 表格密度」硬计算，只要求关键章节与关键表存在。

Planning-assistant may help with day sequencing; review-coach owns content quality. **Re-run Phase E after the prep pack exists.**

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
