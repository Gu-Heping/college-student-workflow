---
description: Run student-os exam-census (past-paper type census and exam-prep pack). Execute the vault skill runbook directly; do not use the Workflow tool.
argument-hint: "vault=<path> course=<course> examScope=<scope>"
---

# /exam-census

执行本 vault 内 `.claude/skills/exam-census/SKILL.md` 的完整 runbook。

你必须 **亲自按该 runbook 逐步跑脚本与填写产物**。不要使用 Workflow 工具，也不要去加载 `.claude/workflows/` 下的 JS。

## 示例

```text
/exam-census vault="D:\vault-test" course="linear-algebra" examScope="期中"
```

```text
/exam-census vault="D:\vault-test" 请对线性代数期中真题做题型普查，先检查 Git，输出所有产物路径
```

缺少 `vault` / `course` / `examScope` 时先询问，不要猜测，不要默认当前工作目录。

标注前先读 manifest 的 `papers` / `batches`：annotation 文件名用 `annotation` 字段（`annotations/<stem>.json`），`source` 用 `path` 字段。Init 可传 `--papers-dir`（支持自动发现 `文本/`）；Aggregate 不要传 `--papers-dir`。

自然语言提到题型普查 / exam-census 时，同样加载并执行同一份 skill runbook。

Phase A Fill 质量底线（content standard v3）：例题 ≥5、自测 ≥4、每题标注真题来源、例题标难度星、自测答案独立成章、ASCII 决策树、核心概念（定义+意义+对比，且有教材 `参考：…` 或「未参考指定教材」）/核心方法/快速得分/易错清单齐全；先读 fill-queue `concept_sources`；禁止编造；不要用引用块内表格，不要在 `<details>` 内写 `$$`。细节见 skill runbook「质量要求」与已安装 student-os 的 `references/exam-census-quality.md`。

Phase 5 Prep pack（Phase B 通过后）：按 L1 备考指南 / L2 题型解析（只链接不重写）/ L3 公式总卡+答题模板速查 / L4 考前1小时清单组装；从题型解析提取，禁止编造；完成后必须再跑 Phase E cross-validation。
