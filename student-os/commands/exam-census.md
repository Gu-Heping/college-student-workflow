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
| 5 Prep pack | L1–L4 四层资料包（须在 Phase B 通过后） |
| E Cross-val | Coverage + prep-pack 四层完整性（prep pack 后再跑） |

Full checklist below; narrative detail in `references/exam-census-workflow.md`.

## Platform entry points

Prefer installing vault adapters once, then using the platform-native trigger:

```bash
python student-os/scripts/install_exam_census_adapters.py /path/to/vault \
  --platforms claude,cursor,opencode,github
```

| Platform | After adapters install | How to run |
| --- | --- | --- |
| Claude Code | `.claude/skills/exam-census/SKILL.md` + `.claude/commands/exam-census.md` | `/exam-census vault="…" course="…" examScope="…"` |
| Cursor / Codex | `.cursor/rules/exam-census.mdc` | Ask for exam-census or `@exam-census` |
| OpenCode | `.opencode/exam-census.md` | Ask to run exam-census with vault/course/scope |
| GitHub Copilot | `.github/copilot-exam-census.md` | Merge into `copilot-instructions.md` if desired |

Claude 端默认使用 skill/command **runbook** 入口（自然语言或 `/exam-census`）；`.claude/workflows/exam-census.js` 仅作为实验性适配（需 `--include-experimental-claude-workflow`），不作为推荐入口。不要使用 Workflow 工具加载自定义 workflow。

If adapters are not installed, follow this command’s stage checklist and call the Python scripts directly (same order).

## Stage checklist

0. **Adapters (optional)** — `install_exam_census_adapters.py` into the learning vault.
1. **Prepare** — convert PDFs to `.pdf.md` sidecars (`materials-convert`, prefer `--repair`).
2. **Init** — `init_exam_census.py` writes manifest + empty taxonomy stub.
3. **Taxonomy** — review-coach drafts `taxonomy.yaml` from 2–3 sample papers.
4. **Annotate** — coordinator splits batches; agents write `annotations/<stem>.json` from manifest (one agent per batch); `source` = manifest `path`; confidence ∈ high|medium|low|uncertain|needs-review.
5. **Aggregate** — `build_exam_type_stats.py --validate` reads the manifest (optional `--papers-dir` is warning-only); stop if validation fails.
6. **Fill (A)** — `fill_type_analysis.py` then agents fill pages per `exam-census-quality.md` (parallel per type).
7. **Quality gate (B)** — run `review_type_analysis.py` once; revise ≤2 rounds or mark `quality: needs-review`. Gate also rejects bulky frontmatter、裸 `|` 拆表、面向用户文档中的英文残留。
8. **Multi-dim (C)** — `build_multi_dim_stats.py --overwrite` drafts under `analysis/`（中文表头/枚举显示）；完成后**再跑一次** `review_type_analysis.py` 专门检查 `analysis_needs_revision`；修订后再跑一次确认清空。

9. **Deep-dive (D)** — `init_exam_deep_dive.py` scaffolds 1–2 representative paper walkthroughs.
10. **Phase 5 Prep pack** — 四层资料包：L1 `备考指南.md`、L2 `题型解析/`（不重写正文）、L3 `公式总卡.md` + `答题模板速查.md`、L4 `考前1小时清单.md`。从频率统计与题型解析提取；证据不足写「证据不足，需人工补充」。
11. **Cross-val (E)** — `cross_validate_exam_census.py`：覆盖率 + prep pack 四层文件/链接/最低结构（prep pack 之后再跑）。

See `references/exam-census-workflow.md` and `references/exam-census-quality.md`.
