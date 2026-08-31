---
type: student-os-reference
scope: runtime-context
status: active
---

# Agent Runtime Context Boundary

Use this reference when a Student OS workflow depends on feedback, examples, prior analysis, or user-visible quality judgments.

## What The Runtime Agent Can Use

- the current user request and current conversation;
- files, images, screenshots, or paths the user explicitly provided;
- files the agent can actually read in the target learning vault;
- this installed `student-os` skill's docs, commands, references, templates, and scripts;
- tool outputs produced in the current workflow.

## What The Agent Must Not Assume

- hidden maintainer analysis or previous development-session conclusions;
- external transcript/log files unless the user provides them in the current task;
- private reference vaults or "good examples" unless the user points to readable files;
- GitHub PR/review/CI state unless the task asks for it and the agent fetches it;
- human verification of math/content correctness;
- that script `ok` or `issue_count: 0` means the material is readable or useful.

## Feedback And Quality Workflows

For workflow feedback, summarize the current conversation, visible artifacts, paths, and command results. Do not ask for an exported log as a normal prerequisite.

For exam-prep quality, the agent must read the generated Markdown as a student/teacher and edit it. Mechanical checks are tripwires only.

For examples from another vault, first read the files the user named and extract reusable patterns. Do not assume those patterns are already available to a fresh runtime agent.
