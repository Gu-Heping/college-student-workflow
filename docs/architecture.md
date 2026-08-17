# 架构与文档分层

## 文档分层

| 层 | 文件 | 读者 | 职责 |
| --- | --- | --- | --- |
| 人类入口 | [`README.md`](../README.md) | 普通学生 | 这是什么、怎么装、一句话发给 agent、安全提醒 |
| 开发 agent 入口 | [`AGENTS.md`](../AGENTS.md) | 云端/仓库内 agent | 安全边界、gotchas、意图路由速查 |
| Skill 总路由 | [`student-os/SKILL.md`](../student-os/SKILL.md) | 已安装 skill 的 agent | 请求类型、角色、脚本、输出合同 |
| 自然语言命令 | [`student-os/commands/`](../student-os/commands/) | agent | 短入口：何时用、默认角色 |
| Workflow 细节 | [`student-os/references/`](../student-os/references/) | agent | 分阶段步骤、目录约定、质量标准 |
| 可执行工具 | [`student-os/scripts/`](../student-os/scripts/) | agent / 开发者 | CLI |
| 产物模板 | [`student-os/templates/`](../student-os/templates/) | agent | 新建 markdown 骨架 |
| 演示与 fixture | [`examples/`](../examples/) | 测试 / 演示 | smoke 与示例 vault |
| 回归入口 | [`scripts/run_smoke_tests.py`](../scripts/run_smoke_tests.py) | 开发者 / CI | 自包含 smoke |
| 维护记录 | [`docs/`](./) | 维护者 | 状态、架构、维护规则、路线图 |

## 代码与配置分层

```text
college-student-workflow/          # skill 源码仓库（不是用户 vault）
├── README.md / AGENTS.md / CHANGELOG.md
├── docs/                          # 维护记录
├── scripts/                       # 安装器、smoke、兼容包装
├── integrations/                  # runtime-native adapters outside the portable skill core
├── install.sh / install.ps1
├── examples/                      # demo vaults + fixtures
└── student-os/                    # 可安装的 skill 包
    ├── SKILL.md
    ├── commands/
    ├── references/
    ├── companions/
    ├── integrations/              # exam-census 多平台适配模板
    ├── scripts/
    └── templates/
```

用户机器上通常还有：

- **已安装 skill 目录**（如 agent 的 skills 路径）+ `.student-os-install.json`
- **学习 vault**（用户自己的笔记库，独立路径）

安装/更新只同步 skill 目录 ↔ 本仓库；vault 只在用户明确要求学术/导入等任务时被脚本以参数形式操作。

## 数据流示例

### 资料导入

```text
PDF/DOCX/PPTX/XLSX/图片
  → materials_convert.py（source 路径，非 vault）
  → markdown sidecar（旁路或 --output-root）
  → 可选 repair_markdown_import / --repair
  → 挂回 course / references / review / planning workflow
```

### 历年试卷 exam-census

```text
试卷 PDF
  → materials_convert（+ repair）→ *.pdf.md sidecar
  → init_exam_census（manifest + taxonomy stub）
  → 标注 annotations/*.json
  → build_exam_type_stats（频率 + 题型解析骨架）
  → Phase A fill → B quality → C multi-dim → D deep-dive
  → 备考包（指南/公式/模板/清单）
  → Phase E cross_validate
```

简明 Phase 说明见 `student-os/references/exam-census-workflow.md` 与 `commands/exam-census.md`。

### 用户反馈 → GitHub

```text
用户抱怨
  → log_feedback（feedback/raw）
  → triage / summarize
  → prepare_github_issue（隐私检查）
  → 用户确认
  → publish_github_issue 或 sanitize_and_post + gh
  → 回写 github_issue_* 元数据
```

任意非 feedback 正文：

```text
draft 文本 → prepare_github_issue --stdin/--check-only
  → sanitize_and_post → gh issue/pr/comment
```

### Skill 安装与自更新

```text
install_student_os / install.sh|ps1
  → 写入 skill 目录 + .student-os-install.json
  → update_student_os --check / --apply
  → 备份（copy 安装）+ rollback 指引
  → 全程不修改学习 vault
```

## Agent 路由原则

1. 先判断意图 → `SKILL.md` 请求类型 / `commands/*`
2. 读对应 `references/*`（不要只凭脚本名猜测阶段）
3. 改文件前 `inspect_repo`；公开前隐私检查；更新 skill 时隔离 vault
4. 结束后给变更摘要与 commit 建议，默认不自动提交
