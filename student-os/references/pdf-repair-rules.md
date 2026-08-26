# PDF Repair Rules

Use this reference after a PDF has been converted into markdown and needs cleanup.

## Repair goals

- Remove obvious layout residue without changing content meaning.
- Improve readability enough for course/reference/review workflows.
- Record what was changed.

## Common fixes

- remove isolated page labels such as `Page 12`
- collapse repeated blank lines
- normalize heading spacing such as `##Title` -> `## Title`
- trim trailing dot leaders or page-number residue in headings
- normalize broken bullet markers
- keep image links and placeholders intact

## Conservative policy

- If the text is ambiguous, prefer leaving it unchanged.
- If a formula, table, or OCR fragment cannot be confidently repaired, keep it and mention it in the repair summary.
- Never present repair output as if it were authoritative source material.
- Automatic repair writes `repair_status: auto-repaired` and `verify_status: unverified`; legacy `repair_status: repaired` is treated as unverified machine output.

## AI-assisted repair loop

Use this loop when the user asks for flexible cleanup or semantic reconstruction from imported sidecars:

1. Inspect Git in the learning vault before changing files.
2. Build the evidence queue: `python student-os/scripts/repair_import_queue.py <vault-or-folder> --write-queue --classify-evidence --json`.
3. Generate a case for one unverified queue item: `python student-os/scripts/repair_import_case.py --queue <queue.json> --queue-item <id> --evidence-mode auto --write-case --json`.
4. Compare the current sidecar, raw import excerpt, repair summary, paired paper/answer sidecar, and original source path. If the source evidence is unavailable, say so and keep the result unverified.
5. Write a proposal that explains the evidence, the intended full replacement, and remaining human-review risks.
6. Run `repair_import_review.py --proposal <proposal.md> --json`; fix the proposal when review reports blocking structural or Markdown/KaTeX issues.
7. Apply with `repair_import_apply.py --proposal <proposal.md> --require-review-pass --json`.

Evidence modes:
- `text-only`: use current sidecar, raw import, repair summary, and paired paper/answer text. This is the default for non-vision models.
- `ocr-assisted`: use OCR/import only to create better text evidence; do not overwrite repaired markdown directly.
- `vision-assisted`: render only candidate PDF pages/crops for multimodal review. This is evidence grounding, not a duplicate OCR pass and not human verification.

AI can help locate and rewrite likely broken content, but only a human source check can mark `verify_status: verified`.
