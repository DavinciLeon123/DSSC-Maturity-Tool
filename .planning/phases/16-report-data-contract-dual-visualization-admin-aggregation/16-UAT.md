---
status: complete
phase: 16-report-data-contract-dual-visualization-admin-aggregation
source: [16-VERIFICATION.md]
started: 2026-07-27T20:45:00Z
updated: 2026-07-28T05:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. WeasyPrint PDF radar/priority-list legibility (RPRT-04 backstop)
expected: Trigger `POST /initiatives/{id}/report/mail` or `GET /initiatives/{id}/report/pdf` against a real submitted assessment via CI/Docker or the deployed Integration environment (WeasyPrint's native libs are unavailable on this local Mac), open the resulting PDF, and compare it against the same assessment's in-app `/report` page. Expected: the radar chart and priority list render identically to the in-app view — correct band colors, no clipped/overlapping text, no missing polygon fill.
result: pass
reported: "Originally reported as clipped ('The text is cut-off in both the browser and the PDF report...'), severity major. Fixed by gap-closure plan 16-05 (G-16-1: position-aware text-anchor + widened SVG viewBox in generate_radar_svg()). Re-verified on a real WeasyPrint render via the Railway Integration deployment (PR #7): all axis labels fully visible on both surfaces, no clipping. User confirmed: 'All approved, please finish up this phase.'"
severity: major
resolved_by: 16-05-PLAN.md (gap_id G-16-1)

### 2. Long dimension-name wrapping in the priority list (RPRT-02/UI-SPEC backstop)
expected: Open the in-app `/report` page for an assessment and visually confirm the "Control over Data & Trust" priority-list row wraps its name onto a second line at normal viewport widths, rather than truncating or breaking the card layout. `white-space: normal` is confirmed present in the CSS; actual rendered wrap was not visually inspected.
result: pass
reported: "Browser wrap confirmed correct; a separate PDF-only issue was found instead (scores misaligned, legend wrapping early), severity major. Fixed by gap-closure plan 16-05 (G-16-2: flattened nested-flex .priority-row/.legend in report.html to a single flex level with a fixed-width right-aligned score column). Re-verified on a real WeasyPrint render via the Railway Integration deployment (PR #7): PDF scores align flush-right, legend fits on one line. User confirmed: 'All approved, please finish up this phase.'"
severity: major
resolved_by: 16-05-PLAN.md (gap_id G-16-2)

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-16-1
  truth: "The radar chart's axis labels render fully visible with no clipped or overlapping text, matching between in-app view and PDF export"
  status: resolved
  resolved_by: 16-05-PLAN.md
  resolved_at: 2026-07-28
  reason: "User reported: The text is cut-off in both the browser and the PDF report. Screenshot shows the left-side axis labels ('Value Creation' and 'Control over Data & Trust') clipped at the chart's left edge — the leading characters are cut off."
  severity: major
  test: 1
  root_cause: "generate_radar_svg() in backend/app/services/report_generator.py hardcodes text-anchor=\"middle\" for every axis label regardless of position. Left-side labels (index 4 'Control over Data & Trust', index 5 'Value Creation') get centered on an anchor point ~36 units from the viewBox's left edge (viewBox=\"0 0 320 320\"), but their rendered text width (~157/~91 units) far exceeds that margin, so the leading characters fall outside 0..320 and are clipped by the SVG's own viewBox — independent of any parent container CSS. The SVG is generated once server-side and reused verbatim by both the React in-app view (dangerouslySetInnerHTML) and the WeasyPrint PDF template, which is why the clipping is identical in both."
  artifacts:
    - path: "backend/app/services/report_generator.py"
      issue: "generate_radar_svg() (lines ~152-174): uniform text-anchor=\"middle\" for all labels; insufficient viewBox margin for long left-side labels"
    - path: "frontend/src/routes/_app/report.tsx"
      issue: "line ~267: consumes the shared SVG verbatim — confirms shared root cause, not independently buggy"
    - path: "backend/app/templates/report.html"
      issue: "lines 43,58-59,147: .card { overflow: hidden } is a secondary/compounding factor, not the root cause"
  missing:
    - "Compute text-anchor per label based on cos(angle) sign: \"end\" for left-side labels, \"start\" for right-side labels, \"middle\" only for top/bottom axes (i=0, i=3)"
    - "Widen the SVG viewBox horizontally (e.g. viewBox=\"-40 0 400 320\") to give long labels breathing room even with corrected anchors"
  debug_session: ".planning/debug/radar-chart-label-clip.md"

- gap_id: G-16-2
  truth: "Priority-area score values align consistently in a column in the PDF report, and the legend fits on one line at full page width, matching the in-app view"
  status: resolved
  resolved_by: 16-05-PLAN.md
  resolved_at: 2026-07-28
  reason: "User reported: That works correctly in the browser, in the PDF report however, the scores don't align due to the text behind it. Maybe you can divide that into columns to make sure it aligns. Also, the legenda beneath also uses a second line while that isn't neccessary if you use the full pagewidth."
  severity: major
  test: 2
  root_cause: "backend/app/templates/report.html nests display:flex containers inside other display:flex containers in two places: .priority-name (flex) inside .priority-row (flex), and .legend-item (flex) inside .legend (flex, flex-wrap:wrap). WeasyPrint 69.0 (pinned in backend/uv.lock) has long-standing open upstream bugs where justify-content free-space distribution and intrinsic/min-content width calculation both break when a child is itself a flex formatting context (Kozea/WeasyPrint #673, #1171, #2479, #1208). This makes .priority-row's justify-content: space-between track the rendered width of the preceding .priority-name text instead of pushing the score flush right, and makes WeasyPrint over-estimate .legend-item's width, wrapping the third legend item early despite available page width. The working React version never nests flex-in-flex (band-dot is a plain sibling at the outer flex level) and additionally uses a fixed minWidth + textAlign: right on the score column, which is why it renders correctly in browsers but breaks in WeasyPrint."
  artifacts:
    - path: "backend/app/templates/report.html"
      issue: "lines 61-109: .priority-row/.priority-name nest flex-in-flex, breaking WeasyPrint's justify-content: space-between"
    - path: "backend/app/templates/report.html"
      issue: "lines 156-176: .legend/.legend-item nest flex-in-flex, causing WeasyPrint to over-estimate item width and wrap early"
    - path: "frontend/src/routes/_app/report.tsx"
      issue: "lines 30-93 (PriorityRow): reference for the non-nested, WeasyPrint-safe structural pattern already proven to work (fixed min-width + text-align: right on the score column, dot as flat sibling)"
  missing:
    - "Flatten .priority-row to a single flex level: dot, name, score, and label as direct siblings; give .priority-score a fixed min-width + text-align: right so it forms a true column independent of flex-distribution correctness"
    - "Flatten .legend-item similarly: render the dot as a plain inline element beside text rather than its own flex child, keeping only the outer .legend as flex/wrap"
    - "Visual confirmation in CI/deploy (WeasyPrint's system libs aren't available in the local sandbox, so this diagnosis is code/structure-based, matched against documented unresolved WeasyPrint issues, not an empirical render)"
  debug_session: ".planning/debug/pdf-priority-align.md"
