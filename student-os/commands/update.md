# update

Intent: maintain the installed `student-os` skill safely.

Use when the user asks to:
- update or upgrade `student-os`
- refresh the installed skill
- reinstall `student-os`
- check whether a newer skill version is available
- update every installed copy across Codex / Claude Code / OpenCode / DSH

Default route:
- primary role: `coordinator`
- supporting role: skill-maintenance flow via `references/update-workflow.md`

Hard rule: update **only** the installed skill directory (user-scope or project-scope skill path). Do **not** modify vault notes/courses/feedback, re-scaffold notes, or treat the skill source checkout as the vault. Project-scope installs may live under the project’s `.codex/skills` / `.claude/skills` / `.opencode/skills`; that is still skill maintenance, not vault content editing.

Expected outputs:
- installed target path
- one target vs multi-target update mode
- current commit and latest commit
- whether an update is available
- confirmation before applying updates
- validation result
- backup path and rollback command when files were replaced
