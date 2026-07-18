# College Student Workflow

## 这是什么

`college-student-workflow` 是一个给大学生学习资料库用的 agent workflow 仓库。  
它的核心是 [`student-os`](./student-os/)——一套装给 `Codex`、`Claude Code`、`OpenCode`、`Cursor` 等 agent 用的 **skill**（可理解为：告诉 AI 怎么在你的笔记库里安全干活的说明书 + 脚本）。

你可以把学习资料放在 Obsidian vault、普通 Markdown 文件夹，或任何以文本笔记为主的目录里。`student-os` 的核心价值是：

- 让 agent **动文件前先检查**目录和 Git 状态
- 用 **Git 留痕**，改动能看、能回滚、能分组提交
- 降低 **误改 / 误删 / 乱提交** 的风险

它不是“替你自动学完一门课”的黑盒，而是让 AI 在你的学习文件夹里工作时更可控、更可追踪。

## 适合谁

- 用 Obsidian、Markdown、文件夹管理课程资料的人
- 想让 AI 帮忙建课程、整理作业/复习，又怕改乱文件的人
- 希望学习资料能用 Git 看改动、分提交、必要时回滚的人
- 想把「安装 → 日常使用 → 反馈问题 → GitHub Issue → 更新 skill」串成闭环的人

如果你只是随手记几条临时笔记、完全不想碰文件夹结构，这个仓库可能会偏重。

## 它能帮你做什么

当前已经能覆盖的日常能力：

- 检查或初始化一个学习 vault（笔记库）
- 新建课程空间：课堂笔记、作业、复习、实验报告等目录
- 整理周计划、deadline、考试倒计时
- 把 PDF / DOCX / PPTX / XLSX（以及图片、旧 Office）转成可读的 Markdown 资料
- 对导入后的 markdown 做保守修复（repair）
- 对历年试卷做 **exam-census**（题型普查 → 频率统计 → 题型解析 → 备考资料包）
- 把使用中的问题记到 `feedback/`，并准备/发布隐私检查后的 GitHub Issue
- 安全更新已安装的 `student-os`，**不碰**你的学习 vault 内容

一句话：先检查，再落盘，最后用 Git 留痕。

更细的能力状态见 [`docs/status.md`](./docs/status.md)；设计分层见 [`docs/architecture.md`](./docs/architecture.md)。

## 最简单的安装方式：直接发给 agent

普通用户不必先学会所有脚本。把下面这句话复制发给你的 agent 即可：

```text
请从 GitHub 仓库 Gu-Heping/college-student-workflow 安装 student-os skill。先只读检查 README 和安装脚本，确认只会安装到当前 agent 的 skills 目录、不修改我的学习 vault，然后运行对应平台的安装脚本。安装完成后告诉我安装位置、manifest 路径和如何更新。
```

## 不会命令行？直接把这些话发给 agent

下面这些话都可以直接复制使用。agent 应按 `student-os` 的约定：先检查、再改文件、最后给变更摘要，**不要自动提交**（除非你明确要求）。

安装：

```text
请从 GitHub 仓库 Gu-Heping/college-student-workflow 安装 student-os skill。先只读检查 README 和安装脚本，确认只会安装到当前 agent 的 skills 目录、不修改我的学习 vault，然后运行对应平台的安装脚本。安装完成后告诉我安装位置、manifest 路径和如何更新。
```

接管学习 vault：

```text
请把这个文件夹作为我的学习 vault 使用 student-os 管理。先检查目录结构和 Git 状态，不要修改任何文件；然后告诉我它是否适合接入 student-os，以及建议的下一步。
```

Git 安全检查：

```text
请检查当前学习 vault 的 Git 状态，把可以提交的学习资料改动、应该暂缓的临时文件/大文件/冲突文件分开列出来，不要自动提交。
```

新建课程：

```text
请用 student-os 给“模拟电子技术”新建课程空间，包含课堂笔记、作业、复习、实验报告目录。修改前先检查 Git 状态，完成后给我变更摘要和 commit 建议。
```

