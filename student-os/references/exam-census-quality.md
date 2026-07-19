# Exam Census Quality Standards

Use this reference for Phase A–E after Aggregate. Mechanical census scripts stay unchanged; agents fill and gate content here.

## Output quality (Issue #51 / #63 / #65)

题型解析面向**中文学生**阅读；**表格为主、段落为辅**。

- **frontmatter 只放短元数据**，统一字段：`type` / `course` / `exam_scope` / `exam_type_id` / `exam_type_name` / `rank` / `paper_count` / `must_know` / `quality` / `status`（可选 `source_summary`）。
- **不要**写入长 `source_artifacts` 路径数组或机器用的 `generated_fingerprint`；详细来源放在 `题型频率统计.md` 或正文「来源依据」。
- 表格单元格里的行列式/绝对值**不要裸写** `|A|`：优先 `$\lvert A\rvert$`，或确保 `|` 已转义为 `\|`（生成脚本统一走 `md_table_cell`）。
- **不要**使用引用块内表格（`> | ... |`）；**不要**在 `<details>` 内使用 `$$` 块级公式（推荐不用 `<details>`）。
- 低频题型证据不足时：写「证据不足，需人工补充」，并设 `quality: needs-review`；不要保留空模板段落。
- Phase B（`review_type_analysis.py`）拦截臃肿 frontmatter、英文残留、坏表格、缺真题来源、不兼容 Markdown/LaTeX、教学支架缺失，以及 v3 结构软检（核心概念/核心方法/抢分/易错表/难度星/自测答案分章）。

## Content standard v3 — required section order

1. 元信息（频率/分值/难度/来源；普通文本，禁止引用块表格）
2. 真卷对应题号
3. **考前速记（30秒掌握）**：ASCII 决策树（`├─`）+ 一眼先记住 + 关键公式表 + 口诀
4. **核心概念**：定义 + 易混对比表
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

# E — coverage / skeleton / prep-guide link traceability
python student-os/scripts/cross_validate_exam_census.py /path/to/vault --course linear-algebra --exam-scope 期中
```

## Reviewer JSON shape (Phase B)

`review_type_analysis.py` writes `.student-os/state/exam-census/.../quality-reviews.json`。Structural checks require non-placeholder body text. Agents may revise a `needs-revision` file at most twice; then set `quality: needs-review` in frontmatter.

v3 soft checks include：`concept_explanation` / `core_methods` / `scoring_strategy` / `error_comparison` / `difficulty_stars` / `self_test_answer_separation` / `fill_in_answer_template`。
