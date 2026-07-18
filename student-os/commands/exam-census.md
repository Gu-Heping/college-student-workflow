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

Before any writing phase: inspect Git in the **learning vault** (not the skill source repo). Announce where artifacts will land before starting the next phase.

## Phase A–E (short)

| Phase | Goal |
| --- | --- |
| A Fill | Fill `题型解析/` pages from skeletons |
| B Quality | Structural quality gate (`review_type_analysis.py`) |
| C Multi-dim | Drafts under `analysis/` |
| D Deep-dive | Representative paper walkthroughs |
| E Cross-val | Coverage / traceability after prep pack |

Full checklist below; narrative detail in `references/exam-census-workflow.md`.

## Platform entry points

Prefer installing vault adapters once, then using the platform-native trigger:

```bash
python student-os/scripts/install_exam_census_adapters.py /path/to/vault \
  --platforms claude,cursor,opencode,github
```

| Platform | After adapters install | How to run |
| --- | --- | --- |
| Claude Code | `.claude/workflows/exam-census.js` | `/exam-census` with args `{vault, course, examScope, …}` |
| Cursor / Codex | `.cursor/rules/exam-census.mdc` | Ask for exam-census or `@exam-census` |
| OpenCode | `.opencode/exam-census.md` | Ask to run exam-census with vault/course/scope |
| GitHub Copilot | `.github/copilot-exam-census.md` | Merge into `copilot-instructions.md` if desired |

If adapters are not installed, follow this command’s stage checklist and call the Python scripts directly (same order).

## Stage checklist

0. **Adapters (optional)** — `install_exam_census_adapters.py` into the learning vault.
1. **Prepare** — convert PDFs to `.pdf.md` sidecars (`materials-convert`, prefer `--repair`).
2. **Init** — `init_exam_census.py` writes manifest + empty taxonomy stub.
3. **Taxonomy** — review-coach drafts `taxonomy.yaml` from 2–3 sample papers.
4. **Annotate** — coordinator splits batches; agents write `annotations/*.json` (one agent per batch).
5. **Aggregate** — `build_exam_type_stats.py --validate` writes `题型频率统计.md` + `题型解析/` skeletons; stop if validation fails.
6. **Fill (A)** — `fill_type_analysis.py` then agents fill pages per `exam-census-quality.md` (parallel per type).
7. **Quality gate (B)** — run `review_type_analysis.py` once; revise ≤2 rounds or mark `quality: needs-review`.
8. **Multi-dim (C)** — `build_multi_dim_stats.py --overwrite` drafts under `analysis/`.
9. **Deep-dive (D)** — `init_exam_deep_dive.py` scaffolds 1–2 representative paper walkthroughs.
10. **Prep pack** — 备考指南 / 公式总卡 / 答题模板 / 考前清单（含到 `题型解析/` 的真实链接）。
11. **Cross-val (E)** — `cross_validate_exam_census.py` coverage report（prep pack 之后再跑）。

See `references/exam-census-workflow.md` and `references/exam-census-quality.md`.
