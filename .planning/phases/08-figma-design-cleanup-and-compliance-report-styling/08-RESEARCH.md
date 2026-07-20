# Phase 8: Figma Design Cleanup and Compliance Report Styling - Research

**Researched:** 2026-03-07
**Domain:** React/TypeScript UI alignment + TanStack Router routing + report restyle
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Phase Boundary:** Fix 9 Figma alignment gaps across the frontend and replace the backend compliance report with a Figma-spec design. No new features — only visual alignment and content corrections.

**9 items in scope:**
1. "Question X of X" pill → move to top-right corner of the question card (currently inline next to topic label)
2. Progress tracker left sidebar → show topic (sub-category) names under the active category
3. Questionnaire navigation → "Vorige" / "Volgende" → "Previous" / "Next" (+ "Voltooien" → "Finish")
4. Login page → add CoE DSC logo
5. Register page → add CoE DSC logo
6. Forgot-password page → add CoE DSC logo
7. Homepage → add CoE DSC logo
8. Homepage → replace Dutch text with English, restyle to match Figma (node 154-3458)
9. Compliance Report → full restyle to match Figma design (node 154-4667)

**Compliance Report (item 9) — Full redesign:**
- Figma URL: https://www.figma.com/design/V3v7Oq6DfXMpQ86llyVCQ0/MAMI-tool?node-id=154-4667
- Scoring model: Switch from CRITICAL/NON_CRITICAL to yes / not yet / n/a
  - Backend maps: YES → "yes" (green chip), NOT_THERE_YET → "not yet" (blue chip), NOT_APPLICABLE → "n/a" (grey chip)
  - Remove severity/MoSCoW language from report output
