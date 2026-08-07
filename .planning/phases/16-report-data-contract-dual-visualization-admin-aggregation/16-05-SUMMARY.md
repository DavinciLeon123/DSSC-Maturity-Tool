---
phase: 16-report-data-contract-dual-visualization-admin-aggregation
plan: 05
subsystem: report-rendering
tags: [svg, radar-chart, weasyprint, jinja2, flexbox, pdf, report-generator]

dependency_graph:
  requires:
    - phase: 16-01
      provides: "generate_radar_svg() and report.html, the shared server-rendered SVG/HTML consumed verbatim by both React (dangerouslySetInnerHTML) and WeasyPrint"
  provides:
    - "Position-aware radar axis text-anchor (end/start/middle derived from cos(angle)) + horizontally widened negative-min-x viewBox, fixing left-side label clipping identically in-app and in the PDF (G-16-1)"
    - "Single-level flex .priority-row (dot/name/score/label as direct siblings) with a fixed min-width + right-aligned .priority-score column, and a flattened single-flex-level .legend, fixing WeasyPrint's score misalignment and legend line-wrap (G-16-2)"
    - "Human visual confirmation on a real WeasyPrint render (Railway Integration deploy) and the in-app /report page, closing both 16-UAT.md gaps"
  affects: [17-test-coverage]

tech-stack:
  added: []
  patterns:
    - "Per-axis text-anchor derived from cos(angle) sign rather than a uniform value — the general fix for any n-axis polar-label layout, not hardcoded to 6 axes"
    - "Flex formatting contexts never nest in report.html — WeasyPrint 69.0 has documented justify-content/intrinsic-width bugs when a flex child is itself a flex container; the React PriorityRow's flat-sibling + fixed-width-column pattern is now mirrored server-side"

key-files:
  created: []
  modified:
    - backend/app/services/report_generator.py
    - backend/app/templates/report.html
    - backend/tests/services/test_report_generator.py

decisions:
  - "Epsilon-based cos(angle) classification (not axis-count-based) for text-anchor — keeps the fix correct for any future axis count, not just the current 6 categories"
  - "viewBox margin sized from the longest real category name at the 11px label font rather than a fixed padding constant, per the plan's explicit instruction not to hardcode n=6 assumptions"
  - "Score column uses fixed min-width + text-align: right (matching the already-proven React PriorityRow pattern) instead of relying on WeasyPrint's justify-content free-space distribution, which is the documented buggy path"
  - "Human verification (Task 3) performed against a real WeasyPrint render on the Railway Integration deployment via the open PR, not a local render — WeasyPrint's native libs are unavailable in the local sandbox on this Mac (recurring, pre-existing constraint noted in every prior Phase 13-16 plan)"

metrics:
  duration: 10min (resumed session — Tasks 1-2 code/tests executed and committed in a prior session; this session covers Task 3 checkpoint resolution + SUMMARY/state finalization)
  completed: 2026-07-28
status: complete
---

# Phase 16 Plan 05: Report-Rendering Gap Closure (G-16-1, G-16-2) Summary

**Fixed radar-chart left-side axis-label clipping via position-aware SVG text-anchor + widened viewBox, and fixed PDF-only priority-score misalignment/legend wrap by flattening report.html's nested flex contexts to a single level with a fixed-width right-aligned score column — both confirmed on a real WeasyPrint render.**

## Performance

- **Duration:** ~10 min this session (Tasks 1-2 were executed and committed 2026-07-28 07:27-07:30 in a prior session; this session resolves the approved Task 3 checkpoint and finalizes tracking artifacts)
- **Completed:** 2026-07-28
- **Tasks:** 3 (2 code tasks + 1 human-verify checkpoint)
- **Files modified:** 3 (`report_generator.py`, `report.html`, `test_report_generator.py`)

## Accomplishments

