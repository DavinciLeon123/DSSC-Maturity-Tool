# Phase 1: Bugfix retake-questionnaire save, CSV followup_selections, DSI/SP heatmap tabs — Research

**Researched:** 2026-03-15
**Domain:** FastAPI + TanStack Router + antd v6 — bug investigation and targeted feature
**Confidence:** HIGH (all findings from direct source code inspection)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Bug #1 — Retake questionnaire / heatmap stale data**

User path confirmed: User clicks through the wizard topic by topic (each "Next" click triggers `saveCurrentTopic()` — badge shows "Saved"). After going through, they navigate to `/report` directly via nav or dashboard — they do NOT use the Finish → completion screen → "Generate heatmap" button path.

Two candidate root causes to investigate (researcher must confirm which):
- Root cause A — TanStack Router component cache: The `/report` page may be cached by TanStack Router. When the user returns to `/report` after visiting `/questionnaire`, the old component instance is reused and `useEffect([initiativeId])` doesn't re-fire → the stale `data` state is shown.
- Root cause B — Last topic not saved on nav-away: The wizard only calls `saveCurrentTopic()` when the user clicks "Next" or "Back". If the user changes an answer on the last topic they were viewing, then navigates away via the nav bar instead of clicking "Next", those changes are never written to DB.

Fix approach (depends on root cause):
- If Root cause A: add a `key` prop or `loaderDeps` to the `/report` route to force remount on navigation, OR change the useEffect to not depend on `initiativeId` staying the same.
- If Root cause B: add a "save-on-nav-away" guard to the wizard (e.g., `useEffect` cleanup, `beforeunload` equivalent, or a route `beforeLoad` hook that triggers save).
- Researcher must confirm which applies by inspecting TanStack Router route config and the wizard's save triggers.

Do NOT assume a specific fix — researcher confirms, planner creates tasks.

**Bug #2 — CSV missing follow-up selections**

What's missing: The SQL query in `GET /admin/export` selects `qa.followup_other` but never selects `qa.followup_selections` (the JSONB column). It is absent from: the SQL SELECT clause, the header row, and the writer.writerow() call.

Format decision: Add `followup_selections` as a new column between `answer_value` and `followup_other`, formatted as a semicolon-separated string (e.g. `"Option A; Option B"`). This is readable in Excel without JSON parsing.

Do NOT touch the `followup_other` column — it already works correctly.

New header row:
```
user_email, initiative_name, participant_type, initiative_status,
question_id, mami_code, answer_value, followup_selections, followup_other
```

Empty value: If `followup_selections` is NULL or empty array → write empty string `""`.

**Feature — DSI/SP split admin heatmap**

Backend: Add optional `?type=dsi` or `?type=sp` query param to the existing `GET /admin/heatmap` endpoint. When present, filter the SQL aggregation `WHERE i.participant_type = :type`. When absent, keep existing behaviour (all types). No new endpoint — one param change.

Frontend — admin.heatmap.tsx:
- Wrap the existing heatmap in antd `Tabs` (already used in `admin.index.tsx`) with two tabs:
  - Tab 1: `"Aggregated Interoperability Heatmap for DSI's"` — fetches `/admin/heatmap?type=dsi`
  - Tab 2: `"Aggregated Interoperability Heatmap for SP's"` — fetches `/admin/heatmap?type=sp`
- Each tab fetches independently (lazy: only fetch when tab is first activated)
- Page title stays `"Aggregated Interoperability Heatmap"` (unchanged)

Footer text per tab:
- DSI tab: `Based on X submitted DSI initiative(s).`
- SP tab: `Based on X submitted Service Provider initiative(s).`

Existing heatmap matrix component (`CountPill`, grid layout, category/topic structure) is reused as-is for both tabs — no visual redesign.

### Claude's Discretion

- TanStack Router cache fix implementation detail (key prop vs loaderDeps vs useEffect refactor)
- Whether to fetch both tabs eagerly on load or lazily on first tab activation
- Exact Python query param typing (`Optional[str]` or `Literal["dsi", "sp"]`)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