批量导入资料：

```text
请把这个课程资料文件夹里的 PDF/DOCX/PPTX/XLSX 转成可读的 Markdown 资料。先检查文件类型和是否需要 OCR，不要删除原文件，不要覆盖已有笔记。
```

考试题型普查：

```text
请用 student-os 对这门课的历年试卷做 exam-census：先扫描试卷 markdown sidecar，建立题型 taxonomy，再统计高频题型，生成题型解析和备考资料包。每一步都先说明产物位置。
```

周计划：

```text
请根据我的学习 vault 生成本周学习计划，优先考虑临近 deadline、考试复习、未完成作业和最近导入的资料。
```

总结变化：

```text
请总结这个学习 vault 最近 7 天的变化，并给出推荐 commit 分组、commit message 和需要暂缓提交的文件。
```

反馈问题：

```text
student-os 这次处理有问题，请把这个问题记录为 feedback，并准备一个 GitHub Issue 草稿。发布前先检查隐私信息，不要直接公开我的本地路径、课本内容、token 或个人资料。
```

更新：

```text
请检查 student-os 是否有更新。如果有，先告诉我当前版本、最新版本、更新内容和风险；确认后再更新。不要修改我的学习 vault。
```

## 手动安装方式

如果你会命令行，也可以自己装。先把仓库 clone 到本地，在仓库根目录执行：

Windows：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

macOS / Linux：

```bash
bash ./install.sh
```

或指定 agent / 安装范围：

```bash
python scripts/install_student_os.py --agent codex
python scripts/install_student_os.py --agent claude --scope project
python scripts/install_student_os.py --agent opencode
python scripts/install_student_os.py --agent all --json
```

说明：

- `--agent`：装给谁（`codex` / `claude` / `opencode` 等）
- `--scope user`：用户目录；`--scope project`：当前项目
- 默认尽量用 symlink，失败再回退到 copy
- 安装后会生成 `.student-os-install.json`，供后续自更新使用

## 日常使用场景

最常见的用法是对 agent 说自然语言（见上一节示例），而不是先背脚本。

如果你确实要自己跑脚本，常见入口：

```bash
# 检查学习 vault（注意：目标是你的 vault，不是本仓库）
python student-os/scripts/inspect_repo.py /path/to/vault

# 新建标准结构 / 新建课程
python student-os/scripts/scaffold_repo.py /path/to/vault
python student-os/scripts/scaffold_course.py /path/to/vault "模拟电子技术"

# 汇总最近变化 / Git 分组建议
python student-os/scripts/summarize_activity.py /path/to/vault --days 7
python student-os/scripts/group_git_changes.py /path/to/vault

# 批量转换资料（positional 参数是资料源目录/文件，不是 vault）
python student-os/scripts/materials_convert.py /path/to/materials --method auto

# 考试题型普查（需先有试卷的 .pdf.md sidecar）
python student-os/scripts/init_exam_census.py /path/to/vault --course <course> --exam-scope 期中
```

导入 PDF/DOCX 等前，先安装可选依赖：

```bash
pip install -r requirements.txt
```

Agent 侧的命令入口见 [`student-os/commands/`](./student-os/commands/)；工作流细节见 [`student-os/references/`](./student-os/references/)。

## 发现问题怎么反馈

完整闭环是：

1. 把问题记到学习 vault 的 `feedback/`
2. 分类（triage）、汇总
3. 生成 GitHub Issue 草稿
4. **发布前做隐私检查**
5. 确认后再发布；发布后把 issue 信息写回本地反馈条目

也可以直接对 agent 说上一节的「反馈问题」示例。

手动脚本入口（目标仍是你的 vault）：

```bash
python student-os/scripts/log_feedback.py /path/to/vault --title "PDF 导入后图示丢失"
python student-os/scripts/prepare_github_issue.py /path/to/vault feedback/triaged/example.md
python student-os/scripts/publish_github_issue.py /path/to/vault feedback/triaged/example.md --json
```

对任意要公开发布的正文（Issue / PR review / comment），应先走脱敏：