- Layout: Two-column — heatmap matrix left + "Next steps" card right
- Heatmap: Replace old `<table>` with chip/pill rows per category × 3 dimensions
  - Chip colors: yes = `rgba(57,158,90,0.2)` bg + checkmark icon; not yet = `rgba(61,82,213,0.2)` bg + clock icon; n/a = `rgba(204,204,204,0.8)` bg + dash icon
  - Category name as bold label on left (Rubik SemiBold 18px, #06004f)
  - Column headers: "Human readability" / "Machine readability" / "Trust anchors" — dark navy header row
  - Divider lines between categories
- Next steps panel: Static — 4 fixed steps always shown (not dynamic)
  1. Review your results
  2. Discuss with an expert
  3. Define improvement priorities
  4. Create improvement plan
  - Panel background: `#cfe7d6` (light green card), 16px radius
  - "Schedule an appointment" button → `mailto:info@coe-dsc.nl?subject=MAMI%20Assessment%20Consultation`
- Page structure: Move from standalone HTML (opened in new tab) to a React route `/report` inside the `_app` layout
  - Backend still generates the report data (JSON or HTML template can be adapted)
  - Frontend renders the report as a React page at `/_app/report`
  - "Generate Compliance Report" on dashboard navigates to `/report` (not opens new tab)
- Styling: White nav header with CoE DSC logo + hamburger/Menu; light green page background (`rgba(57,158,90,0.1)` over white); Rubik font throughout; #06004f dark blue text
- Footer: Dark navy footer with "Follow us" socials + Contact / Privacy & cookies / Newsletter links

**Homepage (items 7+8):**
- Figma URL: https://www.figma.com/design/V3v7Oq6DfXMpQ86llyVCQ0/MAMI-tool?node-id=154-3458
- Logo: Replace "CoE DSC" text with `<img src={logo}>` using `frontend/src/assets/logo-coe-dsc.svg`
- Hero headline: "MAMI - Minimal Agreements for Maximum Interoperability"
- Hero subtitle: "A practical self-assessment tool that helps you understand and improve the interoperability of your initiative"
- Nav buttons: "Log In" (link to /login) + "Register" (green button, link to /register)
- Hero CTA buttons: "Start the check" (green, /login) + "Create an account" (outline white, /register)
- "How it works" section heading: "How does it work?"
- Step cards content as specified in CONTEXT.md decisions
- MAMI section heading and body as specified in CONTEXT.md decisions
- MAMI section CTA button: "Get started"

**Progress tracker — sub-categories (item 2):**
- Topics expand ONLY under the active/current category (accordion style)
- Topics are informational only — NOT clickable for navigation
- Active topic indicator: bold Rubik font + small navy accent dot or left-border accent
- Completed/pending categories show only the category name label (no topics expanded)
- Component to update: `frontend/src/components/questionnaire/StepPills.tsx`

**Questionnaire navigation labels (item 3):**
- "← Vorige" → "← Previous"
- "Volgende →" → "Next →"
- "Voltooien →" → "Finish →"
- File: `frontend/src/components/questionnaire/WizardPage.tsx` lines ~534, ~553

**Question X of X pill position (item 1):**
- Currently: inline next to topic label (flex row with topic h4)
- Target: top-right corner of the question card header
- Move pill to top-right, next to or replacing autosave badge position — autosave badge can go below or swap position
- File: `frontend/src/components/questionnaire/WizardPage.tsx` lines ~401-463

**Logo on auth screens (items 4–6):**
- SVG file: `frontend/src/assets/logo-coe-dsc.svg` (already on disk)
- Add logo image above the "CoE-DSC / TNO" text label on all 4 auth screens
- Files: login.tsx, register.tsx, forgot-password.tsx, reset-password.tsx
- Size: ~76×32px (matching Figma header logo size)

### Claude's Discretion
- Exact pixel layout for the /report React page (infer from Figma screenshot captured above)
- Whether to keep the Jinja2 template or replace entirely with React rendering
- Report data fetching pattern (reuse existing `/initiatives/{id}/report` API or adapt)
- Logo sizing on auth screens
- Homepage layout details not covered by the Figma URL (executor should pull from Figma node 154-3458)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

## Summary

Phase 8 is a purely visual alignment phase — no new backend features, no schema migrations. The work splits into three tiers: (1) quick string/position fixes in existing components (items 1–3), (2) logo insertion into existing auth + homepage screens (items 4–8), and (3) a full compliance report restyle that requires a new React route and a backend data shape change (item 9).

The compliance report redesign is the most substantial work. The current system uses a Jinja2 HTML template returned by `POST /initiatives/{id}/report` and opened as a Blob URL in a new tab. The new design moves report rendering into React at `/_app/report`, which means the backend must return structured JSON (not raw HTML) and the frontend must construct the two-column heatmap layout and static Next Steps panel from that data. Alternatively, the backend could return a simplified JSON payload, and the React page renders the Figma-spec UI using inline styles (matching the existing project pattern — no CSS-in-JS library).

The project uses TanStack Router file-based routing with `routeTree.gen.ts` committed and manually maintained. Adding a new `/_app/report` route requires creating `frontend/src/routes/_app/report.tsx` and updating `routeTree.gen.ts` per the established project convention (the Vite dev server regenerates it, but the generated file is committed). The `implement-design` skill is available and the Figma MCP server should be used to fetch pixel-accurate specs for the homepage (node 154-3458) and report (node 154-4667) before implementing.

**Primary recommendation:** Plan as three logical work streams — (A) quick wins: labels + pill position + sub-category expand [WizardPage.tsx, StepPills.tsx], (B) logo insertion on 4 auth screens + homepage [5 files], (C) report restyle: new `/report` route + backend JSON adapter + React heatmap + Next Steps panel.

---

## Standard Stack

### Core (already in project — no new installs needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | ^19.2.0 | UI rendering | Project foundation |
| TanStack Router | ^1.160.0 | File-based routing | Established project pattern |
| antd | ^6.3.0 | Component library | All auth/app screens use antd Card, Button, Alert, Input |
| TanStack React Query | ^5.90.21 | Server state / data fetching | Used in questionnaire page |
| Vite | ^7.3.1 | Build tool + router plugin | Generates routeTree.gen.ts on dev server start |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Figma MCP (get_design_context, get_screenshot) | — | Pull pixel specs from Figma nodes | Before implementing homepage and report; use `implement-design` skill |
| FastAPI JSONResponse | (fastapi built-in) | Return JSON instead of HTML from report endpoint | If report data adapter approach chosen |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| React inline styles (current pattern) | CSS modules or Tailwind | Project uses inline styles throughout — stay consistent |
| FastAPI JSONResponse for report | Keep HTMLResponse | JSONResponse enables clean React rendering; HTMLResponse requires dangerouslySetInnerHTML |

**Installation:** No new packages needed. All required libraries are already installed.

---

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── routes/_app/
│   └── report.tsx           # NEW: React report page at /report
├── routes/_auth/
│   ├── login.tsx            # ADD logo import
│   ├── register.tsx         # ADD logo import
│   ├── forgot-password.tsx  # ADD logo import
│   └── reset-password.tsx   # ADD logo import
├── routes/
│   └── index.tsx            # RESTYLE homepage, ADD logo, English content
├── components/questionnaire/
│   ├── WizardPage.tsx       # MOVE pill position, RENAME nav labels
│   └── StepPills.tsx        # ADD topic expansion for active category
├── assets/
│   └── logo-coe-dsc.svg     # EXISTS — import as needed
└── routeTree.gen.ts         # UPDATE: add AppReportRoute import + registration
```

### Pattern 1: Adding a New /_app Route (TanStack Router file-based)
**What:** Create a new `.tsx` file under `routes/_app/`, then manually update `routeTree.gen.ts` to import and register the route. Vite regenerates `routeTree.gen.ts` on `npm run dev` but the committed version must be manually updated per project convention.
**When to use:** Any new authenticated page.

```typescript
// frontend/src/routes/_app/report.tsx
import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/_app/report')({
  component: ReportPage,
});

