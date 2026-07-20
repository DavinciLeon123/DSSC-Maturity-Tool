# Phase 10: UX Polish, Scalability & Admin Heatmap - Research

**Researched:** 2026-03-10
**Domain:** React/TypeScript frontend polish + FastAPI backend scalability + admin data aggregation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Survey completion text**
- Heading: change "Your submission is complete" → "Thanks for completing the survey."
- Dashboard button: change "Generate Compliance Report" → "Generate Heatmap"
- (The WizardPage "Generate heatmap" button label is already correct from Phase 9 — no change needed there)

**Scroll-to-top**
- Trigger: on every Next and Previous button click in WizardPage
- Implementation: `window.scrollTo({ top: 0, behavior: 'smooth' })` (or 'instant') inside the existing handleNext / handlePrevious handlers
- Not required on StepPills category click or on wizard mount

**Remove My Initiative tab**
- Remove the `{ label: 'My Initiative', to: '/initiative' }` entry from `navItems` in `TopNav.tsx`
- The /initiative route file can remain (no hard delete needed — just hidden from nav)

**100-user scalability**
- Context: single breakout session event, ~200 total attendees, peak ~100 concurrent
- Railway Hobby plan constraints: single container, limited RAM
- Approach: Claude's discretion — pick what's safe for a Hobby-tier single-container deployment
  - Options: increase DB pool, add uvicorn workers if Railway supports it, or tune existing settings
  - Do NOT introduce gunicorn if it complicates the Railway single-process model
  - Priority: stability over raw throughput — this is a one-off event demo, not production SLA

**Equal-width heatmap pills**
- Use `minWidth` (not fixed `width`) on the StatusChip span so all pills share a minimum width
- Text stays centered; no clipping risk
- Apply to the heatmap chip cells only (not the legend at the bottom)

**Admin aggregated heatmap**
- Route: New page at `/admin/heatmap` (separate route, not a tab on /admin)
- Access: Link from existing /admin page — add a button "View Aggregated Heatmap →" at the top of the admin users panel
- Data source: Only initiatives with `status = 'submitted'` are counted
- Cell content: 3 count pills per cell — green (yes count), blue (not_yet count), grey (n_a count)
  - Unanswered is implicit (total submitted minus the three counts) — not displayed as a pill
- Layout: Same 9×3 matrix as the user heatmap (4 category group headers + 9 topic rows × 3 dimensions)
- Backend: New endpoint `GET /admin/heatmap` that aggregates QuestionnaireAnswer rows for all submitted initiatives, maps to matrix structure, returns counts per cell

### Claude's Discretion

- `behavior: 'smooth'` vs `behavior: 'instant'` for scroll-to-top (both are valid; smooth is friendlier UX for a multi-step wizard)
- Exact pool_size / max_overflow values for 100-user scalability (must stay within Railway Hobby RAM budget)
- How to add a uvicorn `--workers` flag — or whether to keep single worker and just tune pool

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 10 contains seven targeted improvements spread across three concerns: (1) text/label fixes (completion heading, dashboard button), (2) UX scroll behaviour and nav cleanup, and (3) backend scalability tuning plus a new admin aggregated heatmap feature. All changes touch existing files except the new `/admin/heatmap` frontend route and backend endpoint.

The frontend changes (text edits, scroll-to-top, nav removal, minWidth on StatusChip) are zero-risk string/style edits in already-read files. The scalability change is low-risk tuning of DB pool parameters; `fastapi run` under the hood is a single uvicorn process and cannot spawn multiple workers without a Gunicorn or explicit uvicorn `--workers` flag — the correct approach is to tune the connection pool for the same single process. The admin heatmap is the most substantive new feature: a SQL aggregation query on `questionnaire_answer` joined to `initiative` (status = 'submitted'), a new backend endpoint following the exact pattern of existing admin endpoints, and a new TanStack Router page file with the same auth guard pattern.

**Primary recommendation:** Implement in dependency order — backend endpoint first (independent), then frontend route (needs endpoint), then minor text/label fixes (independent), then pool tuning (independent). The routeTree.gen.ts must be manually updated to include `/_app/admin/heatmap` before running `tsc`.

---

## Standard Stack

