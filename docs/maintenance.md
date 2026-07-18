# 维护规则

## 文档改动：何时直提、何时开 PR

| 改动类型 | 建议 |
| --- | --- |
| 错别字、坏链接、明显过时一句 | 可小 PR 快速合；仍建议走 PR，勿直接推 main |
| README 结构、安装/使用示例、安全提醒 | **必须开 PR** |
| AGENTS.md / SKILL.md / commands / references 路由与安全边界 | **必须开 PR** |
| 涉及安装、更新、隐私、安全、脚本命令示例的文档 | **必须开 PR** |
| 新增或调整 docs/status、roadmap、maintenance | 开 PR；与能力变更同一 PR 更佳 |

本仓库默认：**不要直接推 main**。

## 新增 workflow 的同步清单

新增或显著扩展一个 workflow 时，同一变更集应同时更新：

1. [`README.md`](../README.md)（人类能感知到的能力与示例，若适用）
2. [`student-os/SKILL.md`](../student-os/SKILL.md) 路由
3. `student-os/commands/` 与/或 `student-os/references/`
4. [`CHANGELOG.md`](../CHANGELOG.md)
5. [`scripts/run_smoke_tests.py`](../scripts/run_smoke_tests.py) 或相关 fixtures（若有可测行为）
6. [`docs/status.md`](./status.md)（能力状态）

可选：`docs/architecture.md` 数据流、`docs/roadmap.md` 勾掉已完成项。

## 公开仓库禁止提交

- 真实学习 vault 内容
- 课本原文、简历、个人资料
- token、`.env`、密钥
- 不必要的大文件 / 二进制资料包

示例与 fixture 只保留脱敏、小型演示数据。

## PR 要求

- PR body **必须写测试结果**（勾选或说明跳过原因）。
- 合并前至少本地跑：

```bash
python -m py_compile scripts/install_student_os.py scripts/run_smoke_tests.py student-os/scripts/update_student_os.py
python scripts/run_smoke_tests.py
```

- 纯文档 PR：仍建议跑上述命令，确认未误改脚本；若环境无法跑，在 PR Notes 写明原因。
- 涉及公开发布/脱敏示例时，固定 tracker 仓库为 `Gu-Heping/college-student-workflow`，勿引导发到用户私有 vault 远程。

## 版本与 Changelog

- 用户可见行为变化写入 `CHANGELOG.md` 的 `[Unreleased]`。
- 文档整理可用一条 `Changed` / 文档向 bullet，不必重写历史。

## Agent 维护时注意

- 不要把本仓库当 vault 跑 `scaffold_*` / `log_feedback` 等。
- 修改脚本后同步检查 README 命令示例是否仍正确（尤其 `materials_convert` 的 positional 语义）。
