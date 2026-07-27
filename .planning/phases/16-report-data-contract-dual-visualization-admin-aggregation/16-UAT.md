---
status: testing
phase: 16-report-data-contract-dual-visualization-admin-aggregation
source: [16-VERIFICATION.md]
started: 2026-07-27T20:45:00Z
updated: 2026-07-27T20:45:00Z
---

## Current Test

number: 1
name: WeasyPrint PDF radar/priority-list legibility (RPRT-04 backstop)
expected: |
  The radar chart (polygon + 6 axis labels, including "Control over Data & Trust") and the
  priority list render identically to the in-app view — correct band colors, no clipped or
  overlapping text, no missing polygon fill.
awaiting: user response

## Tests

### 1. WeasyPrint PDF radar/priority-list legibility (RPRT-04 backstop)
expected: Trigger `POST /initiatives/{id}/report/mail` or `GET /initiatives/{id}/report/pdf` against a real submitted assessment via CI/Docker or the deployed Integration environment (WeasyPrint's native libs are unavailable on this local Mac), open the resulting PDF, and compare it against the same assessment's in-app `/report` page. Expected: the radar chart and priority list render identically to the in-app view — correct band colors, no clipped/overlapping text, no missing polygon fill.
result: [pending]

### 2. Long dimension-name wrapping in the priority list (RPRT-02/UI-SPEC backstop)
expected: Open the in-app `/report` page for an assessment and visually confirm the "Control over Data & Trust" priority-list row wraps its name onto a second line at normal viewport widths, rather than truncating or breaking the card layout. `white-space: normal` is confirmed present in the CSS; actual rendered wrap was not visually inspected.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