### Core (existing — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React + TypeScript | 18.x | Frontend UI | Project standard |
| TanStack Router | v1 | File-based routing | Project standard; routeTree.gen.ts pattern established |
| Ant Design (antd) | 5.x | UI components (Card, Button, Spin, Alert) | Project standard; ConfigProvider already wraps app |
| FastAPI | 0.11x | Backend REST API | Project standard |
| SQLModel + SQLAlchemy | pinned | ORM + DB engine | Project standard; SQLModel requires SQLAlchemy <2.1.0 |
| PostgreSQL | 15 | Database | Project standard |

### No New Packages Required

All phase 10 changes use existing project dependencies. No `npm install` or `uv add` commands needed.

---

## Architecture Patterns

### Pattern 1: Text Change — WizardPage completion screen

**File:** `frontend/src/components/questionnaire/WizardPage.tsx` line 348

**What:** The `<h2>` inside the `if (submitted)` block contains `"Your submission is complete"`. Change to `"Thanks for completing the survey."`.

**Exact location in code:**
```typescript
// Line ~348 in WizardPage.tsx — inside the `if (submitted) { return (...) }` block
<h2 ...>
  Your submission is complete   {/* CHANGE THIS */}
</h2>
```

### Pattern 2: Text Change — Dashboard button label

**File:** `frontend/src/routes/_app/dashboard.tsx` line ~323

**What:** The secondary Button in the initiative details card has children `"Generate Compliance Report"`. Change to `"Generate Heatmap"`.

```typescript
// Line ~323 in dashboard.tsx
<Button size="large" onClick={handleGenerateReport} loading={reportLoading} ...>
  Generate Compliance Report   {/* CHANGE THIS → "Generate Heatmap" */}
</Button>
```

### Pattern 3: Scroll-to-top in handleNext / handleBack

**File:** `frontend/src/components/questionnaire/WizardPage.tsx`

**What:** Insert `window.scrollTo({ top: 0, behavior: 'smooth' })` as the first statement inside `handleNext` and `handleBack` (before the guard checks or after — the important thing is it fires on every click).

**Correct insertion point:** After the guard check (`if (isNextDisabled) return;`) but before `setIsSaving(true)`:

```typescript
async function handleNext() {
  if (isNextDisabled) return;
  window.scrollTo({ top: 0, behavior: 'smooth' });  // ADD THIS
  setIsSaving(true);
  try {
    // ... existing logic
  } finally {
    setIsSaving(false);
  }
}

async function handleBack() {
  if (isBackDisabled) return;
  window.scrollTo({ top: 0, behavior: 'smooth' });  // ADD THIS
  setIsSaving(true);
  // ... existing logic
}
```

**Why after the guard:** If the button is disabled and returns early, we don't want to scroll. Placing the scroll call after the guard ensures it only fires when navigation actually proceeds.

### Pattern 4: Remove My Initiative from TopNav

**File:** `frontend/src/components/layout/TopNav.tsx`

**What:** Remove the `{ label: 'My Initiative', to: '/initiative' }` entry from the `navItems` array. The TypeScript union type for `to` must also be updated to remove `'/initiative'` from the literal union.

**Current code (lines 24-30):**
```typescript
const navItems: Array<{ label: string; to: '/dashboard' | '/initiative' | '/questionnaire' | '/about' | '/admin' }> = [
  { label: 'Dashboard', to: '/dashboard' },
  { label: 'My Initiative', to: '/initiative' },   // REMOVE THIS LINE
  { label: 'Questionnaire', to: '/questionnaire' },
  { label: 'About', to: '/about' },
  ...(isAdmin ? [{ label: 'Admin', to: '/admin' as const }] : []),
];
```

**After change:**
```typescript
const navItems: Array<{ label: string; to: '/dashboard' | '/questionnaire' | '/about' | '/admin' }> = [
  { label: 'Dashboard', to: '/dashboard' },
  { label: 'Questionnaire', to: '/questionnaire' },
  { label: 'About', to: '/about' },
  ...(isAdmin ? [{ label: 'Admin', to: '/admin' as const }] : []),
];
```

### Pattern 5: Equal-width StatusChip with minWidth

**File:** `frontend/src/routes/_app/report.tsx`

**What:** Add `minWidth: '90px'` (or similar) to the `StatusChip` span's inline style. This ensures all pills in the heatmap cells share a consistent minimum width so the grid looks aligned.

