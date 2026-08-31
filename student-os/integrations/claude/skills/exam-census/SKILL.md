---
name: exam-census
description: Run the legacy/auxiliary student-os exam-census pipeline for explicit exam-census, 题型普查, 题型频率, or frequency-statistics requests. Do not use as the default route for high-quality study packs or tutoring handouts; use AI-first exam prep for 整理历年卷 / 构建备考包.
argument-hint: "vault=<path> course=<course> examScope=<scope> [papersDir=<path>]"
---

# Exam Census Runbook

你是 **exam-census 编排者**。收到 `/exam-census` 或自然语言题型普查 / 题型频率请求时，**由你直接按本 runbook 执行**（Bash / 读文件 / 写文件 / 委派子任务均可）。

本 runbook 是 legacy/auxiliary 机器普查路径。用户要“整理历年卷 / 构建备考包 / 写高质量题型解析 / 做能直接学习的复习资料”时，不要走本路径；改用 Student OS 的 AI-first exam prep 入口。

**禁止**使用 Workflow 工具来跑 exam-census。不要查找或执行 `.claude/workflows/exam-census.js`。本文件就是唯一执行说明。

## 何时触发

- 用户运行 `/exam-census ...`
- 用户说：题型普查、试卷普查、题型频率、exam-census 等

不要因“备考资料包 / 整理历年卷 / 高质量题型解析”触发本 skill；这些属于 AI-first exam prep。

## 参数（全部必填 unless 标注）

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `vault` | 是 | 学习 vault 绝对路径（git root）。**禁止**把 `college-student-workflow` skill 源码仓或当前 agent checkout 当 vault |
| `course` | 是 | 课程 slug 或 `courses/` 下路径 |
| `examScope` | 是 | 如 `期中` / `midterm` |
| `semester` | 否 | 学期 slug |
| `papersDir` | 否 | 试卷目录（相对 vault）；**仅**传给 `init_exam_census.py --papers-dir`，后续阶段不要传 |
| `skillScripts` | 否 | `student-os/scripts` 绝对路径提示 |

缺少 `vault` / `course` / `examScope` 时：**先询问，不要猜测，不要默认 cwd**。

解析参数后先复述：`vault`、`course`、`examScope`、本阶段计划产物路径。

## 脚本目录

设 `SCRIPTS` 为包含 `init_exam_census.py` 的目录，按序查找：

1. 用户传入的 `skillScripts`
2. `~/.claude/skills/student-os/scripts/`
3. `~/.codex/skills/student-os/scripts/`
4. `~/.config/opencode/skills/student-os/scripts/`
5. 附近 checkout 的 `student-os/scripts/`

下文用 `python "$SCRIPTS/<name>.py"`；Windows 上把路径换成实际绝对路径即可。

先拼好公共参数（**不要**把 `--papers-dir` 加进公共参数——只有 Init 支持它）：

```bash
BASE=("$vault" --course "$course" --exam-scope "$examScope")
# 若有 semester：
BASE+=(--semester "$semester")
```

后续阶段一律：`python "$SCRIPTS/<script>.py" "${BASE[@]}" ...`

## 安全边界

- 只写用户学习 vault；不写 skill 源码仓笔记。
- 每个写入阶段前检查 Git（`inspect_repo.py` 或 `git status`）。
- **不自动 commit**。
- **不删除**原始试卷 PDF / 源文件。
- **不覆盖**已有 `annotations/` 或 `taxonomy.yaml`，除非用户明确允许。
- 导入/补 frontmatter 的路径必须先解析为 **vault 内绝对路径**；拒绝 vault 外路径，禁止用 cwd / skill 源码仓当写入目标。
- 每阶段开始前告知产物路径；阶段失败则停止并报告，勿跳过 validate。

## 产物目录

```text
courses/<course-key>/reviews/<exam-scope-key>/
  题型频率统计.md
  题型解析/
  analysis/
  真题精析/          # Phase D
  备考指南.md
  公式总卡.md
  答题模板速查.md
  考前1小时清单.md

.student-os/state/exam-census/<course-key>/<exam-scope-key>/
  taxonomy.yaml
  manifest.json
  annotations/
  fill-queue.json
  quality-reviews.json
  ...
```

## Runbook（严格按序）

### 0. Prepare

1. 在 `vault` 检查 Git。
2. 若缺 `.pdf.md` sidecar 或质量差：先把试卷路径解析为 vault 内绝对路径（相对路径相对 `vault` 展开），确认落在 vault 内后再运行：

