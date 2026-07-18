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

## Blockquote patterns (page-level)

| Type | Role | Typical location |
| --- | --- | --- |
| Badge | Frequency / score / difficulty / sources in 30s | File top |
| Decision tree | Branching method choice (`├─` / `└─`) | 方法选择树 |
| Special trick callout | Cold / high-skill methods | After decision tree or in examples |
| Lookup table | Side-by-side contrasts | 考前速记 / 公式 |
| Advanced-guide link | Shared tricks live in one guide | Badge or 进阶技巧 |
| Motto / relation chain | One-line memorables | 考前速记 |

## Blockquote patterns (inside solutions)

| Type | Solves | Placement |
| --- | --- | --- |
| `> **核心技巧**` | Why this step? | Before a key step |
| `> **关键**` | What does this result mean? | After an intermediate result |
| `> **注意**` | How does this differ from the usual case? | After the solution |
| `> **技巧总结**` | Where else can this method apply? | End of worked example |
| Fill-in template | Exam-ready answer skeleton with `[占位符]` | After each judgment step |
| `> **口诀**` | Compress a criterion | 速记区 |

## Phase scripts

```bash
# A — enqueue fill work for agents
python student-os/scripts/fill_type_analysis.py /path/to/vault --course linear-algebra --exam-scope 期中

# B — structural quality gate (exit 1 if any file needs-revision)
python student-os/scripts/review_type_analysis.py /path/to/vault --course linear-algebra --exam-scope 期中

# C — multi-dim analysis drafts under reviews/<scope>/analysis/
python student-os/scripts/build_multi_dim_stats.py /path/to/vault --course linear-algebra --exam-scope 期中 --overwrite

# D — scaffold 1–2 representative paper deep-dives
python student-os/scripts/init_exam_deep_dive.py /path/to/vault --course linear-algebra --exam-scope 期中 --limit 2

# E — coverage / skeleton / prep-guide link traceability
python student-os/scripts/cross_validate_exam_census.py /path/to/vault --course linear-algebra --exam-scope 期中
```

## Reviewer JSON shape (Phase B)

`review_type_analysis.py` writes `.student-os/state/exam-census/.../quality-reviews.json` as a **report object**:

```json
{
  "course": "linear-algebra",
  "exam_scope": "期中",
  "exam_scope_key": "期中",
  "phase": "B",
  "max_rounds": 2,
  "file_count": 3,
  "pass_count": 0,
  "needs_revision_count": 3,
  "reviews": [
    {
      "file": "courses/.../题型解析/01-matrix-rank.md",
      "verdict": "needs-revision",
      "failed_checks": ["worked_examples", "method_reference"],
      "checks": {
        "required_sections": {"pass": true, "issues": []},
        "entry_layer": {"pass": false, "issues": ["empty entry block: 30秒认题"]},
        "worked_examples": {"pass": false, "issues": ["need >=2 filled worked examples with method refs, found 0"]},
        "self_tests": {"pass": false, "issues": ["need >=2 filled self-tests with answers, found 0"]},
        "method_reference": {"pass": false, "issues": ["need >=2 【方法引用】entries with content, found 0"]},
        "verification_steps": {"pass": false, "issues": ["missing verification/校验 steps"]},
        "no_placeholders": {"pass": true, "issues": []}
      }
    }
  ]
}
```

Structural checks also require non-placeholder body text (empty template headings alone fail). Agents may revise a `needs-revision` file at most twice; then set `quality: needs-review` in frontmatter.
