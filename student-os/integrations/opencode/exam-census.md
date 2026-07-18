# exam-census (OpenCode orchestration)

Use the installed **student-os** skill command `exam-census` and the scripts under `scripts/`.

## One-time adapter install into a vault

```bash
python <student-os>/scripts/install_exam_census_adapters.py /path/to/vault --platforms opencode
```

This copies this note to `.opencode/exam-census.md` in the vault.

## Invoke

Ask OpenCode (with student-os skill loaded):

> Run exam-census for course=<slug> exam-scope=<期中|midterm> on vault=<abs-path>

## Phase checklist

Follow `references/exam-census-workflow.md` and `commands/exam-census.md`:

1. `init_exam_census.py`
2. Taxonomy + parallel annotation batches
3. `build_exam_type_stats.py --validate --overwrite` (stop on failure)
4. `fill_type_analysis.py` → fill pages per `exam-census-quality.md`
5. `review_type_analysis.py` (≤2 revision rounds)
6. `build_multi_dim_stats.py --overwrite`
7. `init_exam_deep_dive.py --limit 2` + fill
8. Prep pack markdowns
9. `cross_validate_exam_census.py`

Operate only on the learning vault, never on the skill repository as the vault.
