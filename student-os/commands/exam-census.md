# exam-census

Intent: large-scale past-paper census and exam-prep pack generation.

Use when the user asks to:
- classify question types across many midterm/final papers
- compute type appearance frequencies
- generate type analyses ranked by frequency
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
5. **Aggregate** — `build_exam_type_stats.py --validate` writes `题型频率统计.md` + `题型解析/` skeletons; stop if validation fails before Synthesize.
6. **Synthesize** — review-coach fills analyses, then prep guide / formula card / templates / checklist.

See `references/exam-census-workflow.md` for the full SOP.
