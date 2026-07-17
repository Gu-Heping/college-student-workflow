# Changelog

本文档记录本项目的所有显著变更。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added

- 为 `student-os` 新增大规模试卷普查工作流（`exam-census`）：`init_exam_census.py` / `build_exam_type_stats.py`、题型 taxonomy/annotation 契约、频率统计与题型解析骨架生成，以及备考指南/公式总卡/答题模板/考前清单模板；配套 `exam-census-workflow.md`、命令入口与 review-coach/coordinator 路由。
- 为 `materials_convert.py` 增加内容探针与智能分流（`probe_materials.py`）：按 PDF/DOCX/PPTX/图片/旧 Office 特征选择 MinerU API（含自动 OCR）、PyMuPDF、pandoc/`docx_to_md` 或本地转换器，并支持 `--probe-only` / `--force-strategy`。
- 为 `student-os` 新增统一的 `token_loader.py`：按 CLI → 进程环境变量 → skill 根目录 `.env` → cwd `.env` 加载 `MINERU_TOKEN` / `MINERU_API_TOKEN`，并提供 `.env.example`；安装/更新时保留 skill 本地 `.env`（含 `--force` 重装），仓库与脚手架默认忽略真实 `.env`，并对已有 vault 的 `.gitignore` 追加缺失的密钥规则。
- 为 `prepare_github_issue.py` 增加 `--stdin` / `--check-only` / `--stdin-format json` / `--allow-privacy-warnings` 独立脱敏管道，使任意 issue draft 在直接 `gh issue create` 前也能走同一套隐私检查与脱敏逻辑；JSON 模式会同时扫描并脱敏 `title` 字段，warning 草稿默认拦截需显式放行，文档统一固定 `--repo Gu-Heping/college-student-workflow`。
- 为 `materials_convert.py` 的 MinerU API 路径增加大 PDF 自动拆分：超过 `--chunk-size`（默认 200 页）时分片转换并默认合并为一个 markdown sidecar；`--chunk-size` 会被裁剪到 MinerU 200 页上限，超过体积上限的 PDF 也会按体积拆分，分片图片按 part 前缀去重，`--no-merge` 会检查已存在分片避免覆盖并对每个分片执行 `--repair`，损坏 PDF 的探测失败会计入 errors 而非中断整个批次。
- 为 `student-os` 新增 GitHub feedback 发布链路，支持从本地反馈条目生成隐私检查后的 issue draft，并可选通过 `gh issue create` 发布。
- 为 `student-os` 新增自更新工作流：安装 manifest、`update_student_os.py`、更新命令入口与更新 reference，支持检查已安装版本、验证更新并提供回滚指引。
- 为 `student-os` 的反馈闭环补充生命周期脚本：`triage_feedback.py`、`resolve_feedback.py`，支持从原始反馈到已解决条目的标准流转。
- 为反馈条目新增稳定 `feedback_id`、开发者摘要、修复版本和 changelog 提示位，便于长期跟踪和开发回流。
- 为反馈汇总新增 `--audience developer` 视图，便于生成 issue-ready 的开发者交接摘要。
- 为 `PDF`、`DOCX`、`XLSX`、`PPTX` 导入链补充真实 fixture 驱动的 smoke coverage，并将导入产物纳入示例仓库。
- 为 `build_week_plan.py` 增加强化版规划工作台输出，补充 overdue carryover、exam countdown、inbox triage、import triage 与 `dashboards/weekly/` 周面板。

### Changed

