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

- Install the optional converter dependencies from the repository `requirements.txt` before running the import scripts (`pymupdf` is required for text-heavy PDF local extraction).
- Optional system binary: `pandoc` improves DOCX conversion; without it, auto mode falls back to `docx_to_md.py`.
- For higher-fidelity OCR and legacy Office parsing, configure a MinerU token and prefer `materials_convert.py --method auto` or `--method api`.
- Token lookup order: `--api-token` → `MINERU_TOKEN` / `MINERU_API_TOKEN` process env → skill-root `.env` → current-working-directory `.env`.
- Prefer a skill-local `.env` (copy from `.env.example`) so tokens stay out of shell history; never commit real `.env` files.
- `--method auto` probes each file (PDF text layer, DOCX/PPTX text vs images, legacy Office, images) and selects MinerU API (+OCR), PyMuPDF, pandoc, or local converters.
- Use `--probe-only` to preview routing without writing sidecars, and `--force-strategy` to override probing.
- MinerU API mode auto-splits PDFs above `--chunk-size` (default 200 pages), converts each chunk, and merges the markdown unless `--no-merge` is set.
- Use `--no-auto-split` when you want oversized PDFs to fail fast instead of chunking.

## `materials_convert.py` argument reminder

```bash
# CORRECT: positional = materials source (file or folder)
python scripts/materials_convert.py /path/to/materials --method auto

# WRONG: do not treat the vault path as the materials positional unless sources live there
# python scripts/materials_convert.py /path/to/vault   # only if converting files inside that tree on purpose
```

- This script does **not** take a separate vault argument.
- Sidecars are written beside sources by default; use `--output-root` to mirror elsewhere.
- After conversion, continue with course/review/planning workflows; use `--repair` or `repair_markdown_import.py` when imports need cleanup.
- When existing `.pdf.md` sidecars are missing YAML frontmatter, run `ensure_frontmatter.py` first (prefer `--dry-run`, then `--apply`) before exam-census or review workflows. It only prepends metadata, never overwrites existing frontmatter, and always reads/writes UTF-8.

```bash
# Preview which sidecars need frontmatter (default: no writes)
python student-os/scripts/ensure_frontmatter.py /path/to/papers --dry-run

# Apply after confirming the plan
python student-os/scripts/ensure_frontmatter.py /path/to/papers --apply
```

Agent one-liner:

```text
请检查这个目录下的 .pdf.md 文件是否缺少 YAML frontmatter。先 dry-run 列出会修改哪些文件，确认后再用 ensure_frontmatter.py 补齐；不要覆盖已有 frontmatter，必须使用 UTF-8。
```

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

## Archiving mixed review folders (Issue #52)

After converting papers or importing old exams into `courses/<course>/reviews/<exam-scope>/`, run the archive helper to keep the directory tidy:

```bash
python student-os/scripts/organize_reviews.py /path/to/vault \
  --course linear-algebra \
  --exam-scope 期中
```

The script classifies loose files into:

```text
reviews/<scope>/
├── 试卷/          # original PDF/DOCX/PPTX/etc.
├── 文本/          # .pdf.md and .raw.md sidecars
├── 归档/          # *-repair-summary.md metadata
└── README.md      # generated index with updated relative links
```

Add `--dry-run` to preview moves. The helper prefers `git mv` when files are tracked and falls back to `shutil.move` otherwise. It skips already-organized directories and never moves exam-census generated artifacts (`题型解析/`, `analysis/`, `真题精析/`, `备考指南.md`, etc.).

## Routing guidance

- If the result is a raw or lightly cleaned import, keep it in `references/` or course `references/`.
- If the result is meant to drive coursework, pass it to `course-tutor`.
- If the result is meant to become review material, pass it to `review-coach`.
- If the result is tabular progress, grade, or workload data, pass it to `planning-assistant`.