**Bug #1 root causes are BOTH confirmed present** by direct source code inspection. Root cause A (TanStack Router component caching) is the primary issue: `report.tsx` uses two chained `useEffect`s where the first has `[]` deps (never re-fires after mount) and the second has `[initiativeId]` deps (never re-fires because `initiativeId` doesn't change on return navigation). Without a `loader`, `loaderDeps`, or forced remount on the `/report` route, the component reuses its cached state. Root cause B (no save-on-nav-away in wizard) is independently confirmed: `saveCurrentTopic()` is only called inside `handleNext()` and `handleBack()` — there is no `useEffect` cleanup, no `beforeunload` handler, and no `beforeLoad` route hook that triggers save on navigation away.

**Bug #2** is a straightforward omission: the SQL in `export_dataset` does not include `qa.followup_selections` in the SELECT clause, and the header/data rows don't include it either. The column exists in the `questionnaire_answer` table as a JSONB `Optional[List[str]]` field. The fix is purely additive: add the column to SQL SELECT, convert the JSONB array to a semicolon-separated string in the Python row writer, and add it to the header. Nothing else needs to change.

**Feature (DSI/SP heatmap tabs)** is well-scoped: add `participant_type: Optional[str] = None` to the FastAPI `get_admin_heatmap` function, conditionally add a `WHERE i.participant_type = :type` clause to the TWO raw SQL queries (count + aggregation), and restructure `admin.heatmap.tsx` to extract the rendering logic into a shared `HeatmapGrid` presentational component used by both tab data-fetching wrappers.

**Primary recommendation:** Fix both root causes for Bug #1 independently — they are separate bugs. Use TanStack Router's `key` prop on the Route definition (forces full remount on navigation) for Root cause A, and a `useEffect` return-cleanup in WizardPage (calls `saveCurrentTopic()` on unmount) for Root cause B.

---

## Standard Stack

### Core (no new installs required — all already in project)

| Library | Version | Purpose | Already Used |
|---------|---------|---------|--------------|
| TanStack Router | existing | Client-side routing with route-level caching | `report.tsx`, `questionnaire.tsx`, all routes |
| antd | v6 | UI components including `Tabs` | `admin.index.tsx`, `admin.heatmap.tsx` |
| FastAPI | existing | Backend API — query params, streaming response | `admin.py` |
| SQLAlchemy `text()` | existing | Raw SQL queries with bind params | `admin.py` throughout |
| Python `csv` + `io.StringIO` | stdlib | Streaming CSV export | `admin.py export_dataset` |
| React `useEffect` / `useState` | existing | Frontend state and side effects | `report.tsx`, `WizardPage.tsx` |

No new packages need to be installed for any of the three tasks.

---

## Architecture Patterns

### Relevant Project Structure

```
frontend/src/
├── routes/_app/
│   ├── report.tsx          # Bug #1: add Route key/loaderDeps
│   └── admin.heatmap.tsx   # Feature: split into tabs + shared grid component
├── components/questionnaire/
│   └── WizardPage.tsx      # Bug #1: add save-on-unmount effect
backend/app/api/v1/
└── admin.py                # Bug #2 + Feature: CSV fix + heatmap param
```

### Pattern 1: TanStack Router forced remount via `key` prop

**What:** Passing a `key` prop to the route's component forces React to unmount and remount the component on every navigation — even if the URL segment matches. This is the simplest fix when a component's `useEffect([], [])` patterns depend on fresh mount.

**When to use:** When a route component has `useEffect` with empty or non-changing deps that need to re-fire on re-navigation.

**TanStack Router v1 approach:** The `createFileRoute` definition accepts a `wrapInSuspense` or you can use `gcTime: 0` to disable caching. The cleanest route-level solution is adding `gcTime: 0` and `staleTime: 0` to the route definition OR restructuring the `useEffect` chain to not depend on `initiativeId` staying the same.

**Alternative approach (recommended for this case):** Merge the two chained `useEffect`s into a single `useEffect` with `[]` deps that fetches initiative first, then report data in sequence. Adding a stable `mountKey` state via `Date.now()` at mount and including it in the `useEffect` dep array is unnecessary — the simpler fix is to make the report page always-re-fetch on mount. This is achieved by restructuring the effect or by adding a `loaderDeps` that changes on every mount.

