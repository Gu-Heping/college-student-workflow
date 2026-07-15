# update

Intent: maintain the installed `student-os` skill safely.

Use when the user asks to:
- update or upgrade `student-os`
- refresh the installed skill
- reinstall `student-os`
- check whether a newer skill version is available

Default route:
- primary role: `coordinator`
- supporting role: skill-maintenance flow via `references/update-workflow.md`

Expected outputs:
- installed target path
- current commit and latest commit
- whether an update is available
- confirmation before applying updates
- validation result
- backup path and rollback command when files were replaced
