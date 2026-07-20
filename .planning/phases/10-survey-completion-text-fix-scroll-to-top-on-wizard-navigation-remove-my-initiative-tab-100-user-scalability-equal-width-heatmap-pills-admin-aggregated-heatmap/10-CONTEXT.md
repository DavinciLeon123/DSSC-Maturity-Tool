# Phase 10: UX Polish, Scalability & Admin Heatmap - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Seven targeted improvements: (1) fix survey completion heading text, (2) rename dashboard button, (3) scroll-to-top on wizard navigation, (4) remove "My Initiative" nav tab, (5) upgrade to 100-user concurrency, (6) equal-width heatmap pills, (7) new /admin/heatmap page with aggregated counts per cell across all submitted initiatives.

</domain>

<decisions>
## Implementation Decisions

### Survey completion text
- Heading: change "Your submission is complete" → "Thanks for completing the survey."
- Dashboard button: change "Generate Compliance Report" → "Generate Heatmap"
- (The WizardPage "Generate heatmap" button label is already correct from Phase 9 — no change needed there)

### Scroll-to-top
- Trigger: on every Next and Previous button click in WizardPage
- Implementation: `window.scrollTo({ top: 0, behavior: 'smooth' })` (or 'instant') inside the existing handleNext / handlePrevious handlers
- Not required on StepPills category click or on wizard mount

### Remove My Initiative tab
- Remove the `{ label: 'My Initiative', to: '/initiative' }` entry from `navItems` in `TopNav.tsx`
- The /initiative route file can remain (no hard delete needed — just hidden from nav)

### 100-user scalability
- Context: single breakout session event, ~200 total attendees, peak ~100 concurrent
- Railway Hobby plan constraints: single container, limited RAM
- Approach: Claude's discretion — pick what's safe for a Hobby-tier single-container deployment
  - Options: increase DB pool, add uvicorn workers if Railway supports it, or tune existing settings
  - Do NOT introduce gunicorn if it complicates the Railway single-process model
  - Priority: stability over raw throughput — this is a one-off event demo, not production SLA

### Equal-width heatmap pills
- Use `minWidth` (not fixed `width`) on the StatusChip span so all pills share a minimum width
- Text stays centered; no clipping risk
- Apply to the heatmap chip cells only (not the legend at the bottom)

### Admin aggregated heatmap
- **Route:** New page at `/admin/heatmap` (separate route, not a tab on /admin)
- **Access:** Link from existing /admin page — add a button "View Aggregated Heatmap →" at the top of the admin users panel
- **Data source:** Only initiatives with `status = 'submitted'` are counted
- **Cell content:** 3 count pills per cell — green (yes count), blue (not_yet count), grey (n_a count)
  - Unanswered is implicit (total submitted minus the three counts) — not displayed as a pill
- **Layout:** Same 9×3 matrix as the user heatmap (4 category group headers + 9 topic rows × 3 dimensions)
- **Backend:** New endpoint `GET /admin/heatmap` that aggregates QuestionnaireAnswer rows for all submitted initiatives, maps to matrix structure, returns counts per cell

</decisions>

<specifics>
## Specific Ideas

- The event will host ~200 people in a breakout session; peak concurrent load is ~100
- Railway Hobby plan: single container — don't add complexity that breaks single-process deployment
- "Generate Compliance Report" button on Dashboard is the one that needs renaming (WizardPage button is already "Generate heatmap" from Phase 9)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `StatusChip` (report.tsx): already used in heatmap — reuse with added `minWidth` for equal-width fix and in admin heatmap cells (count variant needed)
- `HeatmapMatrix` (report.tsx): same structure used for admin heatmap, but cells show 3 count pills instead of 1 status chip
- `CATEGORY_LABELS`, `DIMENSION_LABELS`, `DIMENSION_LABELS_MOBILE` (report.tsx): shared constants, import or duplicate in admin heatmap page

### Established Patterns
- `fastapi run app/main.py` in Dockerfile CMD — single-process uvicorn; scalability change must stay compatible
- `pool_size=10, max_overflow=20` in `backend/app/db/session.py` — increase for 100 users
- `TopNav.tsx` navItems array: simple array edit to remove My Initiative entry
- TanStack Router file-based routing: new `/admin/heatmap` route needs a new file at `frontend/src/routes/_app/admin/heatmap.tsx` (or `admin.heatmap.tsx` flat file)
- Admin auth guard: existing `/admin` route uses `require_admin` dependency — new `/admin/heatmap` backend endpoint must do the same

### Integration Points
- WizardPage.tsx `handleNext` / `handlePrevious`: add `window.scrollTo` call at start of each handler
- dashboard.tsx: one button label change ("Generate Compliance Report" → "Generate Heatmap")
- WizardPage.tsx submitted block: heading text change
- TopNav.tsx navItems: remove My Initiative entry
- backend/app/db/session.py: pool_size / max_overflow tuning
- backend/app/api/v1/admin.py: new `/admin/heatmap` endpoint
- routeTree.gen.ts: must be updated for new admin heatmap route (per project convention of committing generated file)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-survey-completion-text-fix-scroll-to-top-on-wizard-navigation-remove-my-initiative-tab-100-user-scalability-equal-width-heatmap-pills-admin-aggregated-heatmap*
*Context gathered: 2026-03-10*
