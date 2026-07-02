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