function ReportPage() {
  // fetch report data, render two-column layout
}
```

Then in routeTree.gen.ts — add:
```typescript
import { Route as AppReportRouteImport } from './routes/_app/report'

const AppReportRoute = AppReportRouteImport.update({
  id: '/report',
  path: '/report',
  fullPath: '/report',
  getParentRoute: () => AppRoute,
} as any)

// Add AppReportRoute to AppRouteChildren and AppRouteChildren const
```

### Pattern 2: Report Data Fetching Strategy
**What:** The `POST /initiatives/{id}/report` endpoint currently returns `HTMLResponse`. For the React page, change the endpoint to return `JSONResponse` with structured data the frontend renders. The React `/report` page calls this endpoint on mount and renders the Figma-spec layout.
**When to use:** When converting from Blob-URL-in-new-tab to React route rendering.

```typescript
// In dashboard.tsx — change handleGenerateReport
import { useNavigate } from '@tanstack/react-router';

async function handleGenerateReport() {
  if (!initiative) return;
  setReportLoading(true);
  try {
    // POST to trigger scoring + store results, then navigate
    await api.post(`/initiatives/${initiative.id}/report`, {});
    navigate({ to: '/report' });
  } catch {
    setReportError('...');
  } finally {
    setReportLoading(false);
  }
}
```

The `/report` page fetches via `GET /initiatives/{id}/report` (already exists) — but that returns HTML. The backend adapter must be updated to return JSON (see Architecture section below).

### Pattern 3: Backend Report JSON Adapter
**What:** Add a new endpoint `GET /initiatives/{id}/report/data` returning JSON, OR change the existing POST to return JSON and add a `GET /report/data` variant. The React page calls `GET /initiatives/me/report` or passes initiative ID via route search params.
**When to use:** When migrating from HTML-blob report to React-rendered report.

The simplest approach: change `POST /initiatives/{id}/report` to accept `Accept: application/json` and return a JSON payload when the frontend requests JSON. Or add a dedicated `GET /initiatives/{id}/report/json` endpoint.

**Recommended JSON shape:**
```json
{
  "initiative": { "name": "...", "organization": "...", "generated_at": "..." },
  "categories": [
    {
      "id": "scheme",
      "label": "Scheme",
      "dimensions": {
        "human_readable": { "status": "yes" },
        "machine_readable": { "status": "not_yet" },
        "trust_anchors": { "status": "n/a" }
      }
    }
  ],
  "total_yes": 12,
  "total_not_yet": 5,
  "total_na": 3
}
```

### Pattern 4: StepPills Topic Expansion (Accordion)
**What:** Add `currentTopicIndex` prop to `StepPills`. Under the active category row, render the list of topics. Only active category shows topics. Active topic gets bold + navy accent indicator.
**When to use:** Implementing item 2 (progress tracker sub-categories).

```typescript
// Updated Props
interface Props {
  categories: Category[];
  currentCategoryIndex: number;
  completedCategoryIds: Set<string>;
  currentTopicIndex: number;  // NEW prop
}
```

The `Category` type already has a `topics` array (from `questionnaire.ts` lib). Under the active category row, map over `cat.topics` to render topic name labels with active/inactive styling.

### Pattern 5: WizardPage Pill Repositioning (Item 1)
**What:** The "Question X of Y" chip (lines 447–463) currently lives in a flex row with the topic h4. Move it to the top-right card header row (lines 401–425) alongside or replacing the autosave badge position. Autosave badge drops below or swaps.
**Target layout:**

```
[ Category label (left) ]    [ Question X of Y chip (right) ]
[ Topic h4 (full width) ]
[ Autosave badge (right-aligned below) ]
```

### Pattern 6: Compliance Report Heatmap React Component
**What:** Build a `ReportHeatmap` component that receives the JSON data and renders:
- Left card: white bg, 16px radius, navy header row with 3 column labels, then one row per category (label + 3 chips)
- Right card: `#cfe7d6` bg, 16px radius, 4 numbered Next Steps + appointment button

