# Roadmap（短期）

不画大饼；按优先级推进。状态以 [`status.md`](./status.md) 为准。

## P0：安全和 CI

- 保持隐私脱敏与 `sanitize_and_post` 路径为发布默认推荐
- 巩固 Git hold-back（大文件、冲突、venv、密钥类路径）
- CI smoke + py_compile 保持绿灯；修回归优先于新功能

## P1：README / agent prompts / 文档入口

- 人类入口、agent 路由、维护文档三层保持一致（本轮重点）
- 新增能力时同步「一句话发给 agent」示例，避免只写在脚本注释里
- 消除互相矛盾的 reference；过时说法改为当前真实能力

## P2：真实 vault 狗粮测试

- 用脱敏后的真实课程结构做接入演练（不上传私有内容）
- 记录旧布局映射坑点，回写 `vault-governance` / status「需小心」项
- 验证中文路径、Windows 路径在导入与 exam-census 全链路

## P3：更多课程包 / exam-census 体验优化

- 扩充 `references/course-packs/`（按真实开课需求，不堆空包）
- exam-census：降低 Phase A–E 上手成本、更清晰的产物路径提示
- 多平台 adapters 安装体验与文档示例对齐

## 明确不做（近期）

- 把真实 vault 默认公开化
- 无确认的自动 `git commit` / `git push`
- 用本 skill 仓库冒充用户笔记库做「一键整理」演示数据污染
