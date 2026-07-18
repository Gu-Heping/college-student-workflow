---
name: exam-census
description: Run student-os exam-census for past-paper type analysis and exam-prep pack generation. Use when the user asks to analyze past papers, classify exam question types, build type-frequency reports, or generate exam prep materials.
argument-hint: "vault=<path> course=<course> examScope=<scope> [papersDir=<path>]"
disable-model-invocation: true
---

# Exam Census

用 Claude Code 的 **skill / command** 入口跑 student-os 的 exam-census（题型普查 → 频率统计 → 题型解析 → 备考包）。

**不要**调用 `Workflow({name: "exam-census"})` 或 `Workflow({scriptPath: ".claude/workflows/exam-census.js"})`。Claude Code 对自定义 `.claude/workflows/*.js` 的发现与加载不稳定；本 skill 是推荐入口。

## 用法

```text
/exam-census vault="/path/to/vault" course="linear-algebra" examScope="期中"
```

或自然语言（仍须显式给出 vault）：

```text
/exam-census vault="/path/to/vault" 请对线性代数期中真题做题型普查，先检查 Git，输出所有产物路径
```

## 参数

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `vault` | 是 | 学习 vault 的绝对路径（git root）；不要把 skill 源码仓库或当前 checkout 当 vault |
| `course` | 是 | 课程 slug 或 `courses/` 下路径 |
| `examScope` | 是 | 如 `期中` / `midterm` |
| `semester` | 否 | 学期 slug |
| `papersDir` | 否 | 试卷目录（相对 vault）；默认走脚本在课程 `references/` 下的约定 |
| `skillScripts` | 否 | `student-os/scripts` 的绝对路径提示 |

缺少 `vault` / `course` / `examScope` 时：**先询问用户，不要猜测，不要默认当前工作目录**。

## 安全边界

- **target vault 必须是用户学习 vault**，不是 `college-student-workflow` skill 源码仓库。
- 每次写入阶段前先检查 Git（`inspect_repo.py` / 等价检查）。
- **不自动 commit**。
- **不删除**原始试卷 PDF / 源文件。
- **不覆盖**已有 `annotations/` 或 `taxonomy.yaml`，除非用户明确允许。
- 每一阶段开始前，先告知用户本阶段产物路径。

## 脚本位置

优先：

- `~/.claude/skills/student-os/scripts/`
- `~/.codex/skills/student-os/scripts/`
- `~/.config/opencode/skills/student-os/scripts/`
- 用户传入的 `skillScripts`

否则在附近 checkout 中查找包含 `init_exam_census.py` 与 `build_exam_type_stats.py` 的 `student-os/scripts/`。

## 执行流程（按序，勿跳过 validate）

1. **Prepare** — 检查 Git；确认 vault。必要时 `materials_convert.py --repair` 把 PDF 转成 `.pdf.md` sidecar。
2. **Frontmatter** — 若 sidecar 缺 YAML：先 `ensure_frontmatter.py --dry-run`，用户确认后再 `--apply`。
3. **Init** — `init_exam_census.py`
4. **Taxonomy** — 建立 / 修订 `taxonomy.yaml`（id 只增不改语义）
5. **Annotate** — 按 `manifest.batches` 生成 `annotations/*.json`（一批一个 agent；勿双写同一文件）
6. **Aggregate** — `build_exam_type_stats.py --validate --overwrite`（非零退出则停止）
7. **Phase A** — `fill_type_analysis.py`，再按 `exam-census-quality.md` 填写 `题型解析/`
8. **Phase B** — `review_type_analysis.py`（全局一次；修订 ≤2 轮或标 `quality: needs-review`）
9. **Phase C** — `build_multi_dim_stats.py --overwrite`，再跑质量门禁处理 `analysis_needs_revision`；修订后**再跑一次** `review_type_analysis.py` 确认清空，若仍失败则停止，勿进入 Phase D
10. **Phase D** — `init_exam_deep_dive.py`（代表卷精读骨架）
11. **Prep pack** — 备考指南 / 公式总卡 / 答题模板 / 考前清单（含到 `题型解析/` 的真实链接）
12. **Phase E** — `cross_validate_exam_census.py`

细节与目录契约见已安装 student-os 的：

- `commands/exam-census.md`
- `references/exam-census-workflow.md`
- `references/exam-census-quality.md`

## 质量要求

- 面向用户的文档 **中文优先**。
- frontmatter 只放短元数据；**不要**写入臃肿 `source_artifacts` 长路径数组或 `generated_fingerprint`。
- 表格中的行列式/绝对值不要写裸 `|A|`（会拆表）；用 `$\lvert A\rvert$` 或转义。
- analysis / 题型解析不要残留英文 seed 注释、`Paper | Reliability`、`unspecified` 等用户向英文。
- 低频证据不足：写「证据不足，需人工补充」，并设 `quality: needs-review`。

## 完成后

列出：写入/更新的路径、质量门禁结论、建议的 Git 分组与 commit message；**不要**自动提交。
