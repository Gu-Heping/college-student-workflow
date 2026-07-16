# AGENTS.md

## Cursor Cloud specific instructions

`college-student-workflow` is a Python-only CLI/skill toolkit (the `student-os` skill). There are **no long-running services, servers, databases, or ports** — nothing to start or keep alive. Development is entirely running Python CLI scripts and the smoke-test suite.

- Runtimes: Python 3 (system `python3`) + `git` are the only required dependencies for the core workflows. Both are preinstalled.
- Optional dependencies from `requirements.txt` (`pdfplumber`, `pypdf`, `python-docx`, `openpyxl`, `python-pptx`, `mineru-open-sdk`) are only needed for the document-import feature (`student-os/scripts/materials_convert.py`). The startup update script installs them.
- Lint/compile, test, and run commands are documented in `README.md` (see the "测试" / "日常怎么用" sections). Key ones:
  - Tests: `python scripts/run_smoke_tests.py` (self-contained; creates temp Git repos and uses fixtures under `examples/`).
  - Compile check: `python -m py_compile scripts/install_student_os.py scripts/run_smoke_tests.py student-os/scripts/update_student_os.py`.
- CLI scripts operate on a **separate target vault directory passed as an argument** (e.g. `python student-os/scripts/inspect_repo.py /path/to/vault`). Never run them against this repo itself as the vault.
- Gotchas:
  - `materials_convert.py` takes the source file/dir as its **only positional arg** (no vault arg); outputs are written beside the source as `<name>.<ext>.md` unless `--output-root` is given. Use `--method local` to force local converters and avoid the hosted MinerU API.
  - Hosted MinerU conversion (`--method api`) needs `MINERU_TOKEN`/`MINERU_API_TOKEN`; without it, conversion falls back to local converters.
  - Publishing feedback as GitHub Issues (`publish_github_issue.py`) needs an authenticated `gh` CLI; it degrades gracefully to a draft/shell-safe fallback when `gh` is absent.
