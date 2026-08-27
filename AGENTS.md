# AGENTS.md

## 这份文件给谁看

给在本仓库里干活的 **开发 / 云端 agent**（例如 Cursor Cloud），以及需要快速理解安全边界的维护者。

- **普通人学怎么用**：看 [`README.md`](./README.md)
- **已安装的 skill 日常路由**：看 [`student-os/SKILL.md`](./student-os/SKILL.md)
- **维护状态与发 PR 规则**：看 [`docs/`](./docs/)

## 仓库性质

`college-student-workflow` 是 Python 核心 + 可选 DSH 插件的 CLI / skill 工具包（核心是 `student-os`）。**没有**长期运行的服务、端口、数据库——开发就是跑 Python CLI、DSH 插件 npm 检查与 smoke tests。

- 核心依赖：Python 3 + `git`
- 可选依赖：`requirements.txt`（`pdfplumber`、`pypdf`、`pymupdf`、`python-docx`、`openpyxl`、`python-pptx`、`mineru-open-sdk`），仅资料导入需要
- 可选 DSH 插件：`integrations/dsh/`，改动后跑 `npm ci`、`npm run build`、`npm run test`
- 测试：`python scripts/run_smoke_tests.py`
- 编译检查：`python -m py_compile scripts/bootstrap_dsh.py scripts/dsh_plugin_build.py scripts/extract_release_notes.py scripts/install_student_os.py scripts/run_import_repair_evals.py scripts/run_smoke_tests.py student-os/scripts/update_student_os.py student-os/scripts/repair_import_queue.py student-os/scripts/repair_import_case.py student-os/scripts/repair_import_review.py student-os/scripts/repair_import_apply.py`
- CI：`.github/workflows/smoke.yml`（PR 与 main push）

## 最重要的安全边界

1. **本仓库 ≠ 用户学习 vault。** CLI 的目标目录是用户传入的 vault 路径；永远不要把本仓库当成 vault 去改笔记、跑 scaffold、写 feedback。
2. **会改文件的 workflow，先检查 Git 状态**（`inspect_repo.py` / `group_git_changes.py`），并区分「任务产生的改动」与「预先已有的脏文件」。
3. **安装 / 更新 skill** 只动 skill 目录（用户级，或项目内 `.codex/skills` 等），不改 vault 笔记内容。普通用户优先 `--scope user`。
4. **公开发布**（GitHub Issue / PR review / comment）前必须脱敏；有隐私告警或检查失败时默认停在 draft，禁止继续调用 `gh`，除非用户显式确认。
5. **不要提交**真实 vault、课本原文、token、`.env`、大文件到本公开仓库。

## 意图 → workflow 路由

用户意图（自然语言）按下面路由；细节在 `student-os/SKILL.md` 与 `student-os/references/`。

| 用户意图 | 进入 |
| --- | --- |
| 安装 / 更新 student-os | skill maintenance → `references/update-workflow.md`；安装用仓库根 `scripts/install_student_os.py` / `install.sh` / `install.ps1` |
| 检查 vault / Git 状态 | repo governance → `references/vault-governance.md` + `group_git_changes.py` |
| 新建课程 / 作业 / 复习 / 实验 | academic workflow → `references/academic-workflow.md` |
| 导入 PDF/DOCX/PPTX/XLSX/图片/旧 Office | file-handler → `references/file-handler.md`；批量用 `materials_convert.py` |
| 修复导入 markdown | repair → `repair_markdown_import.py` / `materials_convert.py --repair` |
| 考试题型分析 / 真题普查 | exam-census → `references/exam-census-workflow.md`（Phase A–E） |
| 反馈问题（本地） | feedback → `references/feedback-ops.md` |
| 发布到 GitHub Issue | github-feedback → `references/github-feedback.md` |
| 公开发布文本前脱敏 | `prepare_github_issue.py --stdin` / `--check-only` 或 `sanitize_and_post.py` |

## 脚本 Gotchas（开发时必看）

- CLI 脚本操作的是 **参数传入的目标 vault**，例如：`python student-os/scripts/inspect_repo.py /path/to/vault`。
- `materials_convert.py` 的 **唯一 positional 参数是 source file/dir，不是 vault**。默认在源文件旁写 `<name>.<ext>.md`；可用 `--output-root`。`--method local` 强制本地转换，避免走托管 MinerU API。
- `--method api` 需要 `MINERU_TOKEN` / `MINERU_API_TOKEN`（CLI、进程环境，或 skill/cwd `.env`），没有 token 会失败。`--method auto` 在有用时优先 MinerU，无 token 时降级到本地转换或 index sidecar。强制 `--force-strategy mineru-api|ocr` 无 token 也会报错。可选 `pandoc` 改善 DOCX 路由。
- `publish_github_issue.py` 需要已登录的 `gh`；没有 `gh` 时降级为 draft / 可复制命令。不要用裸 `|` 把脱敏输出直接接 `gh`（无 `pipefail` 时可能创建空 body）；用 `sanitize_and_post.py`。

## Cursor Cloud 速查

与上文相同：无服务要启动；改功能后至少跑 py_compile + smoke tests；文档改动规则见 [`docs/maintenance.md`](./docs/maintenance.md)。