```bash
python student-os/scripts/prepare_github_issue.py --check-stdin --check-only < draft.md
python student-os/scripts/sanitize_and_post.py -- \
  gh issue create --repo Gu-Heping/college-student-workflow -F -
```

## 如何更新 student-os

更新只改已安装的 skill，**不会**改你的学习 vault。

```bash
python ~/.codex/skills/student-os/scripts/update_student_os.py --check
python ~/.codex/skills/student-os/scripts/update_student_os.py --apply --target ~/.codex/skills/student-os
```

（路径按你实际安装位置调整；也可让 agent 用上一节的「更新」示例帮你检查。）

- `--check`：比较当前版本与远端最新版
- `--apply`：应用更新；copy 安装会先备份并给出 rollback 命令
- 本地有手改时通常需要显式 `--force`

## 隐私与安全提醒

请务必记住：

- **不要盲目让 agent 执行陌生仓库脚本。** 安装前先让它只读检查 README 和安装脚本。
- 安装 / 更新 skill **不应修改**你的学习 vault。
- 真实 vault **不建议**公开上传到公开仓库。
- `.env`、token、简历、个人资料、课本原文、大文件 **不应**随便提交，也不应直接发到 GitHub Issue。
- 发布 GitHub Issue / PR comment / review 前，应先走脱敏检查（`prepare_github_issue.py --stdin` / `--check-only`，或 `sanitize_and_post.py`）。
- 本仓库（skill 源码）**不是**你的学习 vault；agent 不要把当前仓库误当成 vault 来改笔记。

## 推荐的学习 vault 结构

```text
courses/          # 课程主页、笔记、作业、复习、实验
projects/         # 课程/竞赛/个人项目
tasks/            # deadline、周计划、待办
reviews/          # 跨课复习产物（课程内复习也可放在 courses/.../reviews/）
references/       # 外部资料、导入材料
dashboards/       # 总览、周报
feedback/         # 使用问题与汇总
.student-os/      # repo profile、索引、状态缓存
```

多学期时可用：

- `courses/<semester>/<course>/`
- `semesters/<semester>/`

旧 vault 不必强行改名；`student-os` 更倾向在 `.student-os/repo-profile.md` 里做路径映射。

## 给开发者看的说明

如果你是来改这个仓库本身的，优先看：

| 文档 | 用途 |
| --- | --- |
| [`AGENTS.md`](./AGENTS.md) | 云端/开发 agent 入口与安全边界 |
| [`student-os/SKILL.md`](./student-os/SKILL.md) | skill 总路由 |
| [`docs/architecture.md`](./docs/architecture.md) | 文档与代码分层 |
| [`docs/status.md`](./docs/status.md) | 当前能力状态 |
| [`docs/maintenance.md`](./docs/maintenance.md) | 维护与发 PR 规则 |
| [`docs/roadmap.md`](./docs/roadmap.md) | 短期路线 |
| [`CHANGELOG.md`](./CHANGELOG.md) | 版本变化 |

仓库大致结构：

```text
student-os/     # skill：SKILL.md、commands、references、scripts、templates
examples/       # 演示与 smoke fixtures
scripts/        # 安装器、smoke runner、兼容包装
docs/           # 维护记录文档
```

## 测试

```bash
python -m py_compile scripts/install_student_os.py scripts/run_smoke_tests.py student-os/scripts/update_student_os.py
python scripts/run_smoke_tests.py
```

刷新示例仓库：

```bash
python scripts/run_smoke_tests.py --refresh-examples
```

CI 在 PR 与 main push 上会跑上述编译检查与 smoke tests（[`.github/workflows/smoke.yml`](./.github/workflows/smoke.yml)）。

## Roadmap

短期优先级见 [`docs/roadmap.md`](./docs/roadmap.md)。方向概览：

1. 安全边界与 CI 继续加固
2. README / agent 路由 / 文档入口保持同步
3. 用真实（脱敏）vault 做狗粮测试
4. 课程包与 exam-census 体验优化