Chip rendering:
```typescript
const CHIP_STYLES = {
  yes:      { bg: 'rgba(57,158,90,0.2)',   color: '#399e5a', icon: '✓' },
  not_yet:  { bg: 'rgba(61,82,213,0.2)',   color: '#3d52d5', icon: '⏱' },
  na:       { bg: 'rgba(204,204,204,0.8)', color: '#666',    icon: '–' },
  unanswered: { bg: 'rgba(204,204,204,0.4)', color: '#999', icon: '?' },
};
```

### Anti-Patterns to Avoid
- **Editing `routeTree.gen.ts` then running `npm run dev` without manual merge:** Vite regenerates the file on dev server start, overwriting manual additions. Add route to the file AND let Vite regenerate naturally during dev — they should match. Per project convention: manually update the committed version before running dev.
- **Using `window.open` + Blob URL for the new report:** The decision is to navigate to `/report` route — do not keep the Blob URL approach.
- **Keeping `response_class=HTMLResponse` on the report endpoint if React rendering is chosen:** Return `JSONResponse` for the new data endpoint; the old HTML endpoint can remain for backward compatibility but the new React page must fetch JSON.
- **Making topics clickable in StepPills:** CONTEXT.md explicitly states topics are informational only — NOT clickable.
- **Adding new npm packages:** All visual styling uses inline styles matching existing project pattern. No new CSS libraries.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chip/pill status indicators | Custom CSS component library | Inline styles with hardcoded colors from CONTEXT.md | Project already uses inline styles consistently; colors are Figma-spec |
| Report data store (pass data between pages) | Redux / Zustand | TanStack Router search params OR re-fetch on mount in /report page | Simpler, matches existing patterns |
| SVG icon rendering for chip icons | react-icons or icon library | Unicode characters or inline SVG strings | CONTEXT.md specifies unicode/CSS equivalents acceptable |
| Routing guards for /report | Custom auth middleware | The `/_app` layout already handles auth via `beforeLoad` + redirect | /report inherits auth protection automatically as `/_app/report` |

**Key insight:** This phase is pure UI work on an existing codebase. The "don't hand-roll" principle mainly means: reuse the existing auth guard, existing API client, and existing design tokens. Don't reinvent what's already there.

---

## Common Pitfalls

### Pitfall 1: routeTree.gen.ts Out of Sync
**What goes wrong:** After creating `routes/_app/report.tsx`, the `routeTree.gen.ts` file is not updated. TypeScript compilation (`tsc`) fails, and the route is not navigable.
**Why it happens:** The file is auto-generated by Vite plugin but also committed manually. If you create the file but don't update routeTree.gen.ts before the tsc check, the build fails.
**How to avoid:** Immediately after creating `report.tsx`, add the import and route registration to `routeTree.gen.ts` following the exact pattern used for `_app/about`, `_app/dashboard`, etc.
**Warning signs:** TypeScript errors like "Route not found" or missing type declarations for `/_app/report`.

### Pitfall 2: Report Page Navigation — Initiative ID Not Available
**What goes wrong:** The `/report` page needs to call `GET /initiatives/{id}/report/data` but doesn't know the initiative ID without an extra API call.
**Why it happens:** The route `/report` has no URL parameters. The page must either (A) store the initiative ID in router search params during navigation, or (B) call `GET /initiatives/me` first to get the ID, then fetch report data.
**How to avoid:** On mount in `ReportPage`, call `GET /initiatives/me` first (same pattern as `QuestionnairePage`), then use that initiative ID to fetch the report JSON. This is the cleanest approach matching existing code patterns.
**Warning signs:** 404 errors on the report endpoint because initiative_id is 0 or undefined.

