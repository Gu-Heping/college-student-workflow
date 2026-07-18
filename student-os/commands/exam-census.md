# exam-census

Intent: large-scale past-paper census and exam-prep pack generation.

Use when the user asks to:
- classify question types across many midterm/final papers
- compute type appearance frequencies
- generate type analyses ranked by frequency
- raise skeletons to vault-quality type pages (Phase A–E)
- assemble an exam prep pack (guide, formula card, answer templates, one-hour checklist)

Default route:
- primary role: `review-coach`
- coordinator owns batching, progress checks, and final summary
- `file-operator` only when papers still need `materials_convert` / repair

## Stage checklist

1. **Prepare** — convert PDFs to `.pdf.md` sidecars (`materials-convert`, prefer `--repair`).
2. **Init** — `init_exam_census.py` writes manifest + empty taxonomy stub.
3. **Taxonomy** — review-coach drafts `taxonomy.yaml` from 2–3 sample papers.
4. **Annotate** — coordinator splits batches; agents write `annotations/*.json`.
5. **Aggregate** — `build_exam_type_stats.py --validate` writes `题型频率统计.md` + `题型解析/` skeletons; stop if validation fails.
6. **Fill (A)** — `fill_type_analysis.py` then agents fill pages per `exam-census-quality.md`.
7. **Quality gate (B)** — `review_type_analysis.py`; revise ≤2 rounds or mark `quality: needs-review`.
8. **Multi-dim (C)** — `build_multi_dim_stats.py --overwrite` drafts under `analysis/`.
9. **Deep-dive (D)** — `init_exam_deep_dive.py` scaffolds 1–2 representative paper walkthroughs.
10. **Cross-val (E)** — `cross_validate_exam_census.py` coverage report.
11. **Prep pack** — 备考指南 / 公式总卡 / 答题模板 / 考前清单；re-run E if needed.

See `references/exam-census-workflow.md` and `references/exam-census-quality.md`.
