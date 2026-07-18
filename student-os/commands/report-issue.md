# report-issue

Intent: turn a local `student-os` feedback entry into a GitHub issue draft, and optionally publish it after confirmation.

Use when the user asks to:
- report a `student-os` problem to the developer
- create a GitHub issue from feedback
- publish feedback to GitHub

Default route:
- primary role: `feedback-operator`
- coordinator remains responsible for privacy review and final posting confirmation

Expected outputs:
- located or newly captured feedback path
- issue draft title/body/labels
- blocking privacy findings, if any
- privacy warnings
- completeness warnings
- draft-only result when privacy warnings are present unless the user explicitly confirms public posting
- mandatory cleanup before posting when blocking sensitive data is detected
- explicit confirmation before public posting
- stored GitHub issue metadata after publish

When the draft does not come from a local feedback entry, sanitize then post through the safe wrapper (do not use a bare `|` pipe into `gh` — held-back sanitization can still create an empty body without `pipefail`):

```bash
python scripts/sanitize_and_post.py -- \
  gh issue create --repo Gu-Heping/college-student-workflow -F - < draft.md
```

For PR reviews or comments, use the same wrapper (feed the draft on stdin):

```bash
python scripts/sanitize_and_post.py -- gh pr review <n> --comment -F - < draft.md
python scripts/sanitize_and_post.py -- gh issue comment <n> --body-file - < draft.md
```

- `--check-stdin` / `--stdin` on `prepare_github_issue.py` hold the draft back (non-zero exit, no stdout) when privacy warnings are present; re-run with `--allow-privacy-warnings` only after explicit user confirmation.
- Always pin `--repo Gu-Heping/college-student-workflow` so the issue lands on the student-os tracker instead of the student's current/private repo.

Do not call `gh issue create`, `gh pr review`, or `gh issue comment` directly on unsanitized text.
