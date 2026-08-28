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

1. Inspect Git in the learning vault with compact, task-specific preflight before changing files. For import repair, prefer `group_git_changes.py --compact-json` over a full-vault hygiene inspect.
2. For low-risk Obsidian-visible render fixes, run one guarded direct repair first: `python student-os/scripts/repair_import_run.py <vault-or-folder> --json`. In DSH, prefer `student_os_repair_import_run` when available.
3. If direct run succeeds, inspect the returned target/diff summary and stop. If another defect appears, run a follow-up direct repair or proposal; do not edit the target sidecar by hand.
4. If direct run says the item is blocked, widened, semantic, or evidence-dependent, build the evidence queue with compact agent output: `python student-os/scripts/repair_import_queue.py <vault-or-folder> --write-queue --classify-evidence --compact-json --json`.
5. Generate a case for exactly one unverified `recommended_item` with `single_section_candidate: true`: `python student-os/scripts/repair_import_case.py --queue <queue.json> --queue-item <id> --evidence-mode auto --write-case --json`.
6. Compare the current sidecar, raw import excerpt, repair summary, paired paper/answer sidecar, and original source path. If the source evidence is unavailable, say so and keep the result unverified.
7. Write a proposal that explains the evidence, the intended section replacement, and remaining human-review risks.
8. Run `repair_import_review.py --proposal <proposal.md> --json`; fix the proposal when review reports blocking structural or Markdown/KaTeX issues.
9. Apply with `repair_import_apply.py --proposal <proposal.md> --require-review-pass --json`.

Operational guardrails:
- Do not generate cases in parallel.
- Direct run is allowed to write one local section, but it must review immediately and roll back on failure.
- If the compact queue says `single_section_candidate: false`, create a blocked case or choose a smaller item/section instead of rewriting the whole file.
- Use compact queue `recommended_item.case_argv` as the default next step. If `top_blocked_item` is present, use `next_repairable_item` or narrow the target folder instead of reading the full queue.
- For manual local render proposals, write a section replacement block with `student-os-section-replacement-start/end`; reserve full-file replacement for explicitly widened repairs.
- Do not write `.fixed` files or vault-local debug/trace/repair scripts.
- After apply, do not directly edit the target sidecar. If another defect appears, create a follow-up proposal, review it, and apply it.
- Do not read Student OS script source to interpret risk labels unless the script itself fails.
- When review fails, follow `failure_reason` and `recommended_next_action` from the JSON.
- Treat `unicode-escape` as readability-only and `math-dollar-unbalanced` as a low-confidence heuristic; prioritize localized `math-dollar-odd-line` and render-blocking `latex-left-right-unbalanced` items.
- If Obsidian or another Markdown preview shows literal TeX for an inline formula or inline matrix/array formula, treat that preview as the failure. Do not spend time proving raw bytes contain `\\`, and do not use KaTeX as a substitute for the user's preview target unless asked.
- Inline math delimiters cannot keep spaces just inside the dollar signs in Obsidian. Normalize `$ x = A^{-1}b $` to `$x = A^{-1}b$` without changing the formula body.
- For long inline `array` formulas, convert the local span to display math with opening and closing `$$` delimiters each alone on their own line. Forms such as `即 $$`, `设矩阵 $$`, or `$$，则` are render-blocking.
- For augmented matrices, prefer one structurally correct array such as `{ccc|cc}` and verify the column spec matches row cell counts.

Evidence modes:
- `text-only`: use current sidecar, raw import, repair summary, and paired paper/answer text. This is the default for non-vision models.
- `ocr-assisted`: first create a vault-local `.md` or `.txt` OCR evidence artifact, then bind it with `repair_import_case.py --evidence-mode ocr-assisted --ocr-evidence <path>`. Do not overwrite repaired markdown directly.
- `vision-assisted`: render only candidate PDF pages/crops for multimodal review. This is evidence grounding, not a duplicate OCR pass and not human verification.

AI can help locate and rewrite likely broken content, but only a human source check can mark `verify_status: verified`.
