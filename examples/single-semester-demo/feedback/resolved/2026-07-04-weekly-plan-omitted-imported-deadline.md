---
type: feedback
status: resolved
created: 2026-07-04
updated: 2026-07-04
feedback_id: "fb-20260704-weekly-plan-omitted-imported-deadline"
tags: [feedback, workflow]
feedback_kind: workflow
severity: high
reproducibility: always
source_context: "plan-week request after adding a linked homework task"
related_course: ""
related_artifacts: ["tasks/weekly/current.md", "tasks/deadlines/sample.md"]
related_roles: ["coordinator", "planning-assistant"]
fix_version: "0.7.0"
---

# Feedback - Weekly plan omitted imported deadline

## What Happened

- The generated weekly plan skipped a deadline that already existed in tasks/deadlines/.

## Expected Behavior

- Weekly plans should include near-term deadline tasks alongside inbox and review items.

## Why This Was Unsatisfying

- The user still has to manually inspect deadlines after asking for a full weekly plan.

## Likely Cause

- The planning workflow did not include imported deadline artifacts in the scan window.

## Suggested Improvement

- Expand planning scans to include imported deadline artifacts before sorting upcoming work.

## Developer Summary

- Planning scans need a regression check for imported or linked deadline artifacts.

## Evidence

- tasks/weekly/current.md and tasks/deadlines/sample.md

## Follow-up

- Triage status: resolved
- Next step: Verify once against a real imported-deadline workflow.

## Triage Notes

- Confirmed the issue belongs to planning ingestion rather than task creation.

## Resolution Summary

- Added planning regression coverage so imported deadlines appear in weekly plan summaries.

## Changelog Hint

- Weekly plans now preserve imported and linked deadline tasks in the upcoming-work scan.
