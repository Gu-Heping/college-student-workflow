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
- turn the current failed or unsatisfying workflow into a feedback item

Default route:
- primary role: `feedback-operator`
- coordinator remains responsible for the final summary

If the user wants a **public** GitHub Issue, continue with `commands/report-issue.md` and `references/github-feedback.md`. Always privacy-check before any `gh` call. If the check fails or raises a privacy warning, **stop at draft** — do not publish until content is redacted and the user explicitly confirms. Local `feedback/` entries alone are not public.

When feedback comes from the active workflow, use the current conversation and visible artifacts as the source. Capture:

- the user's original correction or complaint;
- the workflow area;
- what the agent did wrong;
- what the tool or skill contract failed to prevent;
- the user-visible impact;
- related output paths or commands;
- a candidate improvement for the skill/tool.

Use `evidence_source_status: summarized` when the current conversation contains enough evidence. A GitHub issue is optional and requires the normal privacy-checked publish flow.
