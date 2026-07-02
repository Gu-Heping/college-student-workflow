# PDF Workflow

Use this reference for importing PDF files into `student-os`.

## Two modes

### Generic mode

Use when the goal is:
- quick text extraction
- page-level probing
- partial import by page range
- building a simple markdown draft for later cleanup

### MinerU-style mode

Use when the goal is:
- textbook or lecture note conversion into markdown
- a stronger import + cleanup path
- preserving structure well enough for later study or review work

MinerU-style mode in `student-os` means:
- generate a markdown import draft
- run conservative markdown repair
- produce a repair summary
- store raw and repaired outputs separately when helpful

## Output expectations

- Raw imports should usually land in `references/imports/raw/`.
- Repaired imports should usually land in `references/imports/repaired/`.
- Course-targeted imports may land in `courses/<course>/references/`.

## Safety rules

- Do not silently rewrite content meaning.
- Keep page-level separation visible when the structure is uncertain.
- Preserve image placeholders or links instead of dropping them.
- Emit a repair summary whenever imported markdown is modified.
