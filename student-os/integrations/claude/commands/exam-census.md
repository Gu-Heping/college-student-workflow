---
description: Run student-os exam-census (past-paper type census and exam-prep pack). Prefer this over Workflow tool custom JS.
argument-hint: "[vault=<path>] course=<course> examScope=<scope>"
---

# /exam-census

兼容入口：按已安装的 Claude skill `exam-census`（`.claude/skills/exam-census/SKILL.md`）以及 student-os 的 exam-census 流程执行。

**不要**调用：

```text
Workflow({name: "exam-census"})
Workflow({scriptPath: ".claude/workflows/exam-census.js"})
```

## 示例

```text
/exam-census vault="D:\vault-test" course="linear-algebra" examScope="期中"
```

```text
/exam-census 请对线性代数期中真题做题型普查，先检查 Git，输出所有产物路径
```

缺少 `course` / `examScope`（以及无法确定的 `vault`）时先询问，不要猜测。

安全边界与阶段顺序见 `.claude/skills/exam-census/SKILL.md`；权威细节在已安装 student-os 的 `references/exam-census-workflow.md`。
