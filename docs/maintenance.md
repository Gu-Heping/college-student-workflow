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
python -m py_compile scripts/extract_release_notes.py scripts/install_student_os.py scripts/run_import_repair_evals.py scripts/run_smoke_tests.py student-os/scripts/update_student_os.py student-os/scripts/repair_import_queue.py student-os/scripts/repair_import_case.py student-os/scripts/repair_import_review.py student-os/scripts/repair_import_apply.py
python scripts/run_smoke_tests.py
python scripts/run_import_repair_evals.py
```

- 纯文档 PR：仍建议跑上述命令，确认未误改脚本；若环境无法跑，在 PR Notes 写明原因。
- 涉及公开发布/脱敏示例时，固定 tracker 仓库为 `Gu-Heping/college-student-workflow`，勿引导发到用户私有 vault 远程。

## 版本与 Changelog

- 用户可见行为变化写入 `CHANGELOG.md` 的 `[Unreleased]`。
- 文档整理可用一条 `Changed` / 文档向 bullet，不必重写历史。
- 版本号暂时按 `0.x.y` 维护：功能性大更新升 minor，bugfix 升 patch。

## 发布流程

发版采用 **tag 触发自动 Release**（不会在每次 push main 时发版）。Release notes 来自 `CHANGELOG.md` 对应版本段落，不要直接从 `[Unreleased]` 发 release。

1. 平时把变更写到 `CHANGELOG.md` 的 `[Unreleased]`。
2. 准备发版时，把 `[Unreleased]` 改成 `[x.y.z] - YYYY-MM-DD`，并在顶部新建空的 `[Unreleased]`。
3. 合并 release PR 到 `main`。
4. 在 `main` 上打 tag：`vX.Y.Z`。
5. 推送 tag 后，GitHub Actions（[`.github/workflows/release.yml`](../.github/workflows/release.yml)）自动跑验证并从 CHANGELOG 创建 GitHub Release。

```bash
git checkout main
git pull
git tag v0.7.0
git push origin v0.7.0
```

本地可先核对 notes：

```bash
python scripts/extract_release_notes.py --version 0.7.0 --output release-notes.md
```

Workflow 会拒绝：

- 指向未合入 `main` 的 commit 的 tag
- CHANGELOG 缺少对应版本段落
- smoke / 编译失败
- 已存在的同名 GitHub Release（不会静默覆盖）

验证步骤只使用 `contents: read`；创建 Release 才提升到 `contents: write`。

如果 workflow 失败，先修 CHANGELOG 或测试，再删除/重推 tag 或使用新 tag。

## Agent 维护时注意

- 不要把本仓库当 vault 跑 `scaffold_*` / `log_feedback` 等。
- 修改脚本后同步检查 README 命令示例是否仍正确（尤其 `materials_convert` 的 positional 语义）。