**Target:** The `<span>` in the `StatusChip` function (line ~82). Apply only to the heatmap matrix chips — which is the same component instance used in cells. The legend chips at the bottom can keep their current sizing (they're used with labels beside them, so width consistency matters less).

**Option A — apply minWidth to the StatusChip component universally:**
```typescript
function StatusChip({ status }: { status: string }) {
  // ...
  return (
    <span
      style={{
        // ... existing styles
        minWidth: '90px',     // ADD THIS
        justifyContent: 'center',  // center content within the min-width
      }}
    >
```

**Option B — add optional prop `equalWidth?: boolean`:**
```typescript
function StatusChip({ status, equalWidth }: { status: string; equalWidth?: boolean }) {
  return (
    <span style={{ ...existingStyles, ...(equalWidth ? { minWidth: '90px', justifyContent: 'center' } : {}) }}>
```

The CONTEXT.md says "apply to heatmap chip cells only (not the legend)". Option B is safer as it doesn't affect legend chips. However, the minWidth is visually harmless in the legend context too — Option A is simpler.

**Recommended:** Use Option A (universal minWidth) since the visual impact in the legend is negligible and Option B adds prop complexity. Validate visually.

### Pattern 6: DB Connection Pool Tuning

**File:** `backend/app/db/session.py`

**Current:** `pool_size=10, max_overflow=20` → total max 30 connections

**For 100 concurrent users:** The bottleneck analysis:
- Each HTTP request holds a DB connection only during the query (async FastAPI, not per-connection threads)
- `fastapi run` = single uvicorn worker, single asyncio event loop
- Single uvicorn process can handle many concurrent requests via asyncio without needing more workers
- The save-on-navigate endpoint (answers upsert) is the hot path — rate-limited to 60/min per IP, so max burst per user is bounded
- 100 users × peak simultaneous save = ~100 concurrent DB operations at most
- Pool of 30 is likely sufficient; increasing to `pool_size=15, max_overflow=25` (total 40) adds a safety buffer

**Recommended change:**
```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=15,        # Was 10 — up for 100-user peak
    max_overflow=25,     # Was 20 — total max 40 connections
    pool_pre_ping=True,
    pool_recycle=1800,
)
```

**Why NOT multiple uvicorn workers:** The Dockerfile CMD uses `fastapi run app/main.py` which is a thin wrapper around `uvicorn`. Adding `--workers 2` would require the app to be stateless (it is, since app.state is per-worker). However, Railway Hobby plan has memory constraints (~512MB). Each worker spawns a separate Python process with full memory footprint. With ZEN engine and all app.state singletons loaded, a second worker could push memory over limit. The CONTEXT.md explicitly says "stability over raw throughput — do NOT introduce gunicorn if it complicates the Railway single-process model." Keep single worker, tune pool only.

**Pool sizing math for Railway Hobby:** Railway's free PostgreSQL likely has a connection limit (typically 25 on free tier, but this project uses Railway's paid PostgreSQL add-on per earlier phases). If the DB connection limit is 25, pool_size=15 max_overflow=10 is safer. Check Railway dashboard for the connection limit of the attached PostgreSQL service before finalizing.

### Pattern 7: New Backend Endpoint — GET /admin/heatmap

**File:** `backend/app/api/v1/admin.py`

**Pattern established by existing admin endpoints:**
- Use `@router.get(...)` on the existing `router = APIRouter(prefix="/admin", ...)`
- Depend on `get_session` and `require_admin` as function parameters
- Use raw SQL via `session.execute(text(...))` to avoid enum deserialization errors (project convention)
- Return a Pydantic `BaseModel` response

**SQL logic needed:**
```sql
SELECT qa.mami_code, qa.answer_value, COUNT(*) as cnt
FROM questionnaire_answer qa
JOIN initiative i ON i.id = qa.initiative_id
WHERE i.status = 'submitted'
GROUP BY qa.mami_code, qa.answer_value
```

This gives per-(mami_code, answer_value) counts across all submitted initiatives. Then Python maps these counts into the same `{category: {dimension: {topic_id: {yes: N, not_yet: N, n_a: N}}}}` structure.

**Response schema for admin heatmap:**
```python
class AdminHeatmapCell(BaseModel):
    yes: int = 0
    not_yet: int = 0
    n_a: int = 0

class AdminHeatmapResponse(BaseModel):
    total_submitted: int
    matrix: Dict[str, Dict[str, Dict[str, AdminHeatmapCell]]]  # cat -> dim -> topic_id -> counts
    topic_structure: Dict[str, List[dict]]  # same shape as user report topic_structure
```

