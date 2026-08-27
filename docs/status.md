# 当前能力状态

最后核对：文档整理 PR（docs 层）。功能以仓库脚本与 smoke tests 为准；此处不把「计划中」写成「已支持」。

## 已可用

| 能力 | 说明 |
| --- | --- |
| **install** | `install.sh` / `install.ps1` / `scripts/install_student_os.py`；支持 Codex / Claude Code / OpenCode / DeepSeek Harness (DSH)，写入 `.student-os-install.json` |
| **self-update** | `student-os/scripts/update_student_os.py`：`--check` / `--apply`、备份与 rollback 指引；不碰用户 vault |
| **DSH native tools** | `integrations/dsh/`：本地 Cordis plugin，提供 `student_os_inspect` / `student_os_group_changes` / `student_os_frontmatter`，复用 Python core；`scripts/bootstrap_dsh.py` 可生成 project-local overlay；官方 API/package/bootstrap smoke 已通过，Windows 真实 DSH 已验证 project Skill discovery、plugin mount 与三个 native tools |
| **Git safety** | `inspect_repo.py`、`group_git_changes.py`：脏工作区分组、hold-back（冲突/缓存/大文件/venv 等）；默认不自动提交 |
| **feedback lifecycle** | `log` → `triage` → `resolve` → `summarize`；稳定 `feedback_id` |
| **GitHub issue publishing** | `prepare_github_issue.py` + `publish_github_issue.py`；需 `gh` 认证，否则 draft 降级 |
| **privacy redaction** | `--stdin` / `--check-stdin` / `--check-only`；`sanitize_and_post.py` 包装 `gh`；有 warning 默认拦截 |
| **materials_convert** | 批量 PDF/DOCX/PPTX/XLSX/图片/旧 Office → markdown sidecar；positional 为 source，非 vault |
| **MinerU API** | `--method auto` / `--method api`；有 token 时走 v4 精准 API；`auto` 无 token 时 ≤10MB 文件可走 v1 Agent 免登录 API；PDF 按 ≤20 页/片限制自动拆分合并 |
| **markdown repair** | `repair_markdown_import.py`；`materials_convert --repair` / `--repair-only`；AI 导入修复队列/case/proposal/review/apply 闭环可生成证据包并阻止未审查 proposal 直接落盘 |
| **exam-census** | Init → taxonomy → annotate → aggregate；Phase A–E（fill / quality / multi-dim / deep-dive / cross-val）；备考包模板；多平台 adapters |
| **smoke tests / CI** | `scripts/run_smoke_tests.py`、`scripts/run_import_repair_evals.py`；`.github/workflows/smoke.yml` |

## 部分可用 / 需小心

| 能力 | 注意 |
| --- | --- |
| **MinerU / OCR** | 无 token 且超过 v1 Agent 10MB 限制时需配置 token；`--force-strategy ocr/mineru-api` 仍按强制策略处理。质量依赖源文件与 API |
| **AI 导入修复** | 可尽量无人值守生成 proposal 和自动审查，但 `verified` 仍只表示人工对照原 PDF/原文确认；无视觉证据时保持 blocked/unverified |
| **旧 vault 接入** | 可映射，不强制改名；复杂布局需人工确认 `repo-profile.md` |
| **exam-census 内容质量** | 脚本生成骨架与门禁；题型解析正文仍依赖 agent 填写，需跑 Phase B |
| **GitHub 发布** | 隐私 warning 需显式确认；裸管道接 `gh` 不安全 |
| **Windows 路径 / 中文路径** | 多数已覆盖；导入 repair、Git 分组已有针对性修复，仍建议用 smoke 回归 |
| **课程包** | 仅少量 seed course packs；其他课程走通用 academic workflow |

## 计划中

见 [`roadmap.md`](./roadmap.md)。概要：

- 更强的旧 vault 识别与迁移建议
- 更细的 Git hold-back 与真实 vault 狗粮测试
- 更多课程包与 exam-census 体验打磨
- 文档入口与 agent prompt 持续同步（本轮已推进）

## 已知风险

- Agent 可能把 **skill 源码仓库**误当作用户 vault——文档与 `AGENTS.md` 已强调禁止。
- 用户可能让 agent **盲目执行**陌生安装脚本——README 要求先只读检查。
- 公开 Issue 可能泄露路径 / token / 课本——必须走脱敏。
- 真实 vault 含隐私与大文件——**不要**推到公开仓库。
- `materials_convert` 若误传 vault 路径，可能在 vault 内大量生成 sidecar——应确认 positional 是资料源。