### Pitfall 3: Backend Returns HTML, Frontend Expects JSON
**What goes wrong:** The existing `POST /initiatives/{id}/report` returns `HTMLResponse`. If the React `/report` page calls this without backend changes, it receives an HTML string, not structured JSON.
**Why it happens:** The backend was designed for Blob URL rendering, not React component rendering.
**How to avoid:** Add a new JSON endpoint (`GET /initiatives/{id}/report/json` or change POST to return JSON) before implementing the React page. The existing HTML endpoint can remain for backward compatibility.
**Warning signs:** `JSON.parse` errors or the page renders raw HTML text instead of styled components.

### Pitfall 4: StepPills Missing `topics` Property on Category Type
**What goes wrong:** When implementing topic expansion in `StepPills`, TypeScript may report that `Category` doesn't have a `topics` field, even though the questionnaire config does have topics.
**Why it happens:** The `Category` TypeScript interface in `lib/questionnaire.ts` may not expose the full nested structure.
**How to avoid:** Check `frontend/src/lib/questionnaire.ts` to confirm the `Category` interface includes `topics: Topic[]`. If it doesn't, add it. This is a type-only change, not a runtime change.
**Warning signs:** TypeScript compile errors accessing `cat.topics` in StepPills.

### Pitfall 5: Homepage Logo Import Path
**What goes wrong:** Importing the SVG logo with `import logo from '../assets/logo-coe-dsc.svg'` fails because the relative path depth differs between `routes/index.tsx` and `routes/_auth/login.tsx`.
**Why it happens:** Routes are at different depths. `routes/index.tsx` is one level deep, `routes/_auth/login.tsx` is two levels deep.
**How to avoid:** Use `../../assets/logo-coe-dsc.svg` from `_auth/*.tsx` files and `../assets/logo-coe-dsc.svg` from `routes/index.tsx`. Verify by checking existing import paths in those files.
**Warning signs:** Vite build error "Cannot find module '...logo-coe-dsc.svg'".

### Pitfall 6: Report Heatmap Data Shape — Category/Dimension Naming
**What goes wrong:** The backend matrix uses `snake_case` dimension names (`human_readable`, `machine_readable`, `trust_anchors`) but the Figma column headers use title case. Mismatch causes chips to appear under wrong columns.
**Why it happens:** The `_build_matrix` function in `report_generator.py` uses hardcoded `snake_case` keys. The frontend must map these to display labels.
**How to avoid:** In the React heatmap component, define an explicit mapping: `{ human_readable: 'Human readability', machine_readable: 'Machine readability', trust_anchors: 'Trust anchors' }`.

---

## Code Examples

### Logo Import and Render (auth screens + homepage)
```typescript
// In routes/_auth/login.tsx (and register.tsx, forgot-password.tsx, reset-password.tsx)
import logo from '../../assets/logo-coe-dsc.svg';

// In the white card header section (replaces or supplements "CoE-DSC / TNO" text):
<div style={{ marginBottom: '2rem', textAlign: 'center' }}>
  <img src={logo} alt="CoE DSC" style={{ height: '32px', marginBottom: '0.75rem' }} />
  <div style={{ fontSize: '0.75rem', color: '#399e5a', fontWeight: 600, ... }}>CoE-DSC / TNO</div>
  <h1 ...>Sign In</h1>
</div>
```

### Question Pill Repositioned (WizardPage.tsx, lines ~401–463)
```typescript
// BEFORE: pill inline with topic h4 (remove from here)
// AFTER: pill in the top-right header row

{/* Card top row: category title + pill (top-right) */}
<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
  <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#06004f', margin: 0 }}>
    {currentCategory.label}
  </h3>
  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
    <span style={{ background: 'rgba(61,82,213,0.16)', color: '#3d52d5', padding: '0.25rem 0.75rem', borderRadius: '100px', fontSize: '0.8125rem', fontWeight: 500, whiteSpace: 'nowrap' }}>
      {currentTopicQuestionCount === 1
        ? `Question ${questionFrom} of ${totalQuestions}`
        : `Questions ${questionFrom}–${questionTo} of ${totalQuestions}`}
    </span>
    <AutosaveBadge state={badgeState} />
  </div>
</div>

{/* Topic label — now full width, no pill */}
<h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#06004f', margin: 0, marginBottom: '1.5rem' }}>
  {currentTopic.label}
</h4>
```

