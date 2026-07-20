# Phase 9: UX Improvements — Research

**Researched:** 2026-03-09
**Domain:** React/TypeScript frontend UX — dashboard forms, wizard completion flow, report heatmap expansion, mobile responsiveness
**Confidence:** HIGH (all findings from direct source code inspection)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
1. **Initiative Registration on Dashboard:** Inline form on Dashboard when user has no initiative. Required fields: Initiative Name + Sector. All other fields (organization, contact_name, contact_email, description) become optional.
2. **Remove Role Label:** Remove "Role: USER / ADMIN" text from dashboard.tsx completely.
3. **Initiative Details + Questionnaire CTA:** Dashboard shows initiative details after registration. CTA: "Start Questionnaire" (no prior attempt) or "Retake Questionnaire" (already submitted).
4. **Post-Questionnaire Flow:** Completion page in WizardPage.tsx navigates to `/report` (not `/dashboard`). Body text: "Thank you for completing the MAMI Questionnaire. You can now view your MAMI Interoperability heatmap." Button label: "Generate heatmap".
5. **Expanded Report Heatmap:** Top-level categories (Scheme, Participants, Data, Services) become group headers with no chips. Second-level topics (from mami-framework.json `topic_label` field) get their own rows with yes/not_yet/n_a chips per dimension column.
6. **Mobile Responsive Design:** Questionnaire wizard and /report page. Collapse two-column layouts at 768px breakpoint. Minimum target: 375px.

### Claude's Discretion
- Which route/component handles the "submission complete" page (answer: WizardPage.tsx, `if (submitted)` block at line 296)
- How to detect "questionnaire already completed" (answer: `initiative.status === "submitted"`)
- How to get second-level topic data from backend for expanded heatmap
- Whether backend matrix already groups by topic or needs an update

### Deferred Ideas (OUT OF SCOPE)
- Admin dashboard UX improvements
- PDF export / report download (Phase 5)
- Evidence crawling (Phase 5)
</user_constraints>

---

## Summary

Phase 9 is a pure frontend phase with one backend schema change. All six improvements build on existing, well-understood code. No new routes, no new API endpoints, and no database migrations are required — except for making `contact_name`, `contact_email`, and `organization` optional in the `InitiativeCreate` Pydantic schema (they are currently required).

