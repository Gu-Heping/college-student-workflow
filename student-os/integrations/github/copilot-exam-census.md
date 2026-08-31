<!-- student-os exam-census — paste/merge into .github/copilot-instructions.md -->

## exam-census (student-os)

When the user explicitly asks for past-paper census, 题型频率, or exam-census:

This is a legacy/auxiliary machine-census route. For high-quality study packs, tutoring handouts, or "整理历年卷 / 构建备考包", use Student OS AI-first exam prep instead.

1. Confirm the **learning vault** path (not this skill/repo as vault).
2. Use student-os scripts under the installed skill `scripts/` directory.
3. Follow phases in skill files `commands/exam-census.md` and `references/exam-census-workflow.md`.
4. Always run `build_exam_type_stats.py --validate` before synthesizing; stop on failure.
5. Fill type analyses to `references/exam-census-quality.md` (zero-foundation entry + method refs).
6. Finish with `cross_validate_exam_census.py`.

Install vault adapters:

```bash
python <student-os>/scripts/install_exam_census_adapters.py /path/to/vault --platforms github
```
