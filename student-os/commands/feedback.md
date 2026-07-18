# feedback

Intent: capture, triage, resolve, or summarize structured feedback about how `student-os` behaved.

Use when the user asks to:
- record a student-os problem
- save an unsatisfying result for later developer review
- prepare or publish a GitHub issue from feedback
- triage a stored feedback item
- resolve a shipped feedback item
- summarize recent workflow feedback
- mark feedback as resolved

Default route:
- primary role: `feedback-operator`
- coordinator remains responsible for the final summary

If the user wants a **public** GitHub Issue, continue with `commands/report-issue.md` and `references/github-feedback.md`. Always privacy-check before any `gh` call. If the check fails or raises a privacy warning, **stop at draft** — do not publish until content is redacted and the user explicitly confirms. Local `feedback/` entries alone are not public.