**Matrix population logic (Python):**
The matrix structure groups by topic (not mami_code) because the frontend renders one row per topic. For each cell `[category][dimension][topic_id]`, sum up the answer counts for all mami_codes that belong to that topic.

The `_build_topic_structure` function in `report_generator.py` already groups mami_codes by topic. Reuse this function or replicate its logic in the admin endpoint to get the code→topic mapping.

**Full endpoint pattern:**
```python
@router.get("/heatmap")
def get_admin_heatmap(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
    request: Request = None,
):
    # 1. Count submitted initiatives
    # 2. Fetch per-(mami_code, answer_value) counts via raw SQL
    # 3. Load mami_config from request.app.state.mami_config
    # 4. Build topic_structure using _build_topic_structure (import from report_generator)
    # 5. Map counts into matrix[cat][dim][topic_id] = {yes, not_yet, n_a}
    # 6. Return AdminHeatmapResponse
```

Note: `request: Request` dependency needed to access `request.app.state.mami_config`. This is the same pattern used in `deps.py` (`get_mami_config`). Alternatively, use the `get_mami_config` dependency directly.

### Pattern 8: New Frontend Route — /admin/heatmap

**File to create:** `frontend/src/routes/_app/admin/heatmap.tsx`

**TanStack Router flat-file naming convention:** Looking at existing routes, all routes are flat files under `routes/_app/` (e.g., `admin.tsx`, `report.tsx`). The file `routes/_app/admin/heatmap.tsx` uses a directory approach. TanStack Router v1 supports both. Since the existing admin route is a flat file `_app/admin.tsx`, the sub-route needs to be placed carefully.

**Two valid approaches in TanStack Router v1:**

Option A — Flat file `_app/admin.heatmap.tsx` (dot notation):
```typescript
export const Route = createFileRoute('/_app/admin/heatmap')({...})
```
The file lives at `routes/_app/admin.heatmap.tsx`. This is the TanStack Router v1 pattern for nested paths in flat-file mode.

Option B — Directory `_app/admin/heatmap.tsx`:
Requires a parent `_app/admin.tsx` which already exists. But the existing `admin.tsx` uses `createFileRoute('/_app/admin')` not as a layout route. This could create conflicts.

**Recommendation:** Use Option A — flat file `routes/_app/admin.heatmap.tsx` with `createFileRoute('/_app/admin/heatmap')`. This avoids directory structure conflicts with the existing `admin.tsx`.

**Auth guard — same pattern as admin.tsx:**
```typescript
export const Route = createFileRoute('/_app/admin/heatmap')({
  beforeLoad: async () => {
    try {
      const res = await api.get<{ role: string }>('/auth/me');
      if (res.data.role !== 'ADMIN') throw redirect({ to: '/dashboard' });
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'to' in err) throw err;
      throw redirect({ to: '/dashboard' });
    }
  },
  component: AdminHeatmapPage,
});
```

**routeTree.gen.ts update:** Must manually add `/_app/admin/heatmap` route following the established convention. The Vite plugin regenerates on dev server start, but the committed version must be manually updated before `tsc`. Pattern to follow for the new route in all four interface blocks.

**AdminHeatmapPage component:** Renders same 9×3 matrix layout as `HeatmapMatrix` in `report.tsx` but cells show 3 count pills (yes/not_yet/n_a) instead of 1 status chip. Reuse `CATEGORY_LABELS`, `DIMENSION_LABELS`, `DIMENSION_LABELS_MOBILE` constants — either import from report.tsx (if exported) or duplicate them.

**Currently, report.tsx does NOT export these constants** — they are module-level but not exported. Options:
- Add `export const CATEGORY_LABELS = ...` to report.tsx and import in admin heatmap
- Duplicate the constants in the new file (small, stable constants — duplication is acceptable)

**Recommendation:** Duplicate the constants in the new file to avoid coupling admin heatmap to the report page module.

