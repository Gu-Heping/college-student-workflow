# College Student Workflow

这是一个面向大学生学习资料库、Obsidian vault、Markdown 笔记库的 agent workflow 仓库。  
它的核心 skill 是 [`student-os`](./student-os/)，可以让 `Codex`、`Claude Code`、`OpenCode` 这类 agent 在动手改文件前先检查仓库和 `Git` 状态，再整理资料、生成目录、汇总改动、给出提交建议。  
这样做的目的，是减少误改、误删、乱提交、把无关文件混进 commit 这类风险。  
现在它已经支持安装、日常使用、仓库内反馈、发布到 GitHub Issue，以及安装后的自更新。  
最近的变化可以看 [CHANGELOG.md](./CHANGELOG.md)。

## 这是什么

`college-student-workflow` 是一个围绕 `student-os` 搭建的仓库。你可以把它理解成：

- 给学习资料库用的 agent `skill`
- 给 Markdown-first 学习仓库用的工作规范
- 给 AI 使用者准备的一套“先检查、再落盘、最后用 Git 留痕”的安全工作流

它不是单纯的笔记模板，也不是只给程序员用的工具箱。它更像一个“让 agent 在你的学习文件夹里干活时更稳一点”的操作层。

## 适合谁

适合这些人：

- 平时用 Obsidian、Markdown、文件夹管理课程资料的人
- 想让 AI 帮自己整理课程、作业、复习资料，但又担心改乱文件的人
- 希望把学习资料纳入 `Git` 管理，能看改动、能回滚、能分提交的人
- 想把“安装 skill -> 日常使用 -> 反馈问题 -> GitHub Issue -> 后续更新”串成闭环的人

如果你只是随手记几条临时笔记、完全不想接触文件夹结构或 `Git`，这个仓库可能会偏重。

## 它能做什么

`student-os` 目前能覆盖这些事情：

- 初始化或检查一个学习资料库
- 识别课程、作业、复习、任务、项目、dashboard 等目录
- 给课程建主页、笔记区、作业区、复习区
- 帮你整理本周资料变化，给出 `commit` 建议
- 导入和整理 PDF、DOCX、XLSX、PPTX 等资料
- 把使用中的问题记录到 `feedback/`
- 把反馈整理成 GitHub Issue 草稿，并在发布前做隐私检查
- 对已安装的 `student-os` 做安全更新，不碰你的真实 vault 内容

一句话说：它的目标不是替你“自动写完一切”，而是让 agent 在你的知识库里工作得更可控、更可追踪。

## 快速安装

如果你会命令行，可以直接看下面的安装命令。  
如果你不会命令行，建议先看下一节“直接把这些话发给 agent”。

先把这个仓库 clone 到本地，然后在仓库根目录运行安装命令。

Windows：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

macOS / Linux：

```bash
bash ./install.sh
```

如果你想手动指定安装方式，也可以直接调用安装脚本：

```bash
python scripts/install_student_os.py --agent codex
python scripts/install_student_os.py --agent claude --scope project
python scripts/install_student_os.py --agent opencode
python scripts/install_student_os.py --agent all --json
```

说明：

- `--agent` 用来指定装给谁，例如 `codex`、`claude`、`opencode`
- `--scope user` 是装到用户目录，`--scope project` 是装到当前项目里
- 默认会尽量用 symlink，失败时再回退到 copy

安装后会生成一个安装清单 `.student-os-install.json`，后续自更新会用到它。

## 不会命令行？直接把这些话发给 agent

如果你平时主要是在 `Codex`、`Claude Code`、`OpenCode` 里工作，很多事情不一定要自己敲命令。  
你可以直接复制下面这些话发给 agent，让它先检查、再执行、最后汇报结果。

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

整理资料：

```text
请帮我整理这个课程文件夹，把明显的课件、作业、复习资料、实验报告分类；不要删除原文件，所有移动/改名都先给计划，确认后再执行。
```

生成周计划：

```text
请根据我的学习 vault 生成本周学习计划，优先考虑临近 deadline、考试复习、未完成作业和最近导入的资料。
```

导入文件：