The most complex improvement is the expanded heatmap (#5), which requires restructuring `HeatmapMatrix` in `report.tsx` to derive topic-level rows from `mami-framework.json` data already available in the backend response. The backend `_build_matrix()` already stores `{category: {dimension: {mami_code: status}}}` and each code in `mami-framework.json` already carries `topic` and `topic_label` fields — so the expansion is a frontend rendering change plus adding `topics` metadata to the report JSON response.

**Primary recommendation:** Implement in five plans — (1) backend schema loosening, (2) dashboard inline registration + role label removal, (3) dashboard initiative details + questionnaire CTA, (4) wizard completion screen text/nav fix, (5) expanded heatmap + mobile responsive.

---

## Critical Questions Answered

### 1. Where is the current initiative registration form?

`frontend/src/routes/_app/initiative.tsx` — the `InitiativePage` component. It renders a form when `GET /initiatives/me` returns 404. This form currently requires name, organization, contact_name, contact_email, sector, and description (optional). The Dashboard page currently shows a card saying "Use the menu to navigate to My Initiative to register your DSI initiative" when no initiative exists.

### 2. What fields does the Initiative model have? Which are required vs optional?

**DB Model (`backend/app/models/initiative.py`):**
| Field | Python Type | Optional in DB? |
|-------|-------------|-----------------|
| name | str (min 2, max 200) | No |
| description | Optional[str] | Yes |
| sector | str | No |
| sector_other | Optional[str] | Yes |
| contact_name | str | No (currently) |
| contact_email | str | No (currently) |
| organization | str | No (currently) |
| participant_type | ParticipantType | No (default=dsi) |
| status | InitiativeStatus | No (default=draft) |

**Pydantic schema (`backend/app/schemas/initiative.py` — `InitiativeCreate`):**
- `name`: required
- `sector`: required (validated against SECTOR_OPTIONS)
- `contact_name`: required — **must be made Optional[str] = None**
- `contact_email`: EmailStr, required — **must be made Optional[EmailStr] = None**
- `organization`: required — **must be made Optional[str] = None**
- `description`: Optional[str] = None (already optional)
- `sector_other`: Optional[str] = None (already optional)

**DB-level columns** for contact_name, contact_email, organization are `str` without `Optional` — they must also be made `Optional[str] = None` in the model itself to avoid DB NOT NULL errors when omitted.

### 3. What does the submission complete screen look like and which file contains it?

`frontend/src/components/questionnaire/WizardPage.tsx`, lines 296–354. It is an inline conditional render (`if (submitted) { return ... }`), not a separate route. Triggered when `submitMutation.mutateAsync()` resolves successfully (onSuccess sets `setSubmitted(true)`).

Current state:
- Title: "Your submission is complete"
- Body: "Thank you for completing the MAMI questionnaire. You can now generate your compliance report."
- Button label: "Generate Report"
- Button action: `navigate({ to: "/dashboard" })`

Required changes:
- Body text change (exact wording per CONTEXT.md)
- Button label: "Generate heatmap"
- Button action: Must call `POST /initiatives/{id}/report/data` then `navigate({ to: "/report" })` — mirrors the `handleGenerateReport` function currently in dashboard.tsx. WizardPage already has access to `initiativeId` prop.

### 4. Does the backend matrix already break down by topic? What changes are needed?

The backend `_build_matrix()` produces: `{category: {dimension: {mami_code: status}}}`.

Example actual output:
```json
{
  "scheme": {
    "human_readable": { "S-HRA-1.1": "yes", "S-HRA-2.1": "not_yet", "S-HRA-3.1": "unanswered" },
    "machine_readable": { ... },
    "trust_anchors": { ... }
  },
  ...
}
```

The `mami-framework.json` config already has `topic` and `topic_label` on every code entry. The backend `generate_report_data()` does NOT currently include topic metadata in its output — it only exposes the matrix and a flat answers list.

**Two approaches for the expanded heatmap:**

**Option A (frontend-only):** The matrix codes follow a naming pattern (`S-HRA-1.1`, `S-HRA-2.1`, `S-HRA-3.1` where the `1`, `2`, `3` suffix is the topic number). The frontend can request the questionnaire config (already fetched on the questionnaire page) to get topic labels — but report.tsx doesn't have access to it currently.

**Option B (extend report JSON):** Add a `topics` key to `generate_report_data()` output containing `{category: [{topic_id, topic_label, codes: [code_id]}]}`. Frontend uses this to render topic rows. No DB migration needed — this is a pure response shape change.

**Recommendation: Option B.** The mami-framework.json is already loaded as `mami_config` in the endpoint — extracting topic structure is trivial. This keeps the frontend decoupled from config knowledge.

Required backend change in `report_generator.py` — add `_build_topic_structure(mami_config)` helper and include in `generate_report_data()` output. No migration. No endpoint signature change.

### 5. How is "questionnaire completed" status determined on the frontend?

`GET /initiatives/me` returns `{ status: "draft" | "active" | "submitted" }`. The submit endpoint sets `status = "submitted"`. Therefore:
- `initiative.status === "submitted"` → show "Retake Questionnaire" button
- `initiative.status !== "submitted"` → show "Start Questionnaire" button

This is safe and reliable — status is only "submitted" after `POST /initiatives/{id}/submit` succeeds.

### 6. What is the current two-column layout approach? What is the responsive strategy?

**WizardPage.tsx** (lines 373–390):
```tsx
<div style={{
  maxWidth: "1100px",
  margin: "0 auto",
  display: "flex",
  gap: "2rem",
  alignItems: "flex-start",
}}>
  <StepPills ... />          {/* width: 260px, flexShrink: 0 */}
  <div style={{ flex: 1 }}> {/* question card area */}
```
No responsive handling. StepPills has `position: sticky, top: 80px`.

**report.tsx** (lines 356–432):
```tsx
<div style={{
  display: "flex",
  gap: "24px",
  alignItems: "flex-start",
  flexWrap: "wrap",
}}>
  <div style={{ flex: "2 1 520px" }}>  {/* Heatmap card */}
  <div style={{ flex: "1 1 280px" }}>  {/* Next steps card */}
```
Uses `flexWrap: "wrap"` with `flex-basis` — this naturally collapses when viewport is too narrow for 520px minimum. However, inner heatmap grid (`gridTemplateColumns: "200px repeat(3, 1fr)"`) will overflow on mobile.

**Responsive strategy for mobile:**
- WizardPage: Collapse StepPills (hide or move above card) at 768px. Use `@media` query — but inline styles don't support media queries.
- Options: (a) CSS class via a `<style>` tag or separate `.css` import, (b) inline conditional using `window.innerWidth` / `useWindowSize` hook, (c) antd `useBreakpoint()` hook (preferred — already using antd).
- report.tsx HeatmapMatrix grid: Change column definition at mobile from `"200px repeat(3, 1fr)"` to a stacked layout, or reduce label column width.

**Recommended approach:** Use antd `Grid.useBreakpoint()` hook (from `antd`) to get `{ xs, sm, md, lg }` booleans. `xs: true` and no `md` = mobile. This avoids CSS file creation and stays consistent with the project's antd pattern.

---

## Standard Stack

### Core (already in use — no new installs)
| Library | Version | Purpose |
|---------|---------|---------|
| antd | ^5.x | UI components (Card, Button, Input, Select, Alert) |
| @tanstack/react-router | ^1.x | Navigation (useNavigate) |
| @tanstack/react-query | ^5.x | API mutations (useMutation) |
| React | ^18.x | Component framework |

### New Utility
| Library | Purpose | Notes |
|---------|---------|-------|
| `antd` Grid.useBreakpoint | Responsive breakpoint detection | Already installed — just import `Grid` from `antd` |

**No new npm installs required.**

---

## Architecture Patterns

### Pattern 1: Dashboard Inline Registration Form

The `DashboardPage` currently fetches `GET /initiatives/me` and catches 404. The pattern to extend:

```typescript
// Current: catch 404, do nothing
api.get<Initiative>("/initiatives/me")
  .then(res => setInitiative(res.data))
  .catch(() => { /* no initiative */ });

// Phase 9: catch 404, set hasNoInitiative = true
// Render inline form when hasNoInitiative && !initiative
```

The Initiative interface in dashboard.tsx must be expanded to include `status` and `sector` fields (currently only has `id, name, status`).

### Pattern 2: Questionnaire CTA Based on Status

```typescript
// After successful initiative load:
{initiative.status === "submitted" ? (
  <Button onClick={() => navigate({ to: "/questionnaire" })}>Retake Questionnaire</Button>
) : (
  <Button onClick={() => navigate({ to: "/questionnaire" })}>Start Questionnaire</Button>
)}
```

### Pattern 3: WizardPage Completion Screen — Generate Heatmap

The completion screen needs `initiativeId` to call `POST /report/data` before navigating. `initiativeId` is already a prop on `WizardPage`. The action mirrors `handleGenerateReport` in dashboard.tsx:

```typescript
// In completion screen handler:
await api.post(`/initiatives/${initiativeId}/report/data`, {});
navigate({ to: "/report" });
```

Use `useState` for loading/error on the completion screen (same pattern as dashboard.tsx `handleGenerateReport`).

### Pattern 4: Expanded Heatmap — Topic Structure from Backend

New backend helper `_build_topic_structure(mami_config)` returns:
```python
{
  "scheme": [
    {"topic_id": "scheme_pub_updates", "topic_label": "Scheme publication & updates", "codes": ["S-HRA-1.1", "S-MRA-1.1", "S-TA-1.1"]},
    {"topic_id": "incidents_dispute",   "topic_label": "Incidents & dispute management", "codes": ["S-HRA-2.1", ...]},
    ...
  ],
  "participants": [...],
  "data": [...],
  "services": [...]
}
```

Included in `generate_report_data()` response as `"topic_structure"` key.

Frontend `HeatmapMatrix` renders two row types:
1. **Category header row:** Full-width navy label, no chips (spans all 4 grid columns)
2. **Topic data row:** Indented topic label + 3 chip cells (one per dimension)

For each topic row, the chip status = aggregate of all codes in that topic+dimension intersection.

### Pattern 5: Responsive with antd useBreakpoint

```typescript
import { Grid } from "antd";
const { useBreakpoint } = Grid;

function WizardPage(...) {
  const screens = useBreakpoint();
  const isMobile = !screens.md; // md = 768px

  // Conditional layout:
  return isMobile ? (
    <div style={{ flexDirection: "column" }}>
      {/* StepPills above card, collapsed */}
    </div>
  ) : (
    <div style={{ display: "flex" }}>
      {/* Two-column layout */}
    </div>
  );
}
```

### Recommended File Change Map

| File | Change |
|------|--------|
| `backend/app/schemas/initiative.py` | Make contact_name, contact_email, organization Optional |
| `backend/app/models/initiative.py` | Make contact_name, contact_email, organization Optional[str] = None |
| `backend/app/services/report_generator.py` | Add `_build_topic_structure()`, include in `generate_report_data()` output |
| `frontend/src/routes/_app/dashboard.tsx` | Add inline registration form, remove role label, add initiative details + CTA |
| `frontend/src/components/questionnaire/WizardPage.tsx` | Fix completion screen text, button label, navigate to /report |
| `frontend/src/routes/_app/report.tsx` | Expand HeatmapMatrix with topic rows, add mobile responsive |
| `frontend/src/components/questionnaire/WizardPage.tsx` | Add mobile responsive two-column collapse |

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Responsive breakpoints | Custom useWindowSize hook + resize listener | `antd` `Grid.useBreakpoint()` — already in project |
| Form field validation | Manual regex validators | Rely on existing antd Input `required` + Pydantic schema validators on backend |
| Sector dropdown | Custom select element | antd `Select` — already used in initiative.tsx |
| Loading state on completion screen | Complex state machine | Simple `useState` + try/finally pattern (same as dashboard.tsx handleGenerateReport) |

---

## Common Pitfalls

### Pitfall 1: Making contact_name/contact_email/organization Optional in Schema But Not Model

**What goes wrong:** Pydantic schema allows None, but SQLModel model has `str` without Optional — PostgreSQL NOT NULL constraint fires.
**How to avoid:** Update BOTH `Initiative` model (`Optional[str] = None`) AND `InitiativeCreate` schema.
**Warning signs:** 500 error from backend on initiative creation with missing fields.

### Pitfall 2: Dashboard InitiativeRead Interface is Narrow

**What goes wrong:** dashboard.tsx currently declares `interface Initiative { id: number; name: string; status: string; }` — missing `sector`, `contact_email`, `organization` needed for the details display.
**How to avoid:** Expand the dashboard's local `Initiative` interface to match the full `InitiativeRead` schema.

### Pitfall 3: WizardPage Completion Screen Lacks initiativeId for Report Call

**What goes wrong:** The completion screen is an inline render within WizardPage — `initiativeId` is available as a prop. Don't navigate to dashboard and rely on dashboard to call the report endpoint.
**How to avoid:** Call `POST /initiatives/${initiativeId}/report/data` directly in the completion screen handler before `navigate({ to: "/report" })`.

### Pitfall 4: antd useBreakpoint SSR Caveat

**What goes wrong:** `useBreakpoint` returns empty object on first render (before hydration/layout effect). Accessing `screens.md` before it's populated could cause flash.
**How to avoid:** Default to desktop layout when `screens.md` is undefined (i.e. `const isMobile = screens.md === false` not `!screens.md`). This ensures no layout flash.

### Pitfall 5: Heatmap Grid Overflow on Mobile

**What goes wrong:** The heatmap uses `gridTemplateColumns: "200px repeat(3, 1fr)"` — on 375px viewport the 200px label column + 3 chip columns will overflow.
**How to avoid:** On mobile, reduce label column to `120px` or switch to a stacked card layout per topic row. The chips are `whiteSpace: "nowrap"` — they won't wrap. Consider abbreviating dimension labels on mobile ("HR" / "MR" / "TA") or hiding the dimension header labels and adding a legend.

### Pitfall 6: Report Page Two-Step Fetch Pattern

**What goes wrong:** The report.tsx currently calls `POST /report/data` (which regenerates scoring). The completion screen also calls this. If the user navigates to `/report` immediately after completion, there's a double call.
**How to avoid:** The completion screen calls POST then navigates. report.tsx uses the SAME POST on mount. This double-call is acceptable since POST /report/data is idempotent. No change needed to report.tsx fetch logic.

### Pitfall 7: topic_structure in Report Response Needs TypeScript Type

**What goes wrong:** report.tsx currently types `data.matrix` as `ReportMatrix` — adding `topic_structure` requires new TypeScript interfaces.
**How to avoid:** Add TypeScript types `TopicEntry`, `TopicStructure` to report.tsx before using them in `HeatmapMatrix`.

---

## Code Examples

### Expanded Heatmap — Backend Topic Structure Builder

```python
# Source: derived from mami-framework.json structure (directly inspected)
def _build_topic_structure(mami_config: dict) -> dict:
    """Build per-category topic order with code lists.

    Returns: {category: [{topic_id, topic_label, codes: [code_id]}]}
    """
    from collections import OrderedDict
    structure: dict = {}
    seen: dict = {}  # category -> {topic_id -> index}

    for code in mami_config.get("codes", []):
        cat = code["category"]
        topic_id = code["topic"]
        topic_label = code.get("topic_label", topic_id)
        code_id = code["id"]

        if cat not in structure:
            structure[cat] = []
            seen[cat] = {}

        if topic_id not in seen[cat]:
            seen[cat][topic_id] = len(structure[cat])
            structure[cat].append({"topic_id": topic_id, "topic_label": topic_label, "codes": []})

        structure[cat][seen[cat][topic_id]]["codes"].append(code_id)

    return structure
```

### Dashboard Inline Registration — Minimal Form State

```typescript
// Source: derived from initiative.tsx existing pattern
const [regForm, setRegForm] = useState({ name: "", sector: "", sector_other: "" });
const [regLoading, setRegLoading] = useState(false);
const [regError, setRegError] = useState<string | null>(null);

async function handleRegisterInitiative(e: React.FormEvent) {
  e.preventDefault();
  setRegLoading(true);
  setRegError(null);
  try {
    const body: Record<string, string | undefined> = {
      name: regForm.name,
      sector: regForm.sector,
    };
    if (regForm.sector === "Other" && regForm.sector_other) {
      body.sector_other = regForm.sector_other;
    }
    const res = await api.post<FullInitiative>("/initiatives", body);
    setInitiative(res.data);
  } catch (err: unknown) {
    const apiErr = err as { response?: { data?: { detail?: string } } };
    setRegError(apiErr.response?.data?.detail ?? "Failed to register initiative");
  } finally {
    setRegLoading(false);
  }
}
```

### Expanded HeatmapMatrix — Rendering Pattern

```typescript
// Source: derived from existing report.tsx HeatmapMatrix + mami-framework.json structure
function HeatmapMatrix({ matrix, topicStructure }: { matrix: ReportMatrix; topicStructure: TopicStructure }) {
  const categories = Object.keys(CATEGORY_LABELS) as Array<keyof ReportMatrix>;

  return (
    <div>
      {/* Header row — unchanged */}
      ...
      {categories.map((cat) => (
        <div key={cat}>
          {/* Category group header — no chips */}
          <div style={{ gridTemplateColumns: "1fr", background: "rgba(6,0,79,0.06)", padding: "10px 16px" }}>
            <strong>{CATEGORY_LABELS[cat]}</strong>
          </div>
          {/* Topic rows */}
          {topicStructure[cat].map((topic) => (
            <div key={topic.topic_id} style={{ display: "grid", gridTemplateColumns: "200px repeat(3, 1fr)", padding: "12px 16px" }}>
              <div style={{ paddingLeft: "1rem", fontSize: "0.875rem" }}>{topic.topic_label}</div>
              {DIMENSION_LABELS.map((dim) => {
                // Aggregate codes for this topic+dimension intersection
                const cellCodes = topic.codes.filter(c => matrix[cat][dim.key][c] !== undefined);
                const statuses = cellCodes.map(c => matrix[cat][dim.key][c]).filter(Boolean);
                const status = aggregateStatusList(statuses);
                return (
                  <div key={dim.key} style={{ display: "flex", justifyContent: "center" }}>
                    <StatusChip status={status} />
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
```

### Mobile Responsive — antd useBreakpoint

```typescript
// Source: antd Grid.useBreakpoint docs pattern
import { Grid } from "antd";
const { useBreakpoint } = Grid;

// In component:
const screens = useBreakpoint();
const isMobile = screens.md === false; // false means < 768px, undefined means not yet determined

// WizardPage two-column layout:
<div style={{
  maxWidth: "1100px",
  margin: "0 auto",
  display: "flex",
  flexDirection: isMobile ? "column" : "row",
  gap: "2rem",
  alignItems: "flex-start",
}}>
  {/* On mobile, StepPills renders before card but collapsed */}
  {!isMobile && <StepPills ... />}
  <div style={{ flex: 1, minWidth: 0 }}>
    {/* On mobile, show current category/topic as simple header instead of StepPills */}
    ...
  </div>
</div>
```

---

## Topic Structure in mami-framework.json — Complete Mapping

From direct file inspection (mami-framework.json, 28 codes total):

| Category | Topic ID | Topic Label | Codes |
|----------|----------|-------------|-------|
| scheme | scheme_pub_updates | Scheme publication & updates | S-HRA-1.1, S-MRA-1.1, S-TA-1.1 |
| scheme | incidents_dispute | Incidents & dispute management | S-HRA-2.1, S-MRA-2.1, S-TA-2.1 |
| scheme | traceability | Traceability | S-HRA-3.1, S-MRA-3.1, S-TA-3.1 |
| participants | onboarding | On(off)-boarding | PM-HRA-1.1, PM-MRA-1.1, PM-TA-1.1 |
| participants | participants_discovery | Participants discovery | PM-HRA-2.1, PM-MRA-2.1, PM-TA-2.1 |
| data | data_pub_discovery | Data(sets) Publication & discovery | D-HRA-1.1, D-MRA-1.1, D-TA-1.1 |
| data | data_provisions | Data(sets) Provisions | D-HRA-2.1, D-MRA-2.1, D-TA-2.1 |
| services | services_pub_discovery | Services Publications and discovery | SER-HRA-1.1, SER-MRA-1.1, SER-TA-1.1 |
| services | services_provisions | Services Provisions | SER-HRA-2.1, SER-MRA-2.1, SER-TA-2.1 |

**Heatmap expansion result:** 4 category headers + 9 topic rows = 13 rows total (was 4 rows).

Each topic row always has exactly 3 codes (one per dimension) in the current config, so each chip cell will show a single code's status — no aggregation ambiguity for current data.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Navigate to /dashboard after submit | Navigate to /report after submit | Phase 9 change |
| "Generate Report" button label | "Generate heatmap" button label | Phase 9 change |
| 4-row heatmap (category level) | 13-row heatmap (category headers + topic rows) | Phase 9 change |
| Initiative registration on /initiative route | Inline on Dashboard | Phase 9 change |
| contact_name/contact_email/org required | Optional in Phase 9 | Requires schema + model change |

---

## Open Questions

1. **Mobile StepPills on questionnaire wizard**
   - What we know: StepPills is 260px wide, sticky. On mobile there's no space for two-column layout.
   - What's unclear: Should StepPills be hidden entirely on mobile, collapsed to a progress bar, or shown above the card?
   - Recommendation: Hide StepPills on mobile and show a compact "Category X of Y — Topic Y of Z" text indicator in the card header. This is the simplest approach and avoids a large StepPills refactor.

2. **initiative.tsx — does it need changes?**
   - What we know: The "My Initiative" page in the nav still exists. If registration moves to Dashboard, the /initiative page becomes an edit-only view.
   - What's unclear: Should the nav item "My Initiative" still show for users without an initiative (pointing them to Dashboard)?
   - Recommendation: Out of scope — leave /initiative as-is. Users without an initiative who navigate there will see the registration form there too (current behavior). The Dashboard improvement is additive.

3. **"Generate heatmap" on completion screen — error handling**
   - What we know: The API call can fail (e.g. no answers saved).
   - What's unclear: What should the UX be if report generation fails on the completion screen?
   - Recommendation: Show an inline error Alert on the completion screen (same as dashboard.tsx reportError pattern). Keep the "Generate heatmap" button enabled for retry.

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `frontend/src/routes/_app/dashboard.tsx` — dashboard current state
- Direct code inspection of `frontend/src/routes/_app/report.tsx` — heatmap layout, matrix type, fetch pattern
- Direct code inspection of `frontend/src/components/questionnaire/WizardPage.tsx` — completion screen location, layout approach
- Direct code inspection of `frontend/src/routes/_app/initiative.tsx` — existing registration form fields
- Direct code inspection of `backend/app/models/initiative.py` — Initiative model fields
- Direct code inspection of `backend/app/schemas/initiative.py` — InitiativeCreate required fields
- Direct code inspection of `backend/app/services/report_generator.py` — _build_matrix output shape, generate_report_data shape
- Direct code inspection of `backend/app/api/v1/reports.py` — POST /report/data endpoint
- Direct code inspection of `config/mami-framework.json` — full topic structure (28 codes, 9 topics, 4 categories)
- Direct code inspection of `frontend/src/components/questionnaire/StepPills.tsx` — layout and responsive gaps

### Secondary (MEDIUM confidence)
- antd `Grid.useBreakpoint()` — well-documented antd v5 pattern; antd already installed in project

---

## Metadata

**Confidence breakdown:**
- Initiative model/schema fields: HIGH — directly inspected source
- Completion screen location and changes: HIGH — directly inspected WizardPage.tsx
- Backend matrix structure and topic expansion approach: HIGH — inspected report_generator.py and mami-framework.json
- Responsive implementation approach (antd useBreakpoint): HIGH — antd already in project
- Topic-to-row mapping counts: HIGH — read full mami-framework.json

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable codebase)