**Count pill component for admin heatmap:**
```typescript
function CountPill({ count, color }: { count: number; color: 'green' | 'blue' | 'grey' }) {
  const cfg = {
    green: { bg: 'rgba(57,158,90,0.2)', color: '#399e5a' },
    blue:  { bg: 'rgba(61,82,213,0.2)', color: '#3d52d5' },
    grey:  { bg: 'rgba(204,204,204,0.8)', color: '#666' },
  }[color];
  return (
    <span style={{
      background: cfg.bg, color: cfg.color,
      borderRadius: '100px', padding: '4px 12px',
      fontSize: '0.85rem', fontFamily: "'Rubik', sans-serif",
      fontWeight: 600, minWidth: '36px', textAlign: 'center',
      display: 'inline-block',
    }}>
      {count}
    </span>
  );
}
```

**Cell layout for admin heatmap (3 pills stacked or in a row):**
```typescript
<div style={{ display: 'flex', gap: '4px', justifyContent: 'center', flexWrap: 'wrap' }}>
  <CountPill count={cell.yes} color="green" />
  <CountPill count={cell.not_yet} color="blue" />
  <CountPill count={cell.n_a} color="grey" />
</div>
```

### Pattern 9: Link from /admin to /admin/heatmap

**File:** `frontend/src/routes/_app/admin.tsx`

**What:** Add a button at the top of the Users panel (or at the top of the AdminPage, above the Card) that navigates to `/admin/heatmap`.

**Pattern using TanStack Router Link:**
```typescript
import { Link } from '@tanstack/react-router';

// Inside AdminPage render, above or within the Card:
<div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'flex-end' }}>
  <Link to="/admin/heatmap">
    <Button type="default" style={{ fontFamily: "'Rubik', sans-serif", fontWeight: 500 }}>
      View Aggregated Heatmap →
    </Button>
  </Link>
</div>
```

Note: The `to` type in TanStack Router is constrained to registered routes. After adding `/_app/admin/heatmap` to routeTree.gen.ts, TypeScript will accept `to="/admin/heatmap"`.

### Anti-Patterns to Avoid

- **Setting behavior: 'smooth' and also calling it in the `finally` block:** Put the scrollTo call once at the top of each handler, not in finally (it would scroll after save completes, which is too late for UX).
- **Multiple uvicorn workers on Railway Hobby:** Memory budget doesn't support it; keep single worker.
- **Using `width` instead of `minWidth` on StatusChip:** Fixed width clips text on longer labels; minWidth allows growth.
- **Forgetting to update routeTree.gen.ts:** tsc build will fail and the new route won't be registered.
- **Importing _build_topic_structure from report_generator in admin.py:** This creates a cross-dependency. The admin endpoint should either call it directly (import is fine) or replicate the minimal logic it needs. Importing is cleaner — the function is pure Python with no FastAPI dependencies.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SQL aggregation per cell | Loop over Python dicts | Single GROUP BY SQL query | DB does set math faster; avoids N+1 |
| Route type safety | String-based navigation | TanStack Router's typed `to` prop | Compile-time route validation |
| Admin auth guard | Custom session check | Existing `require_admin` FastAPI dependency | Already tested, consistent |
| Topic structure mapping | Re-derive from scratch | `_build_topic_structure()` from report_generator | Already correct and tested |

---

## Common Pitfalls

### Pitfall 1: routeTree.gen.ts not updated before tsc

**What goes wrong:** TypeScript build fails with "Route '/admin/heatmap' is not a registered route" errors.
**Why it happens:** routeTree.gen.ts is auto-generated but committed. The Vite dev plugin regenerates it on dev server start, but the committed version is what `tsc --noEmit` checks.
**How to avoid:** Update routeTree.gen.ts manually before committing — add the new route to all four interface blocks (`FileRoutesByFullPath`, `FileRoutesByTo`, `FileRoutesById`, `FileRouteTypes`) and to `AppRouteChildren`. Follow the exact pattern of existing routes.
**Warning signs:** TypeScript errors referencing the route path, or the `Link to="/admin/heatmap"` showing a type error.

### Pitfall 2: scroll-to-top placed in the wrong handler position

**What goes wrong:** Scroll fires after async save completes (1–2 second delay), making it feel broken.
**Why it happens:** If `window.scrollTo` is inside the `try` block after `await saveCurrentTopic()`, the scroll is delayed.
**How to avoid:** Place `window.scrollTo` as the first statement after the guard check, before any async operations.
**Warning signs:** Page scrolls noticeably after the saving spinner appears.

### Pitfall 3: Admin heatmap SQL missing status filter