```bash
# papers_abs 必须是 vault 下的绝对路径
python "$SCRIPTS/materials_convert.py" "$papers_abs" --repair --method local
```

（或用户指定的 method；有 MinerU token 时可用 auto/api。）

### 1. Frontmatter

若 sidecar 缺 YAML frontmatter：同样先解析为 vault 内绝对路径，再：

```bash
python "$SCRIPTS/ensure_frontmatter.py" "$sidecar_abs" --dry-run
# 用户确认后：
python "$SCRIPTS/ensure_frontmatter.py" "$sidecar_abs" --apply
```

### 2. Init

`init` 的 `--papers-dir` 可以指向 scope 根目录（如 `reviews/期中/`）。若该目录本身没有匹配 `--pattern` 的 `.pdf.md`，但存在 `文本/` / `text/` / `markdown/` / `md/` 子目录且其中有 sidecar，会自动使用该子目录，并在 JSON 的 `papers_dir` / `papers_dir_fallback_subdir` / `papers_pattern` 中写明。若 `--pattern` 本身已是根相对路径（如 `文本/*.pdf.md`），则保持原根目录与 pattern，不切换子目录。

```bash
python "$SCRIPTS/init_exam_census.py" "${BASE[@]}"
# 仅当用户提供了 papersDir 时追加（只有本脚本支持）：
#   --papers-dir "$papersDir"
```

确认出现 `manifest.json` 与 `taxonomy.yaml` stub。**后续阶段不要再传 `--papers-dir`**（aggregate 若收到该参数只会与 manifest 对比并 warning，不会重新扫描）。

### 3. Taxonomy

1. 定位 state 下的 `taxonomy.yaml`。
2. 若文件**已存在**且含非空 `types`：先报告路径与摘要，**暂停并询问**用户是否允许修订；未确认前不改。
3. 若仅是 init 生成的空 stub / 不存在：可起草。
4. 阅读 2–3 份代表卷 sidecar 后编写；已有 `id` 在 annotations 存在后只增不改语义；显示名中文优先。

### 4. Annotate

**先读** `manifest.json` 的 `papers` / `batches`，不要凭文件名猜路径。

对每个 paper：

- 标注文件必须写成 manifest 的 `annotation` 字段，通常是 `annotations/<stem>.json`（**不要**写成 `<stem>.pdf.md.json`）。
- JSON 内 `source` 必须等于 manifest 的 `path`（含 `文本/` 等子目录）。
- `confidence` 只能是：`high` | `medium` | `low` | `uncertain` | `needs-review`。

按 `manifest.batches` 分批；**一批一个 agent**，只写该批文件：

```json
{
  "source": "courses/.../reviews/期中/文本/paper.pdf.md",
  "exam_label": "2019 期中 A",
  "types_present": ["matrix-rank"],
  "type_counts": {"matrix-rank": 2},
  "confidence": "high",
  "notes": ""
}
```

已有 annotation 文件默认跳过。不确定时用 `"confidence": "low"` 或 `"uncertain"`，勿发明 taxonomy id。

### 5. Aggregate

Aggregate **只读 manifest** 中的试卷列表与 `papers_dir`，不重新扫描目录：

```bash
python "$SCRIPTS/build_exam_type_stats.py" "${BASE[@]}" --validate --overwrite
# 不要传 --papers-dir；若误传，JSON 会给出 papers_dir_warning 并忽略
```

非零退出 → **停止**。成功则得到 `题型频率统计.md` 与 `题型解析/` 骨架。链接一律使用 manifest `path`；若 annotation `source` 不一致会出现 source mismatch 诊断。

### 6. Phase A — Fill

```bash
python "$SCRIPTS/fill_type_analysis.py" "${BASE[@]}"
```

按 `fill-queue.json` 填写每页 `题型解析/`（可并行，一页一 agent）。写「核心概念」前先打开队列中的 `concept_sources`（若有）；来源包括课程 `references/`（排除试卷子目录）、vault `references/textbooks/` 以及课程本地 `教材课件/`、`课件/`、`教材/`、`slides/`、`lectures/`。无教材则写「基于考纲整理，未参考指定教材」。质量标准见下方「质量要求」。

### 7. Phase B — Quality gate

```bash
python "$SCRIPTS/review_type_analysis.py" "${BASE[@]}"
```

只处理 `type_needs_revision`；修订 ≤2 轮，否则 `quality: needs-review`。**不要**在 fill worker 内跑此脚本。

