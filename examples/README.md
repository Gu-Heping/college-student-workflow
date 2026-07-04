# Example Repositories

This directory contains generated example student knowledge repositories for `student-os`.

Current snapshots:

- `single-semester-demo/`
  A simple markdown-first course repository using `courses/<course>/`, plus triaged/resolved feedback examples, imported reference artifacts, and a developer-facing summary.
- `multi-semester-demo/`
  A semester-aware repository using `courses/<semester>/<course>/` and `semesters/<semester>/overview.md`.
- `legacy-layout-demo/`
  A lightweight legacy-style course folder without a generated `index.md`, kept to validate fallback discovery and indexing behavior.

These examples are generated from the real `student-os` scripts instead of being hand-maintained fixtures.

The single-semester snapshot now also demonstrates:

- overdue carryover, exam countdowns, inbox triage, and a linked weekly dashboard
- DOCX import into course references
- XLSX import into dashboard summaries
- PPTX import into slide summaries
- PDF generic import, repaired MinerU-style import, and repair summaries

To refresh them:

```bash
python scripts/run_smoke_tests.py --refresh-examples
```

To validate the workflows without overwriting the snapshots:

```bash
python scripts/run_smoke_tests.py
```