- 扩展安装器，使每次成功安装都写入 `.student-os-install.json`，并为后续安全更新保留安装来源、提交版本与文件快照。
- 将自更新实现内聚到 `student-os/scripts/update_student_os.py`，使已安装 skill 自身即可执行检查、更新与回滚，而仓库根目录脚本保留为兼容包装层。
- 扩展 feedback schema 与模板，增加 `github_issue_*` 元数据，便于把本地反馈和开发者 issue 持续关联起来。
- 扩展 `README.md` 与 `SKILL.md`，明确 `update student-os` / `更新 student-os` 属于 skill maintenance，不会触碰用户知识库。
- 扩展 `feedback-ops` reference、`feedback` command、`feedback-operator` companion 和 `SKILL.md`，使反馈工作流覆盖记录、triage、resolve 和开发者交接四个阶段。
- 扩展 smoke test，将反馈生命周期纳入示例仓库与回归验证。
- 重写 `CHANGELOG.md` 为规范 UTF-8 中文版本，便于后续按 Keep a Changelog 持续维护。
- 扩展 smoke runner 与 `examples/single-semester-demo/`，使其同时展示课程导入稿、仪表盘汇总、slides 摘要和 PDF 修复产物。
- 扩展 `task-and-planning.md`、`weekly-plan.md` 和单学期示例，使计划链路从单纯 deadline 列表升级为更完整的学生周执行面板。
- 扩展 `group_git_changes.py`，为混合 dirty worktree 提供默认 hold-back 建议，并把冲突文件、缓存、临时日志与明显的二进制媒体/归档文件从推荐提交分组里分离出来。
- 扩展课程 slug 规则、academic workflow 文档与 smoke coverage，使课程名、学期名和作业标题在中文场景下保持可读、稳定的 Unicode 路径。
- 扩展 `inspect_repo.py` 与 `vault-governance.md`，使仓库检查结果能直接暴露 sync-conflict、缓存、本地工作区文件、临时文件与 binary-heavy 区域。
- 扩展 `group_git_changes.py` 的 Git 状态读取与 smoke coverage，使混合 dirty worktree 下的中文任务路径保持 UTF-8 可读输出。
- 扩展 `inspect_repo.py`、`group_git_changes.py` 与 smoke coverage，使超大 OCR/导出文本等 bulky 文件在默认仓库检查和 Git 分组中得到显式风险提示与 hold-back。

### Fixed

- 修复 `repair_markdown_import.py` 在写入含 Windows/Unicode 路径的 `derived_from_import` 时，`re.sub` 把 JSON `\uXXXX` 当作 replacement 转义并崩溃的问题；改用 callable replacement，避免 `--repair` 在 Windows 中文路径下不可用。
- 修复安装流程缺少可追踪安装元数据的问题，避免后续自更新无法判断安装来源、覆盖风险与回滚路径。
- 修复自更新对 legacy symlink 安装、project-scoped copy 安装、manifest 缺失安装和 fork/local source 安装的兼容与安全边界，避免误触用户 vault 仓库或静默切回上游源。
- 修复大文件检查对损坏符号链接的 `stat()` 崩溃问题，并补齐“已暂存但工作区已缩小/删除”的 oversized 文件识别，避免 `inspect_repo.py` 与 `group_git_changes.py` 漏报 index 中的大体积产物。
- 修复 `group_git_changes.py` CLI 输出仍将中文路径做 ASCII 转义的问题，改为直接输出 UTF-8 可读 JSON，并由 smoke test 锁定原始 stdout 行为。
- 修复 `run_smoke_tests.py --refresh-examples` 会把 `inspect_repo.py` 的 hygiene fixture 污染进 `examples/multi-semester-demo` 的问题，改为在隔离副本中验证仓库检查输出。
- 修复多学期周计划中的课程动作匹配逻辑：优先保留显式课程链接，重复课程名仍保留标题匹配，避免借用其他学期自动生成的 deadline 任务，保留同课程未链接的紧急任务，并兼容 legacy task link 回退匹配。
- 修复示例导入产物中残留临时绝对路径的问题，改为稳定的仓库内相对语义。
- 修复 MinerU-style PDF smoke fixture 对 raw 输出文件名的错误假设，避免回归测试误报。
- 修复 `group_git_changes.py` 对嵌套 `env/pyvenv.cfg` 虚拟环境目录的漏检，避免课程或项目子目录中的本地虚拟环境被错误纳入推荐提交分组。
- 修复 `group_git_changes.py` 对虚拟环境目录的证据判定：补充 `lib64` 覆盖，并避免把课程/项目中名为 `env`、`venv`、`.venv` 的正常路径在缺少 `pyvenv.cfg` 证据时误判为本地虚拟环境。
- 修复 `group_git_changes.py` 在虚拟环境证据探测中丢失原始路径大小写的问题，避免大小写敏感文件系统上的混合大小写课程路径漏检本地虚拟环境。
- 修复 `group_git_changes.py` 的 review 收尾问题：CLI 分类链路现已保留原始路径大小写传入虚拟环境检测，`tmp/temp` 只按真实路径组件命中，且 smoke test 不再写出额外 `__pycache__` 噪音。
- 修复中文课程名、中文学期名和中文作业标题会退化成 `course`、`semester` 等 ASCII 兜底 slug 的问题，避免真实知识库中的路径冲突和不可读目录名。
- 修复 Unicode slug 规则把组合附加符号误当作分隔符的问题，避免印地语等脚本的课程名和学期名在脚手架路径中被打碎。
- 修复 Windows 下脚手架脚本与 smoke harness 处理 Unicode 路径输出时的编码不一致问题，避免非 GBK 路径名触发 `UnicodeEncodeError` 或 `UnicodeDecodeError`。