- **G-16-1 (radar axis-label clipping) fixed.** `generate_radar_svg()` in `backend/app/services/report_generator.py` no longer hardcodes `text-anchor="middle"` for every label. Each label's anchor is now derived from `cos(angle)` of its axis position: `middle` for the top/bottom axes (cos ≈ 0, within a small epsilon), `start` for right-side axes (cos > 0), `end` for left-side axes (cos < 0) — so long left-side labels ("Control over Data & Trust", "Value Creation") grow away from the SVG's left edge instead of being centered on an anchor point too close to it. The SVG `viewBox` was also widened horizontally (negative min-x, width now noticeably greater than height), with the margin sized to the longest real category name at the 11px label font rather than a fixed constant tied to the current 6-axis config. The existing `xml_escape()` call on category names (WR-05/T-16-05-01) was preserved unchanged. Since this single server-generated SVG string is consumed verbatim by both the React in-app view (`dangerouslySetInnerHTML`) and the WeasyPrint PDF template, this one fix resolves the clipping identically on both surfaces.
- **G-16-2 (PDF score misalignment + legend wrap) fixed.** `backend/app/templates/report.html`'s `.priority-row` no longer nests an inner flex wrapper span around the band dot and dimension name — the dot, name, score, and band label are now direct siblings of the single outer flex row, matching the already-correct React `PriorityRow` structure in `frontend/src/routes/_app/report.tsx`. `.priority-score` was given a fixed `min-width` plus `text-align: right`, forming a true flush-right column independent of WeasyPrint 69.0's documented `justify-content` free-space-distribution bug (rather than relying on it). The `.legend`/`.legend-item` structure was similarly flattened: each legend entry's dot is now a plain inline element beside its label text, with only the outer `.legend` remaining a flex/wrap container, fixing WeasyPrint's over-estimation of intrinsic item width that was forcing an early wrap to a second line. All existing visual styling (colors, dot appearance, font sizes, paddings, borders) was preserved — this was a structural flatten only, per the plan's explicit scope.
- **Regression tests added** to `backend/tests/services/test_report_generator.py`, driven from the real 6-category config: exactly 2/2/2 anchor distribution (middle/start/end) across the 6 axes, negative viewBox min-x with width > height, presence of the fixed-width + right-aligned score-column CSS, absence of the removed inner name-wrapper span in rendered priority rows (with names/scores still rendering correctly), and one legend entry per maturity band. All 12 tests in the file pass (`cd backend && uv run pytest tests/services/test_report_generator.py -x -q`).
- **Task 3 — human visual confirmation completed and approved.** The user deployed this branch via the open PR to the Railway Integration environment, generated a real WeasyPrint-rendered PDF, and compared it against the in-app `/report` page. All four checks in the plan's `<how-to-verify>` block passed: (1) radar axis labels fully visible on both surfaces including the two previously-clipped long left-side labels, (2) PDF priority-list scores align in a straight flush-right column regardless of dimension-name length, (3) the maturity-band legend fits on a single line at full page width, (4) no other visual regression (header, cards, radar polygon fill/colors, expert-help box) versus the previous render. The user's response: "All approved, please finish up this phase." G-16-1 and G-16-2 are both confirmed resolved.

## Task Commits

1. **Task 1: Position-aware radar axis labels + widened viewBox (G-16-1)** - `271a543` (fix)
2. **Task 2: Flatten priority-row and legend to single-level flex (G-16-2)** - `61ec7a4` (fix)
3. **Task 3: Human visual confirmation on a real WeasyPrint render (G-16-1, G-16-2)** - checkpoint, no code change; user approved all four checks ("All approved, please finish up this phase.")

**Plan metadata:** (this SUMMARY's own commit, made immediately after this file)

## Files Created/Modified

- `backend/app/services/report_generator.py` - `generate_radar_svg()` now derives per-label text-anchor from cos(angle) and widens the viewBox horizontally with a negative min-x
- `backend/app/templates/report.html` - `.priority-row`/`.priority-score`/`.legend`/`.legend-item` flattened to a single flex level with a fixed-width right-aligned score column
- `backend/tests/services/test_report_generator.py` - New regression tests for the anchor distribution/viewBox geometry and the flattened structural markers

## Verification

- `cd backend && uv run pytest tests/services/test_report_generator.py -x -q` — 12 passed (re-run this session to confirm the prior session's commits are still green before finalizing)
- Human visual confirmation on a real WeasyPrint PDF (Railway Integration deploy via open PR #7) + the in-app `/report` page — all four `<how-to-verify>` checks passed, user typed "approved"

## Decisions Made

- Epsilon-based `cos(angle)` classification for text-anchor selection (not an axis-count-based lookup) — stays correct if the number of maturity dimensions ever changes.
- viewBox margin computed from the longest real category name rather than a hardcoded padding value, per the plan's explicit instruction to avoid n=6-specific assumptions.
- Score column made a true fixed-width right-aligned column (matching the proven React pattern) instead of attempting to work around WeasyPrint's `justify-content` bug within a flex-distribution model.
- Human verification was performed against the Railway Integration deployment (via the already-open PR #7) rather than a local WeasyPrint render, since WeasyPrint's native libraries remain unavailable in the local sandbox on this Mac — consistent with every prior Phase 12-16 plan's noted local-environment gap.

## Deviations from Plan

None — plan executed exactly as written. Tasks 1 and 2 were completed and committed in a prior session; this session resolved the approved Task 3 checkpoint and finalized SUMMARY/STATE/ROADMAP tracking with no code changes.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- G-16-1 and G-16-2 are both closed. Phase 16's 4 core plans + this gap-closure plan (5/5) are now complete; the phase's overall success criteria (radar chart, priority list, single-source color banding, shared JSON contract for in-app + PDF, admin aggregation) are all satisfied and human-confirmed on a real WeasyPrint render.
- Phase 16 is ready for `/gsd-verify-work` / phase-completion sign-off, and Phase 17 (Test Coverage — New Scoring, Questionnaire & Visualization Logic + E2E) is unblocked to begin planning.
- The two commits (`271a543`, `61ec7a4`) are on `feature/dssc-real-questionnaire-content`, already pushed, and already part of the open PR #7 into `staging` — no additional PR work is needed for this plan's code changes.

---
*Phase: 16-report-data-contract-dual-visualization-admin-aggregation*
*Completed: 2026-07-28*

## Self-Check: PASSED

- `backend/app/services/report_generator.py` — FOUND
- `backend/app/templates/report.html` — FOUND
- `backend/tests/services/test_report_generator.py` — FOUND
- `.planning/phases/16-report-data-contract-dual-visualization-admin-aggregation/16-05-SUMMARY.md` — FOUND
- Commit `271a543` — FOUND in git log
- Commit `61ec7a4` — FOUND in git log