### Navigation Button Labels (WizardPage.tsx, lines ~534, ~553)
```typescript
// BEFORE:
// "← Vorige"
// "Volgende →" / "Voltooien →"

// AFTER:
<button ...>← Previous</button>
<button ...>{isSaving ? 'Saving...' : isFinish ? 'Finish →' : 'Next →'}</button>
```

### StepPills Topic Expansion (StepPills.tsx)
```typescript
interface Props {
  categories: Category[];
  currentCategoryIndex: number;
  completedCategoryIds: Set<string>;
  currentTopicIndex: number;  // NEW
}

// Inside the map, after the category label row:
{isActive && cat.topics && (
  <div style={{ marginLeft: '36px', marginTop: '4px', marginBottom: '4px' }}>
    {cat.topics.map((topic, ti) => {
      const isActiveTopic = ti === currentTopicIndex;
      return (
        <div key={topic.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '3px 0' }}>
          {isActiveTopic && (
            <div style={{ width: 4, height: 4, borderRadius: '50%', background: '#06004f', flexShrink: 0 }} />
          )}
          <span style={{
            fontSize: '0.8125rem',
            fontWeight: isActiveTopic ? 600 : 400,
            color: isActiveTopic ? '#06004f' : 'rgba(6,0,79,0.5)',
            fontFamily: "'Rubik', sans-serif",
            paddingLeft: isActiveTopic ? 0 : '10px',
          }}>
            {topic.label}
          </span>
        </div>
      );
    })}
  </div>
)}
```

### Report React Page Data Fetching Pattern
```typescript
// frontend/src/routes/_app/report.tsx
import { createFileRoute } from '@tanstack/react-router';
import { useEffect, useState } from 'react';
import { api } from '../../lib/api';

export const Route = createFileRoute('/_app/report')({
  component: ReportPage,
});

function ReportPage() {
  const [reportData, setReportData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const initiativeRes = await api.get<{ id: number }>('/initiatives/me');
        const reportRes = await api.get<ReportData>(`/initiatives/${initiativeRes.data.id}/report/json`);
        setReportData(reportRes.data);
      } catch {
        setError('Could not load report. Generate one from the dashboard first.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Render two-column layout...
}
```

### Dashboard Navigation Change
```typescript
// frontend/src/routes/_app/dashboard.tsx
import { useNavigate } from '@tanstack/react-router';

// Inside DashboardPage component:
const navigate = useNavigate();

async function handleGenerateReport() {
  if (!initiative) return;
  setReportLoading(true);
  setReportError(null);
  try {
    await api.post(`/initiatives/${initiative.id}/report`, {});
    navigate({ to: '/report' });
  } catch {
    setReportError('Failed to generate report...');
  } finally {
    setReportLoading(false);
  }
}
```

