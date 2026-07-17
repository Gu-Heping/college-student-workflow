# File Handler

Use this reference when the request starts from a PDF, DOCX, XLSX, or PPTX file instead of an existing markdown note.

## Goals

- Convert external files into repository-friendly markdown artifacts.
- Support mixed materials folders without forcing users to import one file at a time.
- Let imported markdown flow through an automatic conservative repair step when the user asks for cleanup.
- Keep imported artifacts traceable back to their source files.
- Prefer conservative transformations that preserve meaning over aggressive rewriting.
- Hand the imported result back to the main study/review/planning workflows.

## Runtime expectation

- Install the optional converter dependencies from the repository `requirements.txt` before running the import scripts.
- For higher-fidelity OCR and legacy Office parsing, configure a MinerU token and prefer `materials_convert.py --method api` or `--method auto`.
- Token lookup order: `--api-token` → `MINERU_TOKEN` / `MINERU_API_TOKEN` process env → skill-root `.env` → current-working-directory `.env`.
- Prefer a skill-local `.env` (copy from `.env.example`) so tokens stay out of shell history; never commit real `.env` files.
- MinerU API mode auto-splits PDFs above `--chunk-size` (default 200 pages), converts each chunk, and merges the markdown unless `--no-merge` is set.
- Use `--no-auto-split` when you want oversized PDFs to fail fast instead of chunking.

## Default landing zones

- Course-local source material:
  - `courses/<course>/references/`
  - `courses/<course>/notes/`
  - `courses/<course>/reviews/` only after explicit review distillation

- Global imports:
  - `references/imports/raw/`
  - `references/imports/repaired/`
  - `references/textbooks/`
  - `references/slides/`

## Shared metadata

Imported artifacts should prefer these optional fields:

```yaml
source_file:
import_method:
repair_status:
derived_from_import:
```

## Routing guidance

- If the result is a raw or lightly cleaned import, keep it in `references/` or course `references/`.
- If the result is meant to drive coursework, pass it to `course-tutor`.
- If the result is meant to become review material, pass it to `review-coach`.
- If the result is tabular progress, grade, or workload data, pass it to `planning-assistant`.
