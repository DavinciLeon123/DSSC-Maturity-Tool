---
status: complete
phase: 16-report-data-contract-dual-visualization-admin-aggregation
source: [16-VERIFICATION.md]
started: 2026-07-27T20:45:00Z
updated: 2026-07-28T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. WeasyPrint PDF radar/priority-list legibility (RPRT-04 backstop)
expected: Trigger `POST /initiatives/{id}/report/mail` or `GET /initiatives/{id}/report/pdf` against a real submitted assessment via CI/Docker or the deployed Integration environment (WeasyPrint's native libs are unavailable on this local Mac), open the resulting PDF, and compare it against the same assessment's in-app `/report` page. Expected: the radar chart and priority list render identically to the in-app view — correct band colors, no clipped/overlapping text, no missing polygon fill.
result: issue
reported: "The text is cut-off in both the browser and the PDF report. Screenshot shows the left-side axis labels ('Value Creation' and 'Control over Data & Trust') clipped at the chart's left edge — the leading characters are cut off."
severity: major

### 2. Long dimension-name wrapping in the priority list (RPRT-02/UI-SPEC backstop)
expected: Open the in-app `/report` page for an assessment and visually confirm the "Control over Data & Trust" priority-list row wraps its name onto a second line at normal viewport widths, rather than truncating or breaking the card layout. `white-space: normal` is confirmed present in the CSS; actual rendered wrap was not visually inspected.
result: issue
reported: "That works correctly in the browser, in the PDF report however, the scores don't align due to the text behind it. Maybe you can divide that into columns to make sure it aligns. Also, the legenda beneath also uses a second line while that isn't neccessary if you use the full pagewidth."
severity: major

## Summary

total: 2
passed: 0
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-16-1
  truth: "The radar chart's axis labels render fully visible with no clipped or overlapping text, matching between in-app view and PDF export"
  status: failed
  reason: "User reported: The text is cut-off in both the browser and the PDF report. Screenshot shows the left-side axis labels ('Value Creation' and 'Control over Data & Trust') clipped at the chart's left edge — the leading characters are cut off."
  severity: major
  test: 1
  artifacts: []
  missing: []

- gap_id: G-16-2
  truth: "Priority-area score values align consistently in a column in the PDF report, and the legend fits on one line at full page width, matching the in-app view"
  status: failed
  reason: "User reported: That works correctly in the browser, in the PDF report however, the scores don't align due to the text behind it. Maybe you can divide that into columns to make sure it aligns. Also, the legenda beneath also uses a second line while that isn't neccessary if you use the full pagewidth."
  severity: major
  test: 2
  artifacts: []
  missing: []
