# XLSX Workflow

Use this reference for spreadsheets such as grade sheets, progress trackers, and schedules.

## Common goals

- summarize one or more worksheets into markdown
- extract compact tables for planning or dashboard use
- turn spreadsheet contents into readable repository artifacts

## Output preference

- compact worksheet summary -> `templates/imported-table-summary.md`
- planning or dashboard material -> pass result to `planning-assistant`

## Handling rules

- include worksheet names
- preserve headers
- keep large tables truncated with a note when needed
- avoid pretending formulas were evaluated unless the workbook already stores values
