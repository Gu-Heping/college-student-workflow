# import-file

Intent: bring an external file into the knowledge base.

Use when the user asks to:
- import a PDF, DOCX, XLSX, or PPTX
- convert a file into markdown
- create a repository-friendly reference draft from an external document

For a **whole materials folder**, prefer `commands/materials-convert.md` (`materials_convert.py` positional = source dir, not vault).

Default route:
- primary role: `file-operator`
- coordinator remains responsible for final summary

Before writing: inspect Git in the learning vault; keep originals; do not overwrite hand-written notes without confirmation.
