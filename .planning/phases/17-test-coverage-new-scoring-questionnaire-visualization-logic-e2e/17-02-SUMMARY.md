---
phase: 17-test-coverage-new-scoring-questionnaire-visualization-logic-e2e
plan: 02
subsystem: frontend
tags: [test-coverage, vitest, fake-timers, react-testing-library]
type: execute
dependencies:
  requires: []
  provides: [TEST-02]
  affects: [frontend test coverage]
duration_minutes: 45
completed: "2026-08-07T07:35:00Z"
tech_stack:
  added: [Vitest fake timers, RTL act(), mock resolution chains]
  patterns: [vi.mock with chained mockResolvedValueOnce/mockRejectedValueOnce, fake-timer microtask flushing, data-driven SVG assertions]
key_files:
  created:
    - frontend/src/routes/_app/report.test.tsx
    - frontend/src/hooks/useDebouncedSave.test.ts
  modified:
    - frontend/src/routes/_app/report.tsx (added export ReportPage)
decisions:
  - Use vi.mock() with manual setup rather than MSW for small-scale frontend testing
  - Fake timers for useDebouncedSave: simulate debounce/retry delays instantly, not real waits
  - Data-driven DOM assertions for radar SVG: check attributes/text-content only, not full SVG markup
  - Use act(async { advanceTimersByTime(...) + await Promise.resolve() }) to ensure microtasks flush after timer advancement
---

# Phase 17 Plan 02: Frontend Test Coverage (Wizard Save & Report Rendering) Summary

Close TEST-02 requirement: add Vitest + React Testing Library coverage for the wizard's debounced-save state machine and the report page's radar/priority-list rendering, with zero mocking of chart libraries (none exist in this codebase) and deterministic fake-timer tests.

## What Was Built

### Task 1: Report Page Export + Rendering Tests

1. **Export ReportPage** (`frontend/src/routes/_app/report.tsx`):
   - Changed `function ReportPage()` to `export function ReportPage()` to match the existing TopNav.tsx precedent for test-isolation exports.
   - One-line change; routing behavior unchanged (TanStack Router only requires `Route` export).

2. **Create report.test.tsx** (`frontend/src/routes/_app/report.test.tsx`):
   - Two data-driven test cases:
     - **Happy path:** Mock `fetchReportData` to return a fixture ReportContract with radar SVG + 2 priority list items. Assert:
       - SVG polygon `fill` attribute matches the fixture color
       - SVG text "Dimension A" is in the DOM
       - Both priority list item names/labels/scores are present
       - Formatted scores (via `.toFixed(2)`) render correctly
       - Color dots' inline `background` style match each item's `band_color`
       - Initiative name is displayed
     - **Error path:** Mock `fetchReportData` to reject. Assert error message ("couldn't load this report") and Retry button are rendered.
   - Mocking strategy: `vi.mock()` on reports/api/@tanstack/react-router (matches TopNav.test.tsx conventions); no chart-library mocking needed (none exists).
   - Uses `await waitFor()` to wait for component's `useEffect` → `fetchReportData` promise resolution before asserting.

### Task 2: useDebouncedSave Fake-Timer Tests

Create `frontend/src/hooks/useDebouncedSave.test.ts` with five deterministic test cases using `vi.useFakeTimers()`:

1. **Debounce timing (Test 1):** Schedule → advance 500ms (early, before debounce fires) → assert no call; advance 1000ms more (to 1500ms total) → assert `saveAnswer` called exactly once with correct payload, `onStateChange` progression is "saving" → "saved".

2. **Debounce reset / last-write-wins (Test 2):** Schedule score 2, advance 500ms, schedule score 4 (same question, resets debounce timer), advance 1500ms from the second schedule → assert `saveAnswer` called once total with score 4 (the later value), never with score 2.

3. **Retry-then-succeed (Test 3):** Mock `saveAnswer` to reject twice, then resolve. Schedule, advance 1500ms (first attempt fails), advance 1000ms (second attempt fails after backoff), advance 2000ms (third attempt succeeds) → assert `onStateChange` calls include "saving", "retrying", "saved"; `saveAnswer` called 3 times total.