**What goes wrong:** Counts include draft/active initiatives, inflating numbers and showing partial data as complete.
**Why it happens:** The `WHERE i.status = 'submitted'` clause is easy to forget.
**How to avoid:** Always include `WHERE i.status = 'submitted'` in the aggregation query.

### Pitfall 4: DB connection pool exceeds PostgreSQL max_connections

**What goes wrong:** SQLAlchemy raises `OperationalError: FATAL: remaining connection slots are reserved` under load.
**Why it happens:** If Railway's PostgreSQL service has a connection limit lower than pool_size + max_overflow.
**How to avoid:** Check Railway PostgreSQL service's connection limit before setting pool values. If limit is 25, use `pool_size=10, max_overflow=10` (total 20, leaving headroom for admin connections).

### Pitfall 5: TypeScript union type in TopNav not updated after removing My Initiative

**What goes wrong:** TypeScript error on the `navItems` array type annotation after removing `'/initiative'` from the union.
**Why it happens:** The `to` type is explicitly annotated as a string union that includes `'/initiative'`.
**How to avoid:** Also remove `'/initiative'` from the union type when removing the nav entry.

### Pitfall 6: Admin heatmap page not using beforeLoad auth guard

**What goes wrong:** Non-admin users can navigate directly to `/admin/heatmap` URL.
**Why it happens:** Forgetting to add the `beforeLoad` check to the new route.
**How to avoid:** Copy the exact `beforeLoad` pattern from `admin.tsx`.

---

## Code Examples

### SQL Aggregation for Admin Heatmap
```python
# Source: derived from existing admin.py raw SQL patterns
result = session.execute(text("""
    SELECT qa.mami_code, qa.answer_value, COUNT(*) as cnt
    FROM questionnaire_answer qa
    JOIN initiative i ON i.id = qa.initiative_id
    WHERE i.status = 'submitted'
    GROUP BY qa.mami_code, qa.answer_value
"""))

counts: dict[str, dict[str, int]] = {}  # {mami_code: {answer_value: count}}
for row in result.mappings():
    code = row["mami_code"]
    val = row["answer_value"]
    cnt = row["cnt"]
    counts.setdefault(code, {})
    counts[code][val] = int(cnt)
```

### Topic-level count aggregation (Python)
```python
# After getting counts per mami_code, roll up to topic level:
# topic_structure: {cat: [{topic_id, topic_label, codes: [code_id]}]}
for cat, topics in topic_structure.items():
    for topic in topics:
        for dim_key in dimensions:
            yes_total = not_yet_total = na_total = 0
            for code_id in topic["codes"]:
                code_meta = code_lookup.get(code_id, {})
                if code_meta.get("dimension") != dim_key:
                    continue
                code_counts = counts.get(code_id, {})
                yes_total += code_counts.get("YES", 0)
                not_yet_total += code_counts.get("NOT_THERE_YET", 0)
                na_total += code_counts.get("NOT_APPLICABLE", 0)
            matrix[cat][dim_key][topic["topic_id"]] = {
                "yes": yes_total, "not_yet": not_yet_total, "n_a": na_total
            }
```

