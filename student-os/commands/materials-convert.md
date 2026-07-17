# materials-convert

Intent: batch-convert a folder of course materials into markdown sidecars or mirrored markdown outputs.

Use when the user asks to:
- convert a directory of PDFs, DOCX files, PPTX decks, or spreadsheets
- generate searchable markdown sidecars beside imported materials
- keep unsupported binaries discoverable with index notes instead of losing track of them
- run a conservative post-processing repair pass after conversion
- repair a batch of already-generated markdown imports without re-running extraction

Recommended API / auto mode:
- set `MINERU_TOKEN` in the environment, or put it in the skill-root / cwd `.env` (see `.env.example`), or pass `--api-token`
- `--method auto` (default) probes each file and routes to MinerU API (+OCR when scanned/image-heavy), PyMuPDF for text-heavy manuals, pandoc/`docx_to_md` for text DOCX, or local pptx/xlsx converters
- `--probe-only` prints the per-file strategy JSON without writing sidecars
- `--force-strategy ocr|mineru-api|pymupdf|pandoc|...` overrides probing for every input
- `--method api` / `--method local` still force a global backend
- run `python scripts/materials_convert.py <folder> --method api --api-model vlm` when you want MinerU for everything API-supported
- large PDFs over the MinerU page limit are auto-split into `<= --chunk-size` chunks (default 200), converted, and merged into one markdown sidecar
- use `--no-auto-split` to fail instead of chunking, `--chunk-size N` for v1/smaller limits, and `--no-merge` to keep per-chunk sidecars
- optional system `pandoc` improves DOCX quality; without it, auto falls back to `docx_to_md.py`
- install `pymupdf` from `requirements.txt` for the local text-manual PDF path

Repair mode:
- add `--repair` to run the conservative markdown repair step immediately after conversion
- add `--repair-only` to repair existing `.md` imports in place and emit `-repair-summary.md` files beside them

Default route:
- primary role: `file-operator`
- coordinator remains responsible for final summary
