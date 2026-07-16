# materials-convert

Intent: batch-convert a folder of course materials into markdown sidecars or mirrored markdown outputs.

Use when the user asks to:
- convert a directory of PDFs, DOCX files, PPTX decks, or spreadsheets
- generate searchable markdown sidecars beside imported materials
- keep unsupported binaries discoverable with index notes instead of losing track of them

Recommended API mode:
- set `MINERU_TOKEN` or pass `--api-token`
- run `python scripts/materials_convert.py <folder> --method api --api-model vlm`
- use `--method auto` to prefer MinerU API when a token is present and fall back to local converters otherwise
- if the materials include scans, images, or legacy `.doc` / `.ppt` / `.xls` files, first check whether a MinerU token is already configured and prompt the user to add one when higher-fidelity parsing is likely to help

Default route:
- primary role: `file-operator`
- coordinator remains responsible for final summary