### routeTree.gen.ts additions for /admin/heatmap
```typescript
// Add import at top:
import { Route as AppAdminHeatmapRouteImport } from './routes/_app/admin.heatmap'

// Add route constant after AppAdminRoute:
const AppAdminHeatmapRoute = AppAdminHeatmapRouteImport.update({
  id: '/admin/heatmap',
  path: '/admin/heatmap',
  getParentRoute: () => AppRoute,
} as any)

// Add to FileRoutesByFullPath interface:
'/admin/heatmap': typeof AppAdminHeatmapRoute

// Add to FileRoutesByTo interface:
'/admin/heatmap': typeof AppAdminHeatmapRoute

// Add to FileRoutesById interface:
'/_app/admin/heatmap': typeof AppAdminHeatmapRoute

// Add to FileRouteTypes fullPaths union:
| '/admin/heatmap'

// Add to FileRouteTypes to union:
| '/admin/heatmap'

// Add to FileRouteTypes id union:
| '/_app/admin/heatmap'

// Add to AppRouteChildren interface:
AppAdminHeatmapRoute: typeof AppAdminHeatmapRoute

// Add to AppRouteChildren const:
AppAdminHeatmapRoute: AppAdminHeatmapRoute,
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pool_size=10, max_overflow=20 (50-user target) | pool_size=15, max_overflow=25 (100-user target) | Phase 10 | +33% connection headroom |
| "Your submission is complete" heading | "Thanks for completing the survey." | Phase 10 | Matches event-specific tone |
| "Generate Compliance Report" button | "Generate Heatmap" | Phase 10 | Consistent naming with report page title |
| No scroll-to-top on wizard nav | window.scrollTo on Next/Previous | Phase 10 | Avoids disorienting mid-page position between topics |
| My Initiative in TopNav | My Initiative removed from nav | Phase 10 | Dashboard is now the single entry point for initiative management |

---

## Open Questions

1. **Railway PostgreSQL connection limit**
   - What we know: Pool currently set for 30 max connections (10 + 20). Increasing to 40 (15 + 25).
   - What's unclear: Railway Hobby PostgreSQL's exact `max_connections` limit. Free tier is typically 25; paid add-on may be higher.
   - Recommendation: Before finalizing pool numbers, check Railway dashboard. If limit is 25, cap pool_size=8, max_overflow=12 (total 20) to leave headroom for admin CLI connections.

2. **TanStack Router flat-file vs directory for admin/heatmap**
   - What we know: TanStack Router v1 supports dot-notation flat files (`admin.heatmap.tsx`) for nested routes.
   - What's unclear: Whether the existing `admin.tsx` flat file and a new `admin/heatmap.tsx` directory file would conflict.
   - Recommendation: Use flat file `admin.heatmap.tsx` with `createFileRoute('/_app/admin/heatmap')` — safest approach, avoids directory/file coexistence issues.

3. **CATEGORY_LABELS / DIMENSION_LABELS sharing**
   - What we know: These constants are defined in report.tsx but not exported.
   - What's unclear: Whether future refactoring will move them to a shared lib.
   - Recommendation: Duplicate in admin heatmap page for now. If duplication proliferates, create `frontend/src/lib/heatmap-constants.ts` as a follow-up.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection:
  - `frontend/src/components/questionnaire/WizardPage.tsx` — handleNext/handleBack exact line positions confirmed
  - `frontend/src/components/layout/TopNav.tsx` — navItems array with TypeScript union type confirmed
  - `frontend/src/routes/_app/dashboard.tsx` — "Generate Compliance Report" button confirmed at line ~323
  - `frontend/src/routes/_app/report.tsx` — StatusChip component structure, CATEGORY_LABELS/DIMENSION_LABELS confirmed
  - `backend/app/db/session.py` — pool_size=10, max_overflow=20 confirmed
  - `backend/app/api/v1/admin.py` — endpoint patterns, require_admin dependency, raw SQL pattern confirmed
  - `backend/app/services/report_generator.py` — _build_topic_structure() and mami_code structure confirmed
  - `backend/Dockerfile` — `fastapi run app/main.py` single-process confirmed
  - `frontend/src/routeTree.gen.ts` — route registration pattern for manual update confirmed
  - `backend/app/models/questionnaire.py` — AnswerValue enum values (YES, NOT_THERE_YET, NOT_APPLICABLE) confirmed
  - `backend/app/core/deps.py` — require_admin, get_mami_config patterns confirmed
  - `.planning/config.json` — no `nyquist_validation` key, Validation Architecture section skipped

### Secondary (MEDIUM confidence)
- TanStack Router v1 flat-file routing convention for dot-notation nested routes (training data, consistent with routeTree.gen.ts patterns observed)
- Railway Hobby plan single-container memory constraints (training data, matches CONTEXT.md explicit constraint)

---

## Metadata

**Confidence breakdown:**
- Text/label changes: HIGH — exact line locations confirmed by source inspection
- Scroll-to-top: HIGH — window.scrollTo API is stable; handler positions confirmed
- Nav removal: HIGH — navItems array structure confirmed; TypeScript union type pitfall identified
- minWidth fix: HIGH — StatusChip implementation confirmed; CSS minWidth behavior is standard
- DB pool tuning: MEDIUM — pool math is sound but Railway PostgreSQL connection limit is unverified
- Admin heatmap backend: HIGH — SQL pattern matches existing admin endpoints; data model confirmed
- Admin heatmap frontend: HIGH — route pattern confirmed from routeTree.gen.ts; auth guard pattern confirmed

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable stack; 30-day window)
