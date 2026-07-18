<!-- student-os exam-census — paste/merge into .github/copilot-instructions.md -->

## exam-census (student-os)

When the user asks for past-paper census, 题型频率, midterm/final prep packs, or exam-census:

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
