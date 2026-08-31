# Exam Census Quality Standards

Use this reference for Phase A–E after Aggregate. Mechanical census scripts stay unchanged; agents fill and gate content here.

This is the legacy/auxiliary exam-census quality contract. It can improve census-derived compatibility pages, but it is not the default standard for AI-first high-quality study material. For tutoring handouts and real exam-prep packages, use `commands/exam-prep-build.md` and `references/exam-prep-gold-standard.md`.

## Output quality (Issue #51 / #63 / #65)

题型解析面向**中文学生**阅读；**表格为主、段落为辅**。

- **frontmatter 只放短元数据**，统一字段：`type` / `course` / `exam_scope` / `exam_type_id` / `exam_type_name` / `rank` / `paper_count` / `must_know` / `quality` / `status`（可选 `source_summary`）。
- **不要**写入长 `source_artifacts` 路径数组或机器用的 `generated_fingerprint`；详细来源放在 `题型频率统计.md` 或正文「来源依据」。
- 表格单元格里的行列式/绝对值**不要裸写** `|A|`：优先 `$\lvert A\rvert$`，或确保 `|` 已转义为 `\|`（生成脚本统一走 `md_table_cell`）。
- **不要**使用引用块内表格（`> | ... |`）；**不要**在 `<details>` 内使用 `$$` 块级公式（推荐不用 `<details>`）。
- 低频题型证据不足时：写「证据不足，需人工补充」，并设 `quality: needs-review`；不要保留空模板段落。
- Phase B（`review_type_analysis.py`）拦截臃肿 frontmatter、英文残留、坏表格、缺真题来源、不兼容 Markdown/LaTeX、教学支架缺失，以及 v3 结构软检（核心概念须有教材引用或「未参考指定教材」声明 / 核心方法 / 抢分 / 易错表 / 难度星 / 自测答案分章）。

## Concept sources（Issue #69）

`fill_type_analysis.py` 在写入 `fill-queue.json` 前从以下位置收集教材/课件 sidecar（仅 `.pdf.md`）：

- `courses/<course>/references/`（排除 `exams/`、`试卷/`、`真题/`、`文本/` 等试卷子目录）
- `<vault>/references/textbooks/`（文件名必须提及本课程，避免跨课程泄漏）
- `courses/<course>/教材课件/`、`课件/`、`教材/`、`slides/`、`lectures/`

以上目录中的期中/期末/试卷/答案子目录与 repair artifact（`.raw.md`）会被过滤。无候选时，`concept_sources` 为空，核心概念应写「基于考纲整理，未参考指定教材」。

## Content standard v3 — required section order

1. 元信息（频率/分值/难度/来源；普通文本，禁止引用块表格）
2. 真卷对应题号
3. **考前速记（30秒掌握）**：ASCII 决策树（`├─`）+ 一眼先记住 + 关键公式表 + 口诀
4. **核心概念**：正式定义 + 几何/代数（或学科等价）意义 + 易混对比表；优先参考 fill-queue `concept_sources` 教材 sidecar，并写 `参考：…`；无教材时写「基于考纲整理，未参考指定教材」
5. **核心方法**：方法卡（适用场景→步骤→技巧）+ 选择速查 + 填空式答题模板（`[表达式]` / `[答案]`）
6. 零基础先看这里（入口四问 + 最低掌握线）
7. 例题精讲（≥5，来源 + 方法引用 + **难度星级**；禁止编造）
8. 自测题（≥4，仅题目与提示；禁止编造）
9. **自测答案**（独立章节，先试后看）
10. **快速得分技巧**（按时间充裕/紧张/几乎不够/完全不会分档）
11. **易错点与检查清单**（表：易错点 | 错误做法 | 正确做法 | 原因 + checklist）
12. 来源校对说明

## Worked examples & self-tests (Issue #63 / #65)

