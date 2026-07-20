# Phase 1: Bugfixes + DSI/SP Heatmaps — Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Three targeted fixes:
1. **Bugfix**: Retaking the questionnaire and navigating to /report directly does not reflect updated answers in the heatmap.
2. **Bugfix**: Admin CSV export is missing the follow-up multi-select selections (the `followup_selections` JSONB column is not queried or written at all).
3. **Feature**: Split the admin `/admin/heatmap` page into two tabs — one for DSI initiatives, one for SP initiatives — filtered by participant type.

</domain>

<decisions>
## Implementation Decisions

### Bug #1 — Retake questionnaire / heatmap stale data

**User path confirmed:** User clicks through the wizard topic by topic (each "Next" click triggers `saveCurrentTopic()` — badge shows "Saved"). After going through, they navigate to `/report` directly via nav or dashboard — they do **not** use the Finish → completion screen → "Generate heatmap" button path.

**Two candidate root causes to investigate (researcher must confirm which):**

- **Root cause A — TanStack Router component cache**: The `/report` page may be cached by TanStack Router. When the user returns to `/report` after visiting `/questionnaire`, the old component instance is reused and `useEffect([initiativeId])` doesn't re-fire → the stale `data` state is shown. The `initiativeId` doesn't change (same number), so the second `useEffect` never re-runs.

- **Root cause B — Last topic not saved on nav-away**: The wizard only calls `saveCurrentTopic()` when the user clicks "Next" or "Back". If the user changes an answer on the **last topic they were viewing**, then navigates away via the nav bar instead of clicking "Next", those changes are never written to DB. The /report page fetches fresh from DB — but the last topic's edits weren't there.

**Fix approach (depends on root cause):**
- If Root cause A: add a `key` prop or `loaderDeps` to the `/report` route to force remount on navigation, OR change the useEffect to not depend on `initiativeId` staying the same (add a timestamp/version dep that changes on mount).
- If Root cause B: add a "save-on-nav-away" guard to the wizard (e.g., `useEffect` cleanup, `beforeunload` equivalent, or a route `beforeLoad` hook that triggers save).
- Researcher must confirm which applies by inspecting TanStack Router route config and the wizard's save triggers.

**Do NOT assume a specific fix** — researcher confirms, planner creates tasks.

### Bug #2 — CSV missing follow-up selections

**What's missing:** The SQL query in `GET /admin/export` selects `qa.followup_other` but never selects `qa.followup_selections` (the JSONB column). It is absent from: the SQL SELECT clause, the header row, and the writer.writerow() call.

**Format decision:** Add `followup_selections` as a **new column between `answer_value` and `followup_other`**, formatted as a **semicolon-separated string** (e.g. `"Option A; Option B"`). This is readable in Excel without JSON parsing.

**Do NOT touch the `followup_other` column** — it already works correctly.

**New header row:**
```
user_email, initiative_name, participant_type, initiative_status,
question_id, mami_code, answer_value, followup_selections, followup_other
```

**Empty value:** If `followup_selections` is NULL or empty array → write empty string `""`.

### Feature — DSI/SP split admin heatmap

**Backend:** Add optional `?type=dsi` or `?type=sp` query param to the existing `GET /admin/heatmap` endpoint. When present, filter the SQL aggregation `WHERE i.participant_type = :type`. When absent, keep existing behaviour (all types). No new endpoint — one param change.

**Frontend — admin.heatmap.tsx:**
- Wrap the existing heatmap in antd `Tabs` (already used in `admin.index.tsx`) with two tabs:
  - Tab 1: `"Aggregated Interoperability Heatmap for DSI's"` — fetches `/admin/heatmap?type=dsi`
  - Tab 2: `"Aggregated Interoperability Heatmap for SP's"` — fetches `/admin/heatmap?type=sp`
- Each tab fetches independently (lazy: only fetch when tab is first activated)
- Page title stays `"Aggregated Interoperability Heatmap"` (unchanged)

**Footer text per tab:**
- DSI tab: `Based on X submitted DSI initiative(s).`
- SP tab: `Based on X submitted Service Provider initiative(s).`

**Existing heatmap matrix component** (`CountPill`, grid layout, category/topic structure) is reused as-is for both tabs — no visual redesign.

### Claude's Discretion

- TanStack Router cache fix implementation detail (key prop vs loaderDeps vs useEffect refactor)
- Whether to fetch both tabs eagerly on load or lazily on first tab activation
- Exact Python query param typing (`Optional[str]` or `Literal["dsi", "sp"]`)

</decisions>

<specifics>
## Specific Ideas

- Bug #2 fix is purely additive: add one column to SQL SELECT, one entry to the header writerow, one entry to the data writerow. Nothing else changes.
- For the heatmap tabs: the existing `AdminHeatmapPage` component in `admin.heatmap.tsx` can be split into a shared `HeatmapGrid` presentational component + two data-fetching wrappers, one per tab.
- The SP tab uses "Service Provider initiatives" (spelled out), not "SP initiatives."

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets

- `admin.heatmap.tsx` — `CountPill` component, grid layout, `CATEGORY_LABELS`, `DIMENSION_LABELS`, full heatmap rendering → extract as shared component for two tabs
- `admin.index.tsx` — antd `Tabs` already imported and used with `items` prop (v6 API) → copy pattern
- `AdminHeatmapResponse` interface in `admin.heatmap.tsx` — already matches what backend returns; will work with filtered data too

### Established Patterns

- Backend: `?type=dsi|sp` query param added as `Optional[str] = None` FastAPI param; used in SQL WHERE clause
- Backend: raw SQL pattern (`session.execute(text(...))`) — follow existing admin.py style
- Frontend: lazy data fetch pattern — `useState(null)` + `useEffect` that fires on tab change → matches existing `/report` page two-step fetch pattern
- CSV export: `io.StringIO` + `csv.writer` streaming — existing pattern; just add one column

### Integration Points

- `GET /admin/heatmap` in `backend/app/api/v1/admin.py` — add `participant_type: Optional[str] = None` param, filter SQL accordingly
- `admin.heatmap.tsx` — add `Tabs` from antd, extract rendering into shared component, add two fetch states
- `admin.py export_dataset` — SQL: add `qa.followup_selections` to SELECT; header row + writerow: add column

### Key Bug Context

- `/report` page uses TWO chained useEffects: `useEffect([], [])` fetches initiative id → `useEffect([], [initiativeId])` fetches report data. If component is cached (not remounted), second useEffect only re-fires if `initiativeId` changes (it won't — same user, same initiative).
- `saveCurrentTopic()` in WizardPage only fires on "Next" / "Back" click — no save on nav-away.
- Questionnaire upsert endpoint has NO `submitted` status guard — retake saves work.

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-bugfix-retake-questionnaire-save-csv-missing-follow-up-selections-separate-dsi-sp-aggregated-heatmaps*
*Context gathered: 2026-03-15*