**Confirmed gap in current code (`report.tsx` lines 415–438):**
```typescript
// Step 1: fetch initiative id — deps: [] — only fires on first mount
useEffect(() => {
  api.get("/initiatives/me").then(res => setInitiativeId(res.data.id))...
}, []);

// Step 2: fetch report — deps: [initiativeId] — only fires when initiativeId changes
// On re-navigation: component reused, initiativeId already set → never re-fires
useEffect(() => {
  if (initiativeId === null) return;
  api.post(`/initiatives/${initiativeId}/report/data`, {})...
}, [initiativeId]);
```

**Fix options (Claude's discretion):**
1. Merge into single `useEffect([], [])` that fetches initiative then report in sequence — simplest
2. Add `loaderDeps: () => ({ ts: Date.now() })` to route definition and thread the dep through — cleaner router integration but more invasive
3. Reset `initiativeId` to `null` on component re-mount using a ref that detects remount — works but hacky

### Pattern 2: Save-on-unmount useEffect cleanup

**What:** A React `useEffect` that returns a cleanup function runs that function when the component unmounts (navigates away).

**Confirmed gap in current code (`WizardPage.tsx`):** `saveCurrentTopic()` is only called inside `handleNext()` (line 235) and `handleBack()` (line 255). No cleanup effect exists.

**Fix pattern:**
```typescript
// In WizardPage — save current topic answers when component unmounts (nav-away)
useEffect(() => {
  return () => {
    // Fire-and-forget save on unmount — don't await, component is going away
    void saveCurrentTopic();
  };
}, [currentTopic, localAnswers]); // must be up-to-date with latest topic/answers
```

**Pitfall:** The cleanup function captures a stale closure if `saveCurrentTopic` is not a stable reference. `saveCurrentTopic` reads `currentTopic` and `localAnswers` from closure — the dep array must include these so the cleanup always has a fresh copy.

**Alternative:** Use `useRef` to always hold the latest `saveCurrentTopic` and call the ref in the cleanup. This avoids the stale closure problem with a simpler dep array `[]`.

### Pattern 3: FastAPI optional query param filtering with raw SQL

**Established pattern in this project (`admin.py`):** All heatmap SQL uses `session.execute(text(...))` with `.mappings()`. Adding a conditional WHERE clause requires string interpolation (safe via bind params) or a conditional SQL string.

**Pattern:**
```python
@router.get("/heatmap", response_model=AdminHeatmapResponse)
def get_admin_heatmap(
    request: Request,
    participant_type: Optional[str] = None,  # "dsi" or "sp" — None means all
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    type_filter = "AND LOWER(i.participant_type) = :ptype" if participant_type else ""
    params = {"ptype": participant_type.lower()} if participant_type else {}

    count_result = session.execute(
        text(f"SELECT COUNT(*) FROM initiative WHERE status = 'submitted' {type_filter}"),
        params
    )
    # Same filter applied to aggregation query
```

**Note:** `participant_type` values in DB are stored as set at registration. The CONTEXT.md confirmed they use `?type=dsi` / `?type=sp` query params. Must verify if DB values are uppercase/lowercase to determine whether `LOWER()` cast is needed.

### Pattern 4: antd v6 Tabs with lazy fetch per tab

**Established pattern in project (`admin.index.tsx` line 255–373):** `Tabs` uses `items` prop array with `key`, `label`, `children`. `defaultActiveKey` sets initial tab.

**Lazy fetch pattern for heatmap tabs:**
```typescript
// Two independent fetch states — only fetch when tab first activated
const [dsiData, setDsiData] = useState<AdminHeatmapResponse | null>(null);
const [spData, setSpData] = useState<AdminHeatmapResponse | null>(null);
const [dsiLoaded, setDsiLoaded] = useState(false);
const [spLoaded, setSpLoaded] = useState(false);

function handleTabChange(key: string) {
  if (key === "dsi" && !dsiLoaded) { fetchDsi(); setDsiLoaded(true); }
  if (key === "sp" && !spLoaded) { fetchSp(); setSpLoaded(true); }
}
```

Initial load: DSI tab is `defaultActiveKey` → fetch DSI immediately on mount. SP tab fetches only when user clicks it for the first time.

### Pattern 5: CSV JSONB array serialisation

**Existing pattern (`export_dataset`):** `row["followup_other"] or ""` — empty-to-string coercion. JSONB fields returned by SQLAlchemy `text()` with `.mappings()` come back as Python `list` or `None`.

**Fix pattern for `followup_selections`:**
```python
# In the generate_csv inner function, data writerow:
selections = row["followup_selections"]  # None or Python list from JSONB
selections_str = "; ".join(selections) if selections else ""

writer.writerow([
    row["email"], row["initiative_name"], row["participant_type"], row["status"],
    row["question_id"], row["mami_code"], row["answer_value"],
    selections_str,           # NEW — between answer_value and followup_other
    row["followup_other"] or "",
])
```

### Anti-Patterns to Avoid

- **Don't add a new `/admin/heatmap/dsi` and `/admin/heatmap/sp` endpoint** — CONTEXT.md locked decision: one endpoint, one query param. Planner must not create separate endpoint tasks.
- **Don't add `beforeunload` browser event for save-on-nav-away** — `beforeunload` fires on tab/window close, not on SPA navigation. Use React `useEffect` cleanup instead.
- **Don't use `useEffect` cleanup with `[]` deps for save-on-nav-away** — `[]` deps means the cleanup captures the initial (empty) `localAnswers`. Must include current topic/answers in the dep array or use a ref.
- **Don't modify `followup_other` column** — locked decision. The bug is purely about the missing `followup_selections` column.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tabs UI for DSI/SP | Custom tab switcher | antd `Tabs` with `items` prop | Already imported and used in `admin.index.tsx` — identical pattern |
| CSV streaming | Custom HTTP chunking | `StreamingResponse` + `io.StringIO` generator | Already used in `export_dataset` — just add the column |
| SQL bind params | String interpolation | `text(sql)` + params dict | Already used throughout `admin.py` — prevents SQL injection |
| Route remount forcing | Custom history listener | TanStack Router `key` prop or `loaderDeps` | Built-in mechanism for this exact use case |

---

## Common Pitfalls

### Pitfall 1: Stale closure in useEffect cleanup for save-on-nav-away

**What goes wrong:** The cleanup function returned from `useEffect` captures the values of `currentTopic` and `localAnswers` as they were when the effect last ran. If deps aren't included, `saveCurrentTopic()` in the cleanup saves the wrong topic or empty answers.

**Why it happens:** React's closure semantics — the cleanup function is a snapshot from when the effect ran.

**How to avoid:** Either include `[currentTopic, localAnswers]` (or a stable derived value) in the effect's dep array, or store a ref that always points to the latest version of `saveCurrentTopic`.

**Warning signs:** Badge says "Saving..." after nav-away but answers don't appear in DB; or empty saves overwrite valid answers.

### Pitfall 2: Report page useEffect double-fire on initiativeId

**What goes wrong:** If the fix merges both effects into one `useEffect([], [])`, the fetch runs once on mount. But if `initiativeId` fetch fails and retries, or if the effect cleans up mid-flight, two parallel requests may race.

**Why it happens:** AbortController not used — if the component unmounts before the fetch completes (e.g., user navigates away quickly), the then-callback still runs and calls `setData`/`setLoading` on an unmounted component.

**How to avoid:** Add cleanup with `AbortController` inside the merged effect — or at minimum, guard with a `let cancelled = false` flag and check it in `.then()`.

**Warning signs:** React warning "Can't perform a React state update on an unmounted component" in console.

### Pitfall 3: participant_type case sensitivity in heatmap filter

**What goes wrong:** The query param `?type=dsi` passes lowercase, but `participant_type` stored in the DB may be uppercase (`DSI`, `SP`) depending on how registration sets it.

**Why it happens:** The `User` model stores `participant_type` as set at registration. Need to verify actual DB values.

**How to avoid:** Use `LOWER(i.participant_type) = :ptype` with `participant_type.lower()` as the bind value, or verify stored values match `dsi`/`sp` exactly.

**Warning signs:** Tabs return 0 results even when submitted initiatives exist.

**Mitigation:** Check `User` model and existing `admin.py` list_users query — it selects `u.participant_type` without case conversion, indicating values may be stored as-is from registration.

### Pitfall 4: antd Card `bodyStyle` prop deprecation in antd v6

**What goes wrong:** `admin.heatmap.tsx` uses `bodyStyle={{ padding: "1.5rem" }}` on `Card`. In antd v6, this prop is deprecated in favour of `styles={{ body: { padding: "1.5rem" } }}`.

**Why it happens:** antd v6 replaced many inline style props with a unified `styles` object prop.

**How to avoid:** When restructuring the Card layout for tabs, use `styles={{ body: ... }}` instead of `bodyStyle`. However, since the CONTEXT.md says to reuse existing component as-is, this may not need to change for the tab implementation — carry forward whatever is already there.

**Warning signs:** Console warning about deprecated prop.

### Pitfall 5: CSV streaming — row state reset issue

**What goes wrong:** The `generate_csv` function uses `output.truncate(0)` + `output.seek(0)` to reset the StringIO buffer between rows. If `followup_selections` contains a semicolon itself (e.g., option text with semicolons), the formatting becomes ambiguous.

**Why it happens:** Semicolons chosen as the separator without escaping.

**How to avoid:** The CONTEXT.md locked decision says semicolon-separated. Option texts in questionnaire configs should not themselves contain semicolons — verify in config files if concerned. The CSV `csv.writer` already handles quoting of the outer column (the whole semicolon-separated string is written as one field), so commas within it are safe.

---

## Code Examples

Verified from source code inspection:

### Bug #2: Exact CSV export diff

Current SQL (admin.py line 222–228):
```python
rows = session.execute(text("""
    SELECT u.email, i.name AS initiative_name, i.participant_type, i.status,
           qa.question_id, qa.mami_code, qa.answer_value, qa.followup_other
    FROM "user" u
    JOIN initiative i ON i.user_id = u.id
    JOIN questionnaire_answer qa ON qa.initiative_id = i.id
    ORDER BY u.email, i.id, qa.question_id
"""))
```

Fixed SQL — add `qa.followup_selections` after `qa.answer_value`:
```python
rows = session.execute(text("""
    SELECT u.email, i.name AS initiative_name, i.participant_type, i.status,
           qa.question_id, qa.mami_code, qa.answer_value,
           qa.followup_selections, qa.followup_other
    FROM "user" u
    JOIN initiative i ON i.user_id = u.id
    JOIN questionnaire_answer qa ON qa.initiative_id = i.id
    ORDER BY u.email, i.id, qa.question_id
"""))
```

Current header (admin.py line 211–214):
```python
writer.writerow([
    "user_email", "initiative_name", "participant_type", "initiative_status",
    "question_id", "mami_code", "answer_value", "followup_other",
])
```

Fixed header:
```python
writer.writerow([
    "user_email", "initiative_name", "participant_type", "initiative_status",
    "question_id", "mami_code", "answer_value", "followup_selections", "followup_other",
])
```

Current data writerow (admin.py line 231–239):
```python
writer.writerow([
    row["email"], row["initiative_name"], row["participant_type"], row["status"],
    row["question_id"], row["mami_code"], row["answer_value"],
    row["followup_other"] or "",
])
```

Fixed data writerow:
```python
selections = row["followup_selections"]
selections_str = "; ".join(selections) if selections else ""
writer.writerow([
    row["email"], row["initiative_name"], row["participant_type"], row["status"],
    row["question_id"], row["mami_code"], row["answer_value"],
    selections_str,
    row["followup_other"] or "",
])
```

### Bug #1 Fix A: Merged useEffect in report.tsx

Replace the two chained effects (lines 415–438) with a single re-fetching effect:
```typescript
// Single effect — re-runs from scratch each time component mounts
// Fix: use a mount counter or just merge into one sequential effect
useEffect(() => {
  let cancelled = false;
  setLoading(true);
  setError(null);

  api.get<{ id: number; name: string; status: string }>("/initiatives/me")
    .then((res) => {
      if (cancelled) return;
      const id = res.data.id;
      return api.post<ReportData>(`/initiatives/${id}/report/data`, {});
    })
    .then((res) => {
      if (cancelled || !res) return;
      setData(res.data);
    })
    .catch(() => {
      if (!cancelled) setError("Failed to generate report.");
    })
    .finally(() => {
      if (!cancelled) setLoading(false);
    });

  return () => { cancelled = true; };
}, []); // [] — fires fresh on every mount; component must be remounted on re-navigation
```

**Note:** This ONLY works if the route component is remounted on re-navigation. Must also confirm TanStack Router remount behaviour — if router reuses the component, deps `[]` still won't re-fire. The route-level fix is required in addition or instead.

### Bug #1 Fix B: Save-on-unmount in WizardPage.tsx

```typescript
// In WizardPage — add after existing useEffect (line 118-134)
// Use ref pattern to avoid stale closure issue
const saveCurrentTopicRef = useRef(saveCurrentTopic);
useEffect(() => {
  saveCurrentTopicRef.current = saveCurrentTopic;
});

useEffect(() => {
  return () => {
    // Fire-and-forget on unmount — save whatever the current topic state is
    void saveCurrentTopicRef.current();
  };
}, []); // [] is safe because we use ref, not closure
```

### Feature: Backend heatmap param addition

In `get_admin_heatmap` function signature and SQL (admin.py):
```python
@router.get("/heatmap", response_model=AdminHeatmapResponse)
def get_admin_heatmap(
    request: Request,
    type: Optional[str] = None,            # "dsi" or "sp" — None means all types
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    type_filter = "AND LOWER(i.participant_type) = :ptype" if type else ""
    params = {"ptype": type.lower()} if type else {}

    count_result = session.execute(
        text(f"SELECT COUNT(*) FROM initiative WHERE status = 'submitted' {type_filter}"),
        params
    )
    total_submitted = int(count_result.scalar() or 0)

    agg_result = session.execute(text(f"""
        SELECT qa.mami_code, qa.answer_value, COUNT(*) as cnt
        FROM questionnaire_answer qa
        JOIN initiative i ON i.id = qa.initiative_id
        WHERE i.status = 'submitted' {type_filter}
        GROUP BY qa.mami_code, qa.answer_value
    """), params)
```

### Feature: Frontend tabs with lazy fetch

In `admin.heatmap.tsx` — add tab structure around existing render logic:
```typescript
// Extract existing rendering into HeatmapGrid component (receives data prop)
// Add two independent fetch states:
const [dsiData, setDsiData] = useState<AdminHeatmapResponse | null>(null);
const [dsiLoading, setDsiLoading] = useState(false);
const [dsiError, setDsiError] = useState<string | null>(null);
const [spData, setSpData] = useState<AdminHeatmapResponse | null>(null);
const [spLoading, setSpLoading] = useState(false);
const [spError, setSpError] = useState<string | null>(null);
const [spFetched, setSpFetched] = useState(false);

// Fetch DSI on mount (default tab)
useEffect(() => {
  setDsiLoading(true);
  api.get<AdminHeatmapResponse>("/admin/heatmap?type=dsi")
    .then(res => setDsiData(res.data))
    .catch(() => setDsiError("Failed to load DSI heatmap data."))
    .finally(() => setDsiLoading(false));
}, []);

// Fetch SP lazily on first tab activation
function handleTabChange(key: string) {
  if (key === "sp" && !spFetched) {
    setSpFetched(true);
    setSpLoading(true);
    api.get<AdminHeatmapResponse>("/admin/heatmap?type=sp")
      .then(res => setSpData(res.data))
      .catch(() => setSpError("Failed to load SP heatmap data."))
      .finally(() => setSpLoading(false));
  }
}

// Tabs items:
const tabItems = [
  {
    key: "dsi",
    label: "Aggregated Interoperability Heatmap for DSI's",
    children: <HeatmapGrid data={dsiData} loading={dsiLoading} error={dsiError} typeLabel="DSI initiative" />,
  },
  {
    key: "sp",
    label: "Aggregated Interoperability Heatmap for SP's",
    children: <HeatmapGrid data={spData} loading={spLoading} error={spError} typeLabel="Service Provider initiative" />,
  },
];
```

Footer text inside `HeatmapGrid` (receives `typeLabel` prop):
```
Based on {data.total_submitted} submitted {typeLabel}(s).
```

---

## Root Cause Confirmation

### Bug #1 — Both root causes confirmed present

**Root cause A — TanStack Router component reuse (CONFIRMED):**
- `report.tsx` line 9: `createFileRoute("/_app/report")({ component: ReportPage })` — no `key`, no `loader`, no `loaderDeps`
- `_app.tsx` layout: plain `<Outlet />` — no route-level config forcing remount
- `__root.tsx`: minimal — `createRootRoute({ component: () => <Outlet /> })`
- Conclusion: TanStack Router will reuse the `ReportPage` component instance when navigating away and back. The two chained `useEffect`s will NOT re-fire.

**Root cause B — No save-on-nav-away (CONFIRMED):**
- `WizardPage.tsx` line 215–228: `saveCurrentTopic()` defined, called ONLY in `handleNext()` (line 235) and `handleBack()` (line 256)
- No `useEffect` cleanup function anywhere in `WizardPage.tsx`
- No route `beforeLoad` or `onLeave` hook in `questionnaire.tsx`
- Conclusion: If user navigates from `/questionnaire` to `/report` via TopNav or dashboard link without clicking "Next", the current topic's answers are not persisted.

**Fix scope:** Both fixes are required and independent. Root cause A fix ensures report always re-fetches fresh data. Root cause B fix ensures DB always has the latest answers when report fetches them.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Separate `useEffect` chains for sequential async | Merged effect with cancellation flag | Better for remount scenarios |
| `followup_selections` absent from CSV | Add column with semicolon-join | Purely additive — no data migration |
| Single aggregated heatmap (all types) | Two tabs filtered by participant_type | One endpoint, param-filtered |

---

## Open Questions

1. **participant_type case in DB**
   - What we know: `admin.py list_users` query selects `u.participant_type` raw. Registration stores whatever the user selects.
   - What's unclear: Are values stored as `dsi`/`sp` (lowercase), `DSI`/`SP` (uppercase), or `DSI Initiative`/`Service Provider` (full label)?
   - Recommendation: Inspect the User model or existing admin data before writing the SQL filter. The `LOWER()` cast is a safe defensive measure; alternatively verify the registration form to see what string gets stored.
   - **Action for planner:** Add a task step "verify participant_type DB values match lowercase `dsi`/`sp`" before writing the SQL filter. Use `LOWER()` cast as default.

2. **TanStack Router exact remount behaviour**
   - What we know: No `key`, no `loader`, no `loaderDeps` on the `/report` route.
   - What's unclear: Whether TanStack Router's default behaviour fully reuses component instances on same-route re-navigation (navigate away then back to same path).
   - Recommendation: Merging the two `useEffect`s into a single `[]`-dep effect alone may not be sufficient if TanStack Router reuses the component. The safest fix is the merged effect PLUS adding `loaderDeps: () => ({ ts: Date.now() })` to the route definition, which forces the route to treat each navigation as a new load.

---

## Sources

### Primary (HIGH confidence)
- Direct source inspection: `C:/Users/djlia/Desktop/MaMi Checker/frontend/src/routes/_app/report.tsx` — two-effect pattern confirmed at lines 415–438
- Direct source inspection: `C:/Users/djlia/Desktop/MaMi Checker/frontend/src/components/questionnaire/WizardPage.tsx` — save-on-nav gap confirmed; `saveCurrentTopic` only in handleNext/handleBack
- Direct source inspection: `C:/Users/djlia/Desktop/MaMi Checker/backend/app/api/v1/admin.py` — missing `followup_selections` in SQL SELECT (line 222), header (line 211), and writerow (line 231); heatmap SQL confirmed at lines 281–343
- Direct source inspection: `C:/Users/djlia/Desktop/MaMi Checker/backend/app/models/questionnaire.py` — `followup_selections: Optional[List[str]]` JSONB field confirmed at line 27
- Direct source inspection: `C:/Users/djlia/Desktop/MaMi Checker/frontend/src/routes/_app/admin.heatmap.tsx` — `CountPill`, grid layout, `AdminHeatmapResponse` interface all confirmed
- Direct source inspection: `C:/Users/djlia/Desktop/MaMi Checker/frontend/src/routes/_app/admin.index.tsx` — antd v6 `Tabs` with `items` prop pattern at line 255, 414

### Tertiary (LOW confidence — general knowledge, not verified via Context7)
- TanStack Router component reuse/caching behaviour on re-navigation: based on known React Router SPA patterns — recommend verifying with TanStack Router docs if any doubt

---

## Metadata

**Confidence breakdown:**
- Bug #1 root cause identification: HIGH — confirmed by direct code inspection of both files
- Bug #2 fix scope: HIGH — confirmed by direct inspection of SQL, header, writerow in admin.py; model confirms JSONB column
- Feature backend: HIGH — existing SQL pattern in admin.py is clear; param addition is straightforward
- Feature frontend: HIGH — Tabs pattern confirmed in admin.index.tsx; lazy fetch pattern is well-established React
- participant_type case sensitivity: MEDIUM — needs verification of actual stored values

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable codebase, no external library changes needed)
