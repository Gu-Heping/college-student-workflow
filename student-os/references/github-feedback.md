# GitHub Feedback

Use this reference when the user asks to report a `student-os` problem to the developer or publish it to GitHub Issues.

Natural language triggers:
- `report this to the developer`
- `把这个问题反馈到 GitHub`
- `create an issue for this`
- `publish this feedback`
- `open a GitHub issue from this feedback`

## Scope

This workflow extends the repository-native feedback loop into a developer-visible GitHub issue.

Expected flow:
1. Capture or locate the feedback item in `feedback/`
2. Prepare a structured issue draft
3. Run a privacy check
4. Ask for confirmation before public posting
5. Publish to GitHub only after explicit approval
6. Store the returned issue metadata back into the feedback entry

## Privacy-first rules

- Never post to a public issue without explicit confirmation.
- Never include private vault content, secrets, tokens, `.env` data, or raw course material without explicit user approval.
- Treat local file paths, private repository paths, and personal note excerpts as sensitive by default.
- When in doubt, redact first and mention the redaction in the issue body.

## Issue format

Default title:
- `<feedback_id>: <short feedback title>`

Default labels:
- `feedback`
- `feedback:<feedback_kind>`
- `severity:<severity>`

Default issue body sections:
- Feedback ID
- Installed Version
- Agent Runtime
- What Happened
- Expected Behavior
- Evidence
- Reproduction Steps
- Likely Area
- Severity
- Privacy Check

## Feedback linkage

Feedback frontmatter should store:
- `github_issue_url`
- `github_issue_number`
- `github_issue_status`
- `reported_to_github_at`

This lets the local feedback trail remain the source of truth even after a public issue exists.

## Developer loop closure

Once the issue is published:
1. Reference the GitHub issue from the relevant fix PR
2. Ship the fix and summarize the user-visible result in `CHANGELOG.md`
3. Update the feedback item through `resolve_feedback.py`
4. Set `github_issue_status` to reflect the public issue lifecycle when known

## Command path

Useful scripts:
- `scripts/prepare_github_issue.py` for issue draft generation
- `scripts/publish_github_issue.py` for optional `gh issue create` publishing

Default behavior:
- Prepare first
- Confirm second
- Publish third