4. **Terminal failed state (Test 4):** Mock `saveAnswer` to always reject. Schedule, advance 1500ms + 1000ms + 2000ms + 4000ms (covering the full 1 initial + 3 retry backoffs) → assert `onStateChange` includes "failed" state; `saveAnswer` called 4 times total (no more retries after terminal state).

5. **Rate-limit non-escalation (Test 5):** Mock `saveAnswer` to reject with `{ response: { status: 429 } }`. Schedule, advance 1500ms only (no backoff needed) → assert `onStateChange` called with "rate-limited", `saveAnswer` called exactly once (429 short-circuits, no retry consumed).

**Test infrastructure details:**
- `beforeEach(() => vi.useFakeTimers())`, `afterEach(() => vi.useRealTimers())`
- Every timer advancement wrapped in `await act(async () => { vi.advanceTimersByTime(...); await Promise.resolve(); })` to ensure microtasks (Promise chains) flush before assertions (addresses RESEARCH Pitfall 4)
- Mock setup uses chained `.mockRejectedValueOnce()` / `.mockResolvedValueOnce()` to queue up rejection/resolution per call
- `onStateChange` tracked via `vi.fn()` and assertions inspect `mock.calls` array

## Verification

All quality gates pass:

```bash
cd frontend && npx vitest run
# Test Files: 3 passed (3)
# Tests: 8 passed (8)
#   - TopNav.test.tsx: 1 test
#   - report.test.tsx: 2 tests
#   - useDebouncedSave.test.ts: 5 tests

npx tsc -b --noEmit
# No errors

npx eslint .
# No errors
```

## Success Criteria Met

- ✅ `ReportPage` exported from `frontend/src/routes/_app/report.tsx`
- ✅ `frontend/src/routes/_app/report.test.tsx` exists with two tests covering happy-path rendering + error-path retry button
- ✅ Radar SVG assertions check attributes/text-content only (no chart-library mocking, no full-markup snapshots)
- ✅ Priority list rows rendered with correct names, labels, scores (via `.toFixed(2)`), and color dots
- ✅ `frontend/src/hooks/useDebouncedSave.test.ts` covers all 5 behaviors (debounce, reset, retry+succeed, exhausted retries, 429 rate-limit)
- ✅ All 5 tests use `vi.useFakeTimers()` and `act()` for deterministic, instant-running tests (no real waits)
- ✅ TEST-02 requirement satisfied: wizard save/state-machine logic and report rendering are covered, regression-safe

## Deviations from Plan

None — plan executed exactly as written. All tasks completed, all success criteria met, all tests passing.

## Decisions Made

1. **Mock rejection chains:** Used chained `.mockRejectedValueOnce()` / `.mockResolvedValueOnce()` rather than single `.mockRejectedValue()` with side-effect re-mocking, to clearly express each call's expected outcome in sequence.

2. **Color assertion format:** SVG colors in jsdom are converted to RGB format (e.g., `#ff9900` → `rgb(255, 153, 0)`). Assertions check for the computed RGB value rather than the original hex.

3. **Microtask flushing pattern:** Every `vi.advanceTimersByTime()` inside `act()` is followed by `await Promise.resolve()` to ensure saveAnswer's Promise chain completes before state checks, matching the established pattern from RESEARCH.md Pitfall 4.

## Key Statistics

- **Commits:** 2 (one per task)
  - `5d891f6`: export ReportPage + report.test.tsx
  - `724c9f9`: useDebouncedSave.test.ts
- **Test files created:** 2 (report.test.tsx, useDebouncedSave.test.ts)
- **Tests added:** 7 new tests (2 for report, 5 for useDebouncedSave)
- **Total test suite:** 8 tests across 3 files (3 files: TopNav.test.tsx + 2 new)
- **Quality gate status:** ✅ tsc, ✅ eslint, ✅ vitest run

---

**Phase 17, Plan 02 COMPLETE** — TEST-02 requirement closed. Frontend coverage for critical save/render logic in place, deterministic and regression-safe via fake timers and mocked dependencies.