### 8. Phase C — Multi-dim

```bash
python "$SCRIPTS/build_multi_dim_stats.py" "${BASE[@]}" --overwrite
```

再跑 `review_type_analysis.py "${BASE[@]}"` 处理 `analysis_needs_revision`；修订后**再跑一次**确认清空。仍失败则停止，勿进入 D。

### 9. Phase D — Deep-dive

```bash
python "$SCRIPTS/init_exam_deep_dive.py" "${BASE[@]}" --limit 2
```

填写 `真题精析/` 骨架。

### 10. Phase 5 — Prep pack 四层资料包

**前置：** Phase B 质量门禁已通过。本阶段**不要**重写 `题型解析/` 正文；只汇总与分层。

先读取：`题型频率统计.md`、`题型解析/*.md`、`quality-reviews.json`、已有 `cross-validation.json`。

在 `reviews/<exam-scope-key>/` 写 / 更新：

| 层级 | 文件 | 模板 |
| --- | --- | --- |
| L1 | `备考指南.md` | `templates/exam-prep-guide.md` |
| L2 | `题型解析/*.md` | 已由 Phase A/B 完成（仅链接） |
| L3 | `公式总卡.md` / `答题模板速查.md` | `formula-cheat-sheet.md` / `answer-template-quickref.md` |
| L4 | `考前1小时清单.md` | `pre-exam-one-hour-checklist.md` |

生成规则：
- 备考指南必须链接所有 P0/P1 题型解析，并链接公式总卡、答题模板速查、考前1小时清单。
- 公式总卡从题型解析公式表提取，不要编造；回链 `题型解析/`。
- 答题模板速查从「2分钟下笔模板 / 快速得分技巧」提取；含 `[条件]` / `[表达式]` / `[答案]`。
- 考前1小时清单链接 L1/L3 与高频题型解析；含 60-45 / 45-30 / 30-15 / 15-5 / 5-0。
- 证据不足写「证据不足，需人工补充」；不做 90% 表格密度硬门禁。

### 11. Phase E — Cross-val

Prep pack 生成后**再跑一次**：

```bash
python "$SCRIPTS/cross_validate_exam_census.py" "${BASE[@]}"
```

检查覆盖率 + 四层文件 / frontmatter / 层级链接 / 最低内容结构。

## 质量要求

- 面向用户文档 **中文优先**；表格为主、段落为辅；输出像辅导老师讲义（讲为什么、怎么选方法、怎么避免错、怎么验算）。
- frontmatter 只放短元数据；**不要** `source_artifacts` 长数组或 `generated_fingerprint`。
- 题型解析按 **content standard v3**：考前速记（含 ASCII `├` 决策树）/ 核心概念（定义+意义+对比；`参考：教材…` 或「基于考纲整理，未参考指定教材」）/ 核心方法 / 例题 / 自测 / **自测答案独立章** / 快速得分技巧 / 易错点与检查清单。
- `fill-queue.json` 的 `concept_sources` 列出课程 `references/`（排除试卷子目录）、vault `references/textbooks/` 以及课程本地 `教材课件/`、`课件/`、`教材/`、`slides/`、`lectures/` 中的教材 sidecar；先读再写核心概念。教材例题仅可补充，真题例题/自测仍禁止编造。
- 例题精讲 **≥5**、自测题 **≥4**；每道题必须标注 `来源：...`；例题标注难度星级；禁止编造题目。
- 禁止引用块内表格（`> | ... |`）；禁止 `<details>` 内 `$$` 块级公式。
- 答题骨架优先填空式：`[表达式]` / `[值]` / `[答案]`。
- 表格行列式/绝对值勿裸写 `|A|`；用 `$\lvert A\rvert$`。
- 勿残留英文 seed 注释、`Paper | Reliability`、`unspecified` 等用户向英文。
- 低频证据不足：写「证据不足，需人工补充」，并设 `quality: needs-review`。

## 并行规则

- Annotate：一批一 agent；禁止双写同一 annotation。
- Fill：一页一 agent；质量门禁全局串行。
- Aggregate / validate 失败时不发明 type id。

## 完成后

列出：写入路径、质量门禁结论、建议 Git 分组与 commit message。**不要**自动提交。

若已安装完整 student-os skill，可对照其 `references/exam-census-workflow.md` 与 `references/exam-census-quality.md` 补细节；**仍以本 runbook 的阶段顺序与禁令为准**。
