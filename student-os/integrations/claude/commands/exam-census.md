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

自然语言提到题型普查 / exam-census 时，同样加载并执行同一份 skill runbook。
