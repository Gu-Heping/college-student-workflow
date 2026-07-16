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
- privacy warnings
- explicit confirmation before public posting
- stored GitHub issue metadata after publish