```text
请把这个 PDF/DOCX/PPTX/XLSX 导入到对应课程资料中，生成可读的 Markdown 摘要。保留原文件，不要覆盖已有笔记。
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

安全提醒：

- 不要让 agent 盲目执行陌生仓库脚本
- 安装前应先让 agent 只读检查 README 和安装脚本
- 安装 / 更新 `student-os` 不应该修改你的学习 vault
- 真实 vault 不建议公开上传
- GitHub Issue 发布前必须检查隐私信息

## 日常怎么用

最常见的用法，不是先记脚本，而是直接对 agent 说自然语言。

例如：

- “把这个文件夹作为我的学习 vault，先检查 Git 状态”
- “帮我给模电课程建一个复习目录”
- “总结这周学习资料有哪些变化，并给我 commit 建议”
- “把这个问题反馈给开发者”
- “更新 student-os”

如果你想直接跑脚本，常见入口有这些：

先检查一个已有资料库：

```bash
python student-os/scripts/inspect_repo.py /path/to/repo
```

新建一个标准资料库：

```bash
python student-os/scripts/scaffold_repo.py /path/to/repo
```

给课程建目录：

```bash
python student-os/scripts/scaffold_course.py /path/to/repo "Analog Electronics"
```

重建索引：

```bash
python student-os/scripts/rebuild_indexes.py /path/to/repo
```

汇总最近变化：

```bash
python student-os/scripts/summarize_activity.py /path/to/repo --days 7
```

如果你要处理 PDF、DOCX、XLSX、PPTX，先安装依赖：

```bash
pip install -r requirements.txt
```

## 发现问题怎么反馈

现在这套流程已经不只是“本地记个反馈”，而是支持：

1. 把问题记录到仓库里的 `feedback/`
2. 做分类、triage、汇总
3. 生成 GitHub Issue 草稿
4. 发布前做隐私检查
5. 发布到 GitHub 后把 issue 信息回写到本地 feedback 条目

常见命令：

```bash
python student-os/scripts/log_feedback.py /path/to/repo --title "PDF 导入后图示丢失"
python student-os/scripts/triage_feedback.py /path/to/repo feedback/raw/2026-07-16-pdf.md
python student-os/scripts/summarize_feedback.py /path/to/repo --title "Weekly feedback review"
python student-os/scripts/prepare_github_issue.py /path/to/repo feedback/triaged/example.md
python student-os/scripts/publish_github_issue.py /path/to/repo feedback/triaged/example.md --json
```

如果存在隐私告警，发布前应先停在 draft，检查草稿后再决定是否继续。

隐私提醒很重要：

- 真实学习 vault 不建议公开上传
- 课本内容、简历、个人资料、大文件、`.env` 不应随便提交
- 发 GitHub Issue 前，一定要先看草稿和隐私提示
- 如果脚本检测到隐私风险，默认应该先停在 draft，而不是直接发布

## 如何更新 student-os

`student-os` 支持安装后的安全更新，而且更新目标只是 skill 本身，不会改你的学习 vault 内容。

先检查：

```bash
python ~/.codex/skills/student-os/scripts/update_student_os.py --check
```

再应用更新：

```bash
python ~/.codex/skills/student-os/scripts/update_student_os.py --apply --target ~/.codex/skills/student-os
```

说明：

- `--check` 会比较当前安装版本和远端最新版本
- `--apply` 会更新 skill 文件
- copy 安装会先做备份，并给出 rollback 命令
- 如果本地安装有手改内容，通常需要显式 `--force`

## 推荐的知识库结构

推荐的基础结构如下：

```text
courses/
projects/
tasks/
reviews/
references/
dashboards/
.student-os/
feedback/
```

其中：

- `courses/` 放课程主页、课堂笔记、作业、复习资料
- `projects/` 放课程项目、竞赛项目、个人项目
- `tasks/` 放 deadline、每周计划、待办
- `reviews/` 放期中期末复习产物
- `references/` 放外部资料、导入材料、课本摘要
- `dashboards/` 放总览、周报、进度页
- `.student-os/` 放 repo profile、索引、状态缓存
- `feedback/` 放使用过程中的问题反馈与汇总

如果你是多学期管理，也可以用：

- `courses/<semester>/<course>/`
- `semesters/<semester>/`

`student-os` 不强制你把旧 vault 全部改名，它更倾向于“识别和映射”，而不是“一刀切重构”。

## 给开发者看的说明

如果你是来改这个仓库本身的，可以重点看这些位置：

- [`student-os/`](./student-os/)：核心 skill
- [`student-os/SKILL.md`](./student-os/SKILL.md)：主入口和行为合同
- [`student-os/references/`](./student-os/references/)：各工作流说明
- [`student-os/scripts/`](./student-os/scripts/)：脚本入口
- [`student-os/templates/`](./student-os/templates/)：模板
- [`CHANGELOG.md`](./CHANGELOG.md)：版本变化

仓库结构大致如下：

```text
student-os/
  SKILL.md
  references/
  scripts/
  templates/
examples/
scripts/
CHANGELOG.md
README.md
```

当前已经覆盖的重点能力包括：

- Git-first 的资料库治理
- 多学期课程结构
- 文件导入处理
- feedback -> GitHub Issue 发布闭环
- 安装清单和 skill 自更新

有几条实现原则建议继续保持：

- Markdown first
- Git friendly
- agent friendly
- 旧资料库尽量映射接入，而不是强制迁移
- 可再生索引和状态尽量脚本化

## 测试

最直接的回归测试方式：

```bash
python scripts/run_smoke_tests.py
```

如果你要先检查关键脚本能不能编译：

```bash
python -m py_compile scripts/install_student_os.py
python -m py_compile scripts/run_smoke_tests.py
python -m py_compile student-os/scripts/update_student_os.py
```

CI 会在 PR 和 main push 上运行 py_compile 与 smoke tests。

如果你想刷新示例仓库：

```bash
python scripts/run_smoke_tests.py --refresh-examples
```

仓库里保留了这些重要入口，请不要在 README 里丢掉：

- [`student-os/`](./student-os/)
- [`CHANGELOG.md`](./CHANGELOG.md)
- [`scripts/install_student_os.py`](./scripts/install_student_os.py)
- [`scripts/run_smoke_tests.py`](./scripts/run_smoke_tests.py)
- [`.github/workflows/smoke.yml`](./.github/workflows/smoke.yml)

## Roadmap

接下来比较值得继续推进的方向：

1. 更强的旧 vault 识别和迁移建议
2. 更细的 Git change grouping 与 hold-back 规则
3. 更强的课程 / 作业 / 复习自动串联
4. 更稳的导入处理回归测试
5. 更完整的多 agent 协作体验
6. 更细的反馈闭环与 GitHub Issue / CHANGELOG 联动

## 补充说明

这个仓库默认是“文本优先、版本控制优先”的路线。

- 二进制大文件可以存在，但不是第一设计目标
- 真实学习资料库往往包含隐私，不建议直接公开
- 真正重要的不是“让 agent 自动做更多”，而是“让它做事前后都能被你看懂、检查、回滚”