### Backend JSON Report Endpoint (new)
```python
# backend/app/api/v1/reports.py — add after existing endpoints

@router.get("/initiatives/{initiative_id}/report/json")
async def get_report_json(
    initiative_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    mami_config: dict = Depends(get_mami_config),
):
    """Return report data as structured JSON for the React /report page."""
    initiative = session.get(Initiative, initiative_id)
    if not initiative or initiative.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Initiative not found")

    answers = session.exec(
        select(QuestionnaireAnswer).where(
            QuestionnaireAnswer.initiative_id == initiative_id
        )
    ).all()

    # Build answer lookup
    answer_lookup = {a.mami_code: a.answer_value for a in answers}

    # Status mapping: YES→yes, NOT_THERE_YET→not_yet, NOT_APPLICABLE→na
    STATUS_MAP = {
        "YES": "yes",
        "NOT_THERE_YET": "not_yet",
        "NOT_APPLICABLE": "na",
    }

    categories_out = []
    for cat_conf in mami_config.get("categories", []):
        dims = {}
        for dim_key in ["human_readable", "machine_readable", "trust_anchors"]:
            # Find codes for this category+dimension
            code = next((c for c in mami_config.get("codes", [])
                         if c["category"] == cat_conf["id"] and c["dimension"] == dim_key), None)
            if code:
                raw = answer_lookup.get(code["id"])
                dims[dim_key] = STATUS_MAP.get(raw, "unanswered") if raw else "unanswered"
            else:
                dims[dim_key] = "na"
        categories_out.append({
            "id": cat_conf["id"],
            "label": cat_conf.get("label", cat_conf["id"].title()),
            "dimensions": dims,
        })

    return {
        "initiative": {
            "name": initiative.name,
            "organization": initiative.organization,
            "generated_at": datetime.utcnow().isoformat(),
        },
        "categories": categories_out,
        "summary": {
            "yes": sum(1 for a in answers if a.answer_value == "YES"),
            "not_yet": sum(1 for a in answers if a.answer_value == "NOT_THERE_YET"),
            "na": sum(1 for a in answers if a.answer_value == "NOT_APPLICABLE"),
        }
    }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Blob URL + window.open for report | React route `/report` in `_app` layout | Phase 8 | Auth headers work naturally, TopNav included for free, no popup blockers |
| CRITICAL/NON_CRITICAL chip colors | yes/not yet/n/a chips (green/blue/grey) | Phase 8 | Matches Figma spec and user-facing language from questionnaire |
| Dutch nav labels (Vorige/Volgende/Voltooien) | English (Previous/Next/Finish) | Phase 8 | Consistency with English-language UI from Phase 7 |
| Dutch homepage content | English content matching Figma node 154-3458 | Phase 8 | Matches brand spec |
| Text "CoE DSC" in nav/auth | SVG logo `logo-coe-dsc.svg` | Phase 8 | Visual brand alignment |

**Deprecated/outdated after Phase 8:**
- `backend/app/templates/report.html`: Jinja2 template still exists but the React `/report` page is the new user-facing report. The Jinja2 template + HTML endpoint can remain as-is (for potential PDF export in Phase 5) but the dashboard no longer links to it directly.

---

## Open Questions

1. **Does `mami_config` have a `categories` top-level array, or only `codes`?**
   - What we know: `report_generator.py` uses `mami_config.get("codes", [])` and iterates `categories = ["scheme", "participants", "data", "services"]` as hardcoded strings.
   - What's unclear: Whether the JSON config has a `categories` key with labels, or just `codes` with embedded category references.
   - Recommendation: The executor must read the actual config files (`dsi-questionnaire-v2.json` or the mami scoring config) before writing the JSON endpoint. If no `categories` key exists, derive categories from unique `code["category"]` values with labels hardcoded or mapped.

2. **WizardPage — how is `currentTopicIndex` passed to StepPills?**
   - What we know: `WizardPage.tsx` has `categoryIndex` and `topicIndex` as state. `StepPills` is rendered inside `WizardPage`.
   - What's unclear: Whether `StepPills` is rendered with direct props or via a separate component tree path.
   - Recommendation: Read lines 300–400 of `WizardPage.tsx` to confirm the StepPills render call, then pass `currentTopicIndex={topicIndex}` directly.

3. **Does `Category` interface in `lib/questionnaire.ts` include `topics`?**
   - What we know: The questionnaire config has a topics nested structure (from Phase 3.1).
   - What's unclear: Whether the frontend `Category` TypeScript type already exposes `topics: Topic[]`.
   - Recommendation: Executor reads `frontend/src/lib/questionnaire.ts` as first step. If `topics` is missing from the type, add it before modifying StepPills.

---

## Sources

### Primary (HIGH confidence)
- Direct source code inspection: `WizardPage.tsx`, `StepPills.tsx`, `reports.py`, `report_generator.py`, `dashboard.tsx`, `_app.tsx`, `routeTree.gen.ts` — all read directly
- CONTEXT.md — all Figma URLs, color values, and implementation decisions verified from user-provided context

### Secondary (MEDIUM confidence)
- TanStack Router file-based routing pattern — inferred from existing `routeTree.gen.ts` + established project convention in STATE.md
- `implement-design` skill (`.agents/skills/implement-design/SKILL.md`) — confirms Figma MCP workflow for homepage and report nodes

### Tertiary (LOW confidence)
- Backend JSON endpoint shape — proposed based on reading `report_generator.py`; actual mami_config structure not verified (see Open Questions)

---

## Metadata

**Confidence breakdown:**
- Quick fixes (items 1–3): HIGH — exact file locations and line numbers confirmed by reading source
- Logo insertion (items 4–7): HIGH — SVG confirmed on disk, auth screen pattern confirmed
- Homepage restyle (item 8): HIGH — current Dutch content confirmed, English spec from CONTEXT.md, Figma node available
- Report restyle (item 9): MEDIUM — React route pattern HIGH, JSON endpoint shape MEDIUM (depends on mami_config structure not fully read)

**Research date:** 2026-03-07
**Valid until:** 2026-04-06 (stable dependencies, no fast-moving ecosystem concerns)