## [0.6.0] - 2026-07-03

### Added

- 为 `student-os` 增加多学期知识库支持，允许同时管理单学期仓库和 `courses/<semester>/<course>/` 形式的多学期仓库。
- 新增 `semesters/` 顶层契约与 `templates/semester-overview.md`，用于维护学期总览和课程入口。
- 新增 `student-os/scripts/course_layout.py`，统一课程发现、路径解析与多学期课程定位逻辑。

### Changed

- 更新 `scaffold_course.py`，在创建带学期标签的课程时同步生成学期总览、课程列表，并启用仓库中的 semester mode。
- 更新 `scaffold_homework.py`、`build_review_indexes.py`、`build_week_plan.py`、`rebuild_indexes.py`、`inspect_repo.py` 和 `group_git_changes.py`，使多学期课程、legacy 课程和 Git 分组策略保持一致。
- 更新 `README.md`、`SKILL.md`、`academic-workflow.md`、`vault-governance.md`、`repo-profile.md`、`course-home.md` 和 `course-dashboard.md`，补充多学期仓库约定与使用示例。

### Fixed

- 修复多学期课程下作业脚手架、周计划、review 索引和课程索引无法正确识别嵌套课程目录的问题。
- 修复 semester overview 会覆盖用户手写内容、错误回填课程标题或错误翻转 `semesters.enabled` 标志的问题。
- 修复 legacy 课程目录在缺少 `index.md` 时无法被发现，导致作业脚手架和索引脚本退化的问题。

## [0.5.0] - 2026-07-03

### Added

- 为 `student-os` 新增仓库内反馈闭环工作流，支持将使用中的问题、体验落差和改进建议沉淀为结构化反馈条目。
- 新增 `feedback` 命令入口、`feedback-operator` companion、`feedback-ops` reference，以及反馈条目和反馈汇总模板。
- 新增 `log_feedback.py` 与 `summarize_feedback.py`，用于记录单条反馈和生成周期性反馈汇总。
- 为仓库脚手架新增 `feedback/raw`、`feedback/triaged`、`feedback/resolved` 和 `feedback/summaries` 目录。

### Changed

- 扩展 `student-os` 总控 skill，使其能够识别反馈记录、反馈汇总和反馈状态流转请求。
- 扩展 Git 变更分组规则，使反馈文件能够与课程、作业、复习和仓库运维改动分开建议提交。
- 在 `README.md` 中新增 feedback loop 使用说明，并说明反馈与 `CHANGELOG.md` 的关系。

### Fixed

- 修复反馈脚本对 summary 标题的路径安全问题，避免越界写入非 `feedback/summaries` 文件。
- 修复反馈 frontmatter 中多行文本的编码问题，避免换行污染 `status` 等元数据解析。

## [0.4.0] - 2026-07-03

### Added

- 新增 `student-os` 一键安装器，支持为 Codex、Claude Code 和 OpenCode 安装 skill。
- 新增跨平台安装入口 `install.ps1`、`install.sh` 与 `scripts/install_student_os.py`。
- 在 `README.md` 中补充安装方式、目标目录和常见安装命令。

### Changed