- 默认 **≥5 道例题** + **≥4 道自测题**。
- 每道题必须标注 `来源：YYYY-YYYY 第X学期 第X题`（或 `来源：<试卷名>，题号待人工校对`）。
- 例题标题或正文标注难度 `⭐…`；至少 3 道带实质星级。
- 题目必须来自 manifest / annotations 命中该题型的 `source_papers`；**禁止自行编造**。
- 真题实例不足 9 个时：尽量覆盖全部实例；不足处写「证据不足，需人工补充」，并设 `quality: needs-review`。
- 自测题区不写答案；答案统一放在 `## 自测答案`。
- 输出要像辅导老师讲义：讲为什么、怎么选方法、怎么避免错、怎么验算、不会做时先写什么拿步骤分。

## Zero-foundation entry (must answer)

| Question | Block |
| --- | --- |
| 这题到底考什么？ | 这类题考试到底在考什么 |
| 看到什么特征先按什么想？ | 30秒认题 |
| 第一笔写什么？ | 2分钟下笔模板 |
| 不会做时怎样拿步骤分？ | 不会做时先写什么拿步骤分 |

Principles: conclusions/templates before deep theory; expand numeric substitution; first sentence of solutions states order; key observations only explain *why* or *common error*.

## Writing style

- Prefer short 2–4 column tables over long prose（不强制 90% 表格密度硬门禁）。
- Method choice must use an ASCII decision tree with `├─` / `└─`.
- Fill-in answer skeletons use bracket placeholders：`[表达式]`、`[值]`、`[答案]`.

## Prep pack 四层结构（Phase 5 / Issue #65）

在 Phase B 通过后组装；从频率统计与题型解析**提取**，禁止编造。

| 层级 | 文件 | 职责 |
| --- | --- | --- |
| L1 | `备考指南.md`（`type: exam-prep-guide`） | 怎么用资料包、题型优先级、时间分配 |
| L2 | `题型解析/*.md`（v3，由 Fill/Quality 完成） | 概念/方法/例题/自测/抢分/易错 |
| L3 | `公式总卡.md` + `答题模板速查.md` | 公式与答题模板速查，回链题型解析 |
| L4 | `考前1小时清单.md` | 最后 60 分钟分段冲刺 |

Cross-validation（Phase E）在 prep pack 生成后应再跑：检查四文件存在、frontmatter `type`、层级链接、关键章节（不做全文件表格比例硬门禁）。缺文件或关键结构缺失 → `ok: false`，并写入 `prep_pack.missing_files` / `layer_link_issues` / `content_issues`。

## Phase scripts

```bash
# A — enqueue fill work for agents
python student-os/scripts/fill_type_analysis.py /path/to/vault --course linear-algebra --exam-scope 期中

# B — structural quality gate (exit 1 if any file needs-revision)
python student-os/scripts/review_type_analysis.py /path/to/vault --course linear-algebra --exam-scope 期中

# C — multi-dim analysis drafts under reviews/<scope>/analysis/
python student-os/scripts/build_multi_dim_stats.py /path/to/vault --course linear-algebra --exam-scope 期中 --overwrite

# D — scaffold 1–2 representative paper deep-dives
python student-os/scripts/init_exam_deep_dive.py /path/to/vault --course linear-algebra --exam-scope 期中 --limit 2

# E — coverage / skeleton / prep-pack 四层完整性（Phase 5 后再跑一次）
python student-os/scripts/cross_validate_exam_census.py /path/to/vault --course linear-algebra --exam-scope 期中
```

## Reviewer JSON shape (Phase B)

`review_type_analysis.py` writes `.student-os/state/exam-census/.../quality-reviews.json`。Structural checks require non-placeholder body text. Agents may revise a `needs-revision` file at most twice; then set `quality: needs-review` in frontmatter.

v3 soft checks include：`concept_explanation` / `core_methods` / `scoring_strategy` / `error_comparison` / `difficulty_stars` / `self_test_answer_separation` / `fill_in_answer_template`。
