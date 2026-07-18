# Exam Census Quality Standards

Use this reference for Phase A–E after Aggregate. Mechanical census scripts stay unchanged; agents fill and gate content here.

## Content standard v2 — required section order

1. 元信息 (badge: frequency / score / difficulty / sources)
2. 真卷对应题号
3. 考前速记（一眼先记住 / 符号 / 术语 / 最容易混的 N 件事）
4. 本页最佳使用指引
5. 零基础先看这里（入口四问 + 最低掌握线）
6. 知识讲解 + 方法总结（决策树 + 最少必须记住的公式）
7. 例题精讲（≥2，标注方法引用）
8. 自测题（≥2，先试后看答案）
9. 来源校对说明

## Zero-foundation entry (must answer)

| Question | Block |
| --- | --- |
| 这题到底考什么？ | 这类题考试到底在考什么 |
| 看到什么特征先按什么想？ | 30秒认题 |
| 第一笔写什么？ | 2分钟下笔模板 |
| 不会做时怎样拿步骤分？ | 不会做时先写什么拿步骤分 |

Principles: conclusions/templates before deep theory; expand numeric substitution; first sentence of solutions states order; key observations only explain *why* or *common error*.

## Blockquote patterns

- Badge at top (`> **考试频率**` …)
- Decision trees as ASCII (`├─` / `└─`) preferred over long prose
- In solutions: `> **核心技巧**` (before), `> **关键**` (after result), `> **注意**`, `> **技巧总结**`
- Fill-in answer templates in `>` blocks with `[占位符]`
- Separate advanced tricks into an optional 考试技巧进阶指南 and link from type pages

## Phase scripts

```bash
# A — enqueue fill work for agents
python student-os/scripts/fill_type_analysis.py /path/to/vault --course linear-algebra --exam-scope 期中

# B — structural quality gate (exit 1 if any file needs-revision)
python student-os/scripts/review_type_analysis.py /path/to/vault --course linear-algebra --exam-scope 期中

# C — multi-dim analysis drafts under reviews/<scope>/analysis/
python student-os/scripts/build_multi_dim_stats.py /path/to/vault --course linear-algebra --exam-scope 期中

# D — agent-authored 真题精析 for 1–2 representative papers (no dedicated script; follow SOP)

# E — coverage / skeleton traceability
python student-os/scripts/cross_validate_exam_census.py /path/to/vault --course linear-algebra --exam-scope 期中
```

## Reviewer JSON shape (Phase B)

`review_type_analysis.py` writes `.student-os/state/exam-census/.../quality-reviews.json` with:

```json
{
  "file": "courses/.../题型解析/01-matrix-rank.md",
  "verdict": "pass",
  "checks": {
    "required_sections": {"pass": true, "issues": []},
    "entry_layer": {"pass": true, "issues": []},
    "worked_examples": {"pass": true, "issues": []},
    "self_tests": {"pass": true, "issues": []}
  }
}
```

Agents may revise a `needs-revision` file at most twice; then set `quality: needs-review` in frontmatter.
