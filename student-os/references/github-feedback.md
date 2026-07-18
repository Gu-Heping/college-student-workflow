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
3. Run a privacy check and completeness check
4. If blocking sensitive data exists, stop at draft output and require cleanup before any public posting
5. If only privacy warnings exist, stop at draft output unless the user explicitly confirms public posting
5. Ask for confirmation before public posting
6. Publish to GitHub only after explicit approval
6. Store the returned issue metadata back into the feedback entry

## Privacy-first rules

- Never post to a public issue without explicit confirmation.
- Never include private vault content, secrets, tokens, `.env` data, or raw course material without explicit user approval.
- Treat local file paths, private repository paths, and personal note excerpts as sensitive by default.
- When in doubt, redact first and mention the redaction in the issue body.
- Treat JWTs, secret-like key/value assignments, and phone-number-like personal data as blocking findings that must be removed before publication.
- If privacy warnings are present, default to draft-only output and require an explicit override such as `--allow-privacy-warnings` before publishing.

## Issue format

Default title:
- `<feedback_id>: <short feedback title>`

Default labels:
- `feedback`
- `feedback:<feedback_kind>`
- `severity:<severity>`

Label fallback:
- Prefer existing repository labels only.
- If the target repository does not already contain `feedback`, `feedback:*`, or `severity:*`, publish without those labels rather than failing the issue creation flow.

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
- `scripts/prepare_github_issue.py` for issue draft generation and stdin sanitization
- `scripts/sanitize_and_post.py` for sanitize-then-post (safe wrapper around `gh`)
- `scripts/publish_github_issue.py` for optional `gh issue create` publishing
  - default behavior: refuse direct publish when privacy warnings exist
  - use `--allow-privacy-warnings` only after explicit user confirmation

### Standalone sanitize (any GitHub body)

Use `--stdin` / `--check-stdin` for issue drafts, PR reviews, issue comments, and comment edits:

```bash
# Pre-flight check (non-zero on blockers OR warnings; no rewrite)
python scripts/prepare_github_issue.py --check-stdin --check-only < draft.md

# Emit sanitized text (held back on warnings unless overridden)
python scripts/prepare_github_issue.py --check-stdin < draft.md
python scripts/prepare_github_issue.py --stdin --stdin-format json < payload.json
```

- `--stdin` / `--check-stdin` read arbitrary text, print privacy `BLOCK:` / `WARN:` lines to stderr, and write sanitized text to stdout
- blockers and warnings hold the draft back (non-zero exit, **no stdout**); pass `--allow-privacy-warnings` only after explicit user confirmation to emit the sanitized draft
- `--check-only` reports findings without rewriting; exits non-zero on blockers or warnings
- `--stdin-format json` accepts `gh`-style JSON payloads that include `body` (and optional `title`) fields; both are scanned and the sanitized result is emitted as a JSON object when a title is present

### Safe post wrapper (preferred)

Do **not** rely on bare shell pipes such as `prepare ... | gh ...`. Without `set -o pipefail`, a held-back sanitize step still leaves `gh` running with an empty body (this created empty issues such as #40). Prefer `sanitize_and_post.py`, which only invokes the follow-up command when sanitization succeeds:

```bash
# Issue create
python scripts/sanitize_and_post.py --allow-privacy-warnings -- \
  gh issue create --repo Gu-Heping/college-student-workflow -F -

# PR review comment
python scripts/sanitize_and_post.py -- \
  gh pr review 39 --comment -F -

# Issue comment
python scripts/sanitize_and_post.py -- \
  gh issue comment 40 --body-file -

# Edit an existing comment (body via stdin to gh api)
python scripts/sanitize_and_post.py -- \
  gh api -X PATCH /repos/Gu-Heping/college-student-workflow/issues/comments/COMMENT_ID \
  -F body=@-

# Sanitize-only (same hold-back rules; no gh invocation)
python scripts/sanitize_and_post.py --check < draft.md
```

Feed draft text on stdin (or redirect a file). Always pin `--repo Gu-Heping/college-student-workflow` on issue create so drafts land on the student-os tracker, not the student's current/private repo.

Default behavior:
- Prepare first
- Confirm second
- Publish third
