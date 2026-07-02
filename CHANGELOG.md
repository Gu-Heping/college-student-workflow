# Changelog

此文件记录本项目的所有显著变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，并且本项目遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.4.0] - 2026-07-03

### Added

- 新增 `student-os` 一键安装器，支持为 Codex、Claude Code 与 OpenCode 安装 skill。
- 新增跨平台安装入口 `install.ps1`、`install.sh` 与 `scripts/install_student_os.py`。
- 在 README 中补充安装方式、目标目录和常见安装命令。

### Changed

- 将 Codex 的默认安装目标调整为 `$CODEX_HOME/skills` 或 `~/.codex/skills`，并支持项目级 `.codex/skills`。
- 将项目级安装的默认策略调整为复制安装，以避免绝对符号链接造成的不可移植问题。
- 默认安装路径策略避免为 OpenCode 生成重复可见的同名 skill。
- 将 Windows 的推荐安装命令调整为显式使用 `ExecutionPolicy Bypass`。

### Fixed

- 修复 `install.sh` 的可执行权限问题，避免在 macOS/Linux 下直接执行失败。

## [0.3.0] - 2026-07-02

### Added

- 新增文件导入与资料处理链路，覆盖 `PDF`、`DOCX`、`XLSX` 与 `PPTX`。
- 新增 `file-operator` companion 角色以及 `import-file`、`pdf-to-md`、`tabular-summary` 命令入口。
- 新增导入类模板、文件处理 references 与相关脚本。
- 新增 `requirements.txt`，声明导入脚本依赖。

### Changed

- 将 PDF 导入扩展为 generic 与 MinerU-style 双模式。
- 将导入产物正式接入 `student-os` 的知识库契约与 Git 分组规则。

### Fixed

- 改进 PDF 导入的修复链路、图片占位保留与修复稿 provenance。
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

- 初始化 `student-os` 顶层 skill，建立 Git-first 的大学生知识库工作流定位。
- 新增基础仓库契约、课程/任务/项目/复习目录约定与模板集合。
- 新增基础脚本，包括仓库检查、课程脚手架、索引重建、活动汇总与 Git 分组辅助。
- 新增 README，说明仓库目标与 `student-os` 的使用方式。

[Unreleased]: https://github.com/Gu-Heping/college-student-workflow/compare/32ad733bf899c946b300944e2c5e6250aa1c05ea...HEAD
[0.4.0]: https://github.com/Gu-Heping/college-student-workflow/compare/05b35868f272176a4e52cbab4ae5159018790b8d...32ad733bf899c946b300944e2c5e6250aa1c05ea
[0.3.0]: https://github.com/Gu-Heping/college-student-workflow/compare/98ab862469f2b6ea9425a3d3c629b02084879e21...05b35868f272176a4e52cbab4ae5159018790b8d
[0.2.0]: https://github.com/Gu-Heping/college-student-workflow/compare/31a7b84a17bae94cc016c7ecc24734b155d96993...98ab862469f2b6ea9425a3d3c629b02084879e21
[0.1.0]: https://github.com/Gu-Heping/college-student-workflow/compare/b9c2f0ed66e495a0c4d3b02583814a48e0dbfbc3...31a7b84a17bae94cc016c7ecc24734b155d96993
