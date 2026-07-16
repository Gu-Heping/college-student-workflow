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

When the draft does not come from a local feedback entry, sanitize through:

```bash
python scripts/prepare_github_issue.py --stdin < draft.md | gh issue create -F -
```

Do not call `gh issue create` directly on unsanitized text.