- 将 Codex 的默认安装目录调整为 `$CODEX_HOME/skills` 或 `~/.codex/skills`，并支持项目级 `.codex/skills`。
- 将项目级安装的默认策略调整为复制安装，以避免绝对符号链接造成的不便携问题。
- 默认安装路径策略避免为 OpenCode 生成重复可见的同名 skill。
- 将 Windows 的推荐安装命令调整为显式使用 `ExecutionPolicy Bypass`。

### Fixed

- 修复 `install.sh` 的可执行权限问题，避免在 macOS/Linux 下直接执行失败。

## [0.3.0] - 2026-07-02

### Added

- 新增文件导入与资料处理链路，覆盖 `PDF`、`DOCX`、`XLSX` 和 `PPTX`。
- 新增 `file-operator` companion 角色，以及 `import-file`、`pdf-to-md`、`tabular-summary` 命令入口。
- 新增导入类模板、文件处理 references 与相关脚本。
- 新增 `requirements.txt`，声明导入脚本依赖。

### Changed

- 将 PDF 导入扩展为 generic 和 MinerU-style 双模式。
- 将导入产物正式接入 `student-os` 的知识库契约与 Git 分组规则。

### Fixed

- 改进 PDF 导入的修复链路、图片占位保留与修复来源说明。
- 修复 DOCX 表格与段落输出顺序，保持原始文档块顺序。
- 修复 XLSX 大表截断策略、Markdown 转义与公式回退逻辑。
- 修复导入类 frontmatter 的 YAML 路径安全性。

## [0.2.0] - 2026-07-02

### Added

- 扩展 `student-os` 的作业、题解、复习、周回顾与课程规则包能力。
- 新增 `homework-solution`、`chapter-review`、`weekly-review-digest`、`problem-analysis` 等模板。
- 新增三门种子课程规则包：`analog-electronics`、`calculus-ii`、`data-structures`。
- 新增作业脚手架、review 索引与 Git 分组增强脚本。

### Changed

- 将原有大学生工作流收敛为更强的单入口 `student-os` 主链。
- 强化 companion 协作层中 `course-tutor` 与 `review-coach` 的职责分工。

### Fixed

- 修复周计划截止日期窗口、作业脚手架 backlink、review 索引匹配与 dashboard 索引问题。
- 根据 review 结果修正 Git 变更分组与仓库脚手架细节。

## [0.1.0] - 2026-07-02

### Added

- 初始提供 `student-os` 顶层 skill，建立 Git-first 的大学生知识库工作流定位。
- 新增基础仓库契约、课程、任务、项目、复习目录约定与模板集合。
- 新增基础脚本，包括仓库检查、课程脚手架、索引重建、活动汇总与 Git 分组辅助。
- 新增 `README.md`，说明仓库目标与 `student-os` 的使用方式。

[Unreleased]: https://github.com/Gu-Heping/college-student-workflow/compare/9a663267a29055728fd5f2425548dc327c830bb7...HEAD
[0.6.0]: https://github.com/Gu-Heping/college-student-workflow/compare/a00ee8f01bc15ed6f09339e1b37c8166a765987a...9a663267a29055728fd5f2425548dc327c830bb7
[0.5.0]: https://github.com/Gu-Heping/college-student-workflow/compare/d51e56ec1416be3b937f067c65798e4a108b728e...a00ee8f01bc15ed6f09339e1b37c8166a765987a
[0.4.0]: https://github.com/Gu-Heping/college-student-workflow/compare/05b35868f272176a4e52cbab4ae5159018790b8d...32ad733bf899c946b300944e2c5e6250aa1c05ea
[0.3.0]: https://github.com/Gu-Heping/college-student-workflow/compare/98ab862469f2b6ea9425a3d3c629b02084879e21...05b35868f272176a4e52cbab4ae5159018790b8d
[0.2.0]: https://github.com/Gu-Heping/college-student-workflow/compare/31a7b84a17bae94cc016c7ecc24734b155d96993...98ab862469f2b6ea9425a3d3c629b02084879e21
[0.1.0]: https://github.com/Gu-Heping/college-student-workflow/compare/b9c2f0ed66e495a0c4d3b02583814a48e0dbfbc3...31a7b84a17bae94cc016c7ecc24734b155d96993
