# Phase 11: Recommendations drawer + mail report + invalid date fix + homepage images + mobile portrait fix — Research

**Researched:** 2026-03-13
**Domain:** React/antd frontend UI, FastAPI email/PDF backend, date serialisation
**Confidence:** HIGH (codebase read directly; external library APIs verified)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Recommendations drawer:**
- Trigger: `answer_value === "NOT_THERE_YET"` OR no answer (unanswered)
- Placement: Below heatmap on report page, antd `Collapse` (single panel)
- Default state: Collapsed
- Header: "Recommendations for improving your interoperability"
- Explanatory text (inside panel): "Below are suggested steps you could take in the areas that you have indicated as 'Not yet, but planning to do'. The MAMI document, available on the CoE-DSC website, contains elaborate recommendations for all of the areas."
- Item format: `<dimension_label> — <topic_label> - <recommendation_text>`
- Sub-theme from `mami-framework.json` via `mami_code` lookup (no hardcoded labels)
- 27 hardcoded recommendation texts stored as static map in frontend
- Data source: client-side from existing `ReportData.answers` — no new API endpoint

**Next steps panel:**
- Two-column layout: heatmap left, next steps right (existing `NextStepsPanel` already exists and renders)
- Steps: "Review your results", "Discuss with an expert", "Define improvement priorities", "Create improvement plan"
- No "Schedule an appointment" button
- "Mail me the results" button (primary CTA)
- Supporting text: "Our experts will help you translate your results into concrete actions"

**Mail me the results:**
- PDF attachment (not inline HTML)
- WeasyPrint PDF generation from stored `html_content` in `ComplianceReport`
- Sender: `noreply@coe-dsc.nl` if domain verified; else `onboarding@resend.dev`
- Subject: "Your MAMI Interoperability Heatmap"
- Trigger: POST `/initiatives/{id}/report/mail`; uses JWT user email
- Pattern: follow `_send_reset_email` in `auth.py`

**Invalid Date fix:**
- Backend: change `datetime.utcnow().strftime(...)` in `report_generator.py` to `datetime.utcnow().isoformat() + "Z"`
- Frontend: keep `new Date(...).toLocaleString()` — ISO 8601 string is safe cross-platform
- Both `generate_html_report` (line ~49) and `generate_report_data` (line ~204) need changing

**Homepage images:**
- `OBJECTS.svg` → hero right side
- `lines-top.svg` → left-side decoration, upper page
- `lines-bottom.svg` → left-side decoration, lower page
- All files exist: `frontend/src/assets/`
- File: `frontend/src/routes/index.tsx`

**Mobile portrait fix:**
- `overflowX: "auto"` on heatmap container in `report.tsx`
- Check header/pill row for similar clipping

### Claude's Discretion

- Loading/sending state on "Mail me the results" button (spinner, disabled while sending)
- Exact styling of recommendations flat list (bullet points, dividers, typography)
- Exact email body copy (beyond CoE invite paragraph)
- Error state if email send fails
- Exact breakpoint(s) for mobile fix; whether to reflow elements vs scroll-only

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 11 spans five independent deliverables across frontend and backend. The frontend work (recommendations drawer, next steps panel updates, homepage images, mobile fix) is straightforward React/antd work with no new dependencies. The backend work (WeasyPrint PDF, Resend email, date fix) requires adding WeasyPrint as a dependency and updating the Dockerfile with system packages — this is the highest-risk item.

The most critical discovery is the **mami_code → recommendation ID mapping**: `mami_code` values in the DB (`S-HRA-1.1`, `PM-HRA-1.1`, `D-HRA-1.1`, `SER-HRA-1.1`) do NOT map to recommendation IDs (`HRA-1.1`, `HRA-2.1`, `HRA-3.1`, `HRA-4.1`) via simple prefix stripping. The category prefix varies (`S-`, `PM-`, `D-`, `SER-`) and the numeric suffix resets per category. A complete hardcoded `MAMI_CODE_TO_REC_ID` map must be implemented in the frontend. Also: the **report page already has a `NextStepsPanel` component and two-column layout** — the current "Schedule an appointment" button just needs replacing with "Mail me the results".

WeasyPrint requires system libraries (pango, cairo, gdk-pixbuf, libffi) that must be added to the Dockerfile. The `python:3.13-slim` base image does not include these. Resend attachment format uses `list(pdf_bytes)` (array of integers), not base64 string.

**Primary recommendation:** Implement deliverables in order of risk — Invalid Date fix first (trivial, unblocks the date display), then homepage images and mobile fix (pure frontend, no new deps), then recommendations drawer (frontend-only, new antd Collapse), then mail+PDF (requires Dockerfile change and backend work).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| antd | ^6.3.0 (project installed) | Collapse UI component | Already in project |
| resend | >=2.23.0 (project installed) | Email with PDF attachment | Already integrated |
| weasyprint | latest stable (~68.x) | HTML→PDF bytes | Only pure-Python HTML-to-PDF that doesn't need headless Chrome |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python:3.13-slim + apt packages | system | pango/cairo/libffi for WeasyPrint | Required in Dockerfile only |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WeasyPrint | reportlab / fpdf2 | reportlab/fpdf2 can't render HTML — would need to rewrite report template entirely |
| WeasyPrint | Playwright headless Chrome | Playwright is 200MB+; complex on Railway; not appropriate for this lightweight use |
| WeasyPrint | xhtml2pdf | Older, less maintained, CSS support weaker |

**Backend installation:**
```bash
# In pyproject.toml dependencies:
uv add weasyprint
# In Dockerfile (before uv sync):
apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

---

## Architecture Patterns

### Recommended Change Locations

```
backend/
├── app/
│   ├── services/report_generator.py   # Fix generated_at format (2 locations)
│   ├── api/v1/reports.py              # Add POST /initiatives/{id}/report/mail endpoint
│   └── core/config.py                 # (no change needed — RESEND_API_KEY already present)
├── pyproject.toml                     # Add weasyprint dependency
└── Dockerfile                         # Add apt system packages

frontend/src/routes/
├── _app/report.tsx                    # Add recommendations drawer + update NextStepsPanel
└── index.tsx                          # Add 3 SVG images

frontend/src/assets/
├── OBJECTS.svg                        # Already exists
├── lines-top.svg                      # Already exists
└── lines-bottom.svg                   # Already exists
```

### Pattern 1: antd v6 Collapse with items prop (NOT deprecated Panel subcomponent)

**What:** antd v6 removed deprecated v4 APIs. Use `items` prop, not `<Collapse.Panel>` or `<Panel>`.
**When to use:** Any new Collapse in the project.

```typescript
// Source: Ant Design v6 official API (items-based, verified current)
import { Collapse } from 'antd';

const items = [
  {
    key: 'recommendations',
    label: 'Recommendations for improving your interoperability',
    children: <RecommendationsList data={recommendations} />,
  },
];

<Collapse items={items} defaultActiveKey={[]} />
// defaultActiveKey={[]} means collapsed by default
// No accordion needed — single panel only
```

### Pattern 2: Resend email with PDF attachment

**What:** Resend attachment format uses `list(bytes)` (array of integers), not base64 string.
**Source:** Official Resend Python docs — https://resend.com/docs/dashboard/emails/attachments

```python
# Source: Resend official Python docs (verified 2026-03-13)
import resend
from weasyprint import HTML

def _send_report_email(email: str, html_content: str, api_key: str) -> None:
    if not api_key:
        print(f"[DEV] Would send report to {email}", flush=True)
        return
    pdf_bytes: bytes = HTML(string=html_content).write_pdf()
    attachment: resend.Attachment = {
        "content": list(pdf_bytes),
        "filename": "MAMI-Interoperability-Report.pdf",
    }
    resend.api_key = api_key
    params: resend.Emails.SendParams = {
        "from": "MaMi Checker <onboarding@resend.dev>",  # fallback until domain verified
        "to": [email],
        "subject": "Your MAMI Interoperability Heatmap",
        "text": (
            "Dear participant,\n\n"
            "Please find attached your MAMI Interoperability Heatmap report.\n\n"
            "Would you like expert guidance on your results? The Centre of Excellence "
            "for Data Sharing and Cloud (CoE-DSC) is available to help you translate "
            "your assessment into a concrete improvement plan. Contact us via the "
            "CoE-DSC website to schedule a follow-up conversation.\n\n"
            "The MAMI Checker team"
        ),
        "attachments": [attachment],
    }
    resend.Emails.send(params)
```

### Pattern 3: Invalid Date fix — ISO 8601 serialisation

**What:** Replace `strftime("%Y-%m-%d %H:%M UTC")` with `isoformat() + "Z"`.
**Root cause:** V8 on Linux rejects space-separated date strings; ISO 8601 is cross-browser/cross-platform.

```python
# In report_generator.py — TWO locations to update:

# generate_html_report() context dict (line ~49):
"generated_at": datetime.utcnow().isoformat() + "Z",

# generate_report_data() initiative dict (line ~204):
"generated_at": datetime.utcnow().isoformat() + "Z",
```

Frontend stays unchanged — `new Date("2026-03-13T14:30:00Z").toLocaleString()` works correctly everywhere.

### Pattern 4: mami_code → Recommendation ID mapping (CRITICAL FINDING)

**What:** The DB stores codes like `S-HRA-1.1`, `PM-HRA-1.1`, `D-HRA-1.1`, `SER-HRA-1.1`. The user's recommendation keys are `HRA-1.1`, `HRA-2.1`, `HRA-3.1`, `HRA-4.1`. These are NOT related by simple prefix stripping.

**Correct mapping (verified from mami-framework.json):**

| DB mami_code | Rec ID | DB mami_code | Rec ID | DB mami_code | Rec ID |
|---|---|---|---|---|---|
| S-HRA-1.1 | HRA-1.1 | S-MRA-1.1 | MRA-1.1 | S-TA-1.1 | TA-1.1 |
| S-HRA-2.1 | HRA-1.2 | S-MRA-2.1 | MRA-1.2 | S-TA-2.1 | TA-1.2 |
| S-HRA-3.1 | HRA-1.3 | S-MRA-3.1 | MRA-1.3 | S-TA-3.1 | TA-1.3 |
| PM-HRA-1.1 | HRA-2.1 | PM-MRA-1.1 | MRA-2.1 | PM-TA-1.1 | TA-2.1 |
| PM-HRA-2.1 | HRA-2.2 | PM-MRA-2.1 | MRA-2.2 | PM-TA-2.1 | TA-2.2 |
| D-HRA-1.1 | HRA-3.1 | D-MRA-1.1 | MRA-3.1 | D-TA-1.1 | TA-3.1 |
| D-HRA-2.1 | HRA-3.2 | D-MRA-2.1 | MRA-3.2 | D-TA-2.1 | TA-3.2 |
| SER-HRA-1.1 | HRA-4.1 | SER-MRA-1.1 | MRA-4.1 | SER-TA-1.1 | TA-4.1 |
| SER-HRA-2.1 | HRA-4.2 | SER-MRA-2.1 | MRA-4.2 | SER-TA-2.1 | TA-4.2 |

Implement as a `const MAMI_CODE_TO_REC_ID: Record<string, string>` in report.tsx.

### Pattern 5: ReportData answers — filtering for recommendations

**What:** `data.answers` from `POST /initiatives/{id}/report/data` is an array with `mami_code` and `answer_value`. Also need to detect unanswered (codes in `mami_config` but absent from answers).

```typescript
// answer_value values: "NOT_THERE_YET", "YES", "NOT_APPLICABLE", or absent (unanswered)
// Filter logic for recommendations:
const answeredCodes = new Set(data.answers.map(a => a.mami_code));
const allCodes = Object.keys(MAMI_CODE_TO_REC_ID); // 27 codes

const recommendedCodes = allCodes.filter(code => {
  const answer = data.answers.find(a => a.mami_code === code);
  return !answer || answer.answer_value === "NOT_THERE_YET";
});
```

But NOTE: `data.answers` only includes codes that have been answered (saved to DB). Unanswered codes are absent from the array. The frontend must detect unanswered codes by comparing against the known set of 27 codes.

However: `data.topic_structure` and `mami_framework.json` are NOT returned by the report data API — they're backend-only. The frontend must use the hardcoded `MAMI_CODE_TO_REC_ID` map to derive dimension and topic labels. But `dimension_label` and `topic_label` are needed for display.

**Solution:** Include a second static map `MAMI_CODE_TO_LABELS: Record<string, { dimension_label: string; topic_label: string }>` in report.tsx. Values come directly from mami-framework.json (already read by researcher).

```typescript
// Complete labels map (derived from mami-framework.json):
const MAMI_CODE_TO_LABELS: Record<string, { dimension_label: string; topic_label: string }> = {
  "S-HRA-1.1": { dimension_label: "Human Readable/Actionable", topic_label: "Scheme publication & updates" },
  "S-MRA-1.1": { dimension_label: "Machine Readable", topic_label: "Scheme publication & updates" },
  "S-TA-1.1":  { dimension_label: "Trust Anchors", topic_label: "Scheme publication & updates" },
  "S-HRA-2.1": { dimension_label: "Human Readable/Actionable", topic_label: "Incidents & dispute management" },
  "S-MRA-2.1": { dimension_label: "Machine Readable", topic_label: "Incidents & dispute management" },
  "S-TA-2.1":  { dimension_label: "Trust Anchors", topic_label: "Incidents & dispute management" },
  "S-HRA-3.1": { dimension_label: "Human Readable/Actionable", topic_label: "Traceability" },
  "S-MRA-3.1": { dimension_label: "Machine Readable", topic_label: "Traceability" },
  "S-TA-3.1":  { dimension_label: "Trust Anchors", topic_label: "Traceability" },
  "PM-HRA-1.1":{ dimension_label: "Human Readable/Actionable", topic_label: "On(off)-boarding" },
  "PM-MRA-1.1":{ dimension_label: "Machine Readable", topic_label: "On(off)-boarding" },
  "PM-TA-1.1": { dimension_label: "Trust Anchors", topic_label: "On(off)-boarding" },
  "PM-HRA-2.1":{ dimension_label: "Human Readable/Actionable", topic_label: "Participants discovery" },
  "PM-MRA-2.1":{ dimension_label: "Machine Readable", topic_label: "Participants discovery" },
  "PM-TA-2.1": { dimension_label: "Trust Anchors", topic_label: "Participants discovery" },
  "D-HRA-1.1": { dimension_label: "Human Readable/Actionable", topic_label: "Data(sets) Publication & discovery" },
  "D-MRA-1.1": { dimension_label: "Machine Readable", topic_label: "Data(sets) Publication & discovery" },
  "D-TA-1.1":  { dimension_label: "Trust Anchors", topic_label: "Data(sets) Publication & discovery" },
  "D-HRA-2.1": { dimension_label: "Human Readable/Actionable", topic_label: "Data(sets) Provisions" },
  "D-MRA-2.1": { dimension_label: "Machine Readable", topic_label: "Data(sets) Provisions" },
  "D-TA-2.1":  { dimension_label: "Trust Anchors", topic_label: "Data(sets) Provisions" },
  "SER-HRA-1.1":{ dimension_label: "Human Readable/Actionable", topic_label: "Services Publications and discovery" },
  "SER-MRA-1.1":{ dimension_label: "Machine Readable", topic_label: "Services Publications and discovery" },
  "SER-TA-1.1": { dimension_label: "Trust Anchors", topic_label: "Services Publications and discovery" },
  "SER-HRA-2.1":{ dimension_label: "Human Readable/Actionable", topic_label: "Services Provisions" },
  "SER-MRA-2.1":{ dimension_label: "Machine Readable", topic_label: "Services Provisions" },
  "SER-TA-2.1": { dimension_label: "Trust Anchors", topic_label: "Services Provisions" },
};
```

### Pattern 6: report.tsx current state — what's already there vs what needs changing

**Already exists (confirmed by code read):**
- `NextStepsPanel` component renders 4 steps + "Schedule an appointment" button
- Two-column layout: heatmap left (flex 2) + next steps right (flex 1, green bg)
- `ReportData` type with `answers` array having `mami_code` and `answer_value`
- `overflow: "hidden"` on heatmap card div (line ~419) — this is the mobile bug

**Needs changing:**
- `NextStepsPanel`: replace "Schedule an appointment" href button with "Mail me the results" onClick button
- Add `isSending` state and API call for mail endpoint
- Add recommendations `Collapse` below the two-column flex div
- Change heatmap card `overflow: "hidden"` to `overflow: "visible"` + add `overflowX: "auto"` wrapper on `HeatmapMatrix`

### Pattern 7: Backend mail endpoint

**Pattern to follow:** `_send_reset_email` / `forgot_password` in `auth.py`

```python
# New endpoint in reports.py
@router.post("/initiatives/{initiative_id}/report/mail", status_code=202)
async def mail_report(
    initiative_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Email the stored HTML report as PDF to the authenticated user."""
    initiative = session.get(Initiative, initiative_id)
    if not initiative or initiative.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Initiative not found")

    report = session.exec(
        select(ComplianceReport).where(ComplianceReport.initiative_id == initiative_id)
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="No report generated yet. Generate a report first.")

    background_tasks.add_task(
        _send_report_email,
        current_user.email,
        report.html_content,
        settings.RESEND_API_KEY,
    )
    return {"message": "Report is being emailed to your address."}
```

### Anti-Patterns to Avoid

- **Using `Collapse.Panel` or `<Panel>` subcomponent:** Removed in antd v6. Use `items` prop only.
- **Using `datetime.strftime("%Y-%m-%d %H:%M UTC")` format:** Breaks `new Date()` on Linux V8. Always use ISO 8601.
- **Passing base64 string to Resend attachment `content`:** Wrong format. Use `list(bytes)` (array of ints).
- **Importing SVGs as URL strings with `?url` suffix:** Not needed — Vite handles `.svg` imports as component URLs by default in this project (see `logoSrc` import pattern in `index.tsx`).
- **Generating PDF synchronously in the request handler:** Use `BackgroundTasks` to avoid blocking the 202 response.
- **Adding WeasyPrint to pyproject.toml without updating Dockerfile:** Will fail on Railway with `OSError: cannot load library 'libgobject-2.0-0'`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML-to-PDF | Custom PDF builder | WeasyPrint `HTML(string=...).write_pdf()` | CSS rendering, pagination, fonts — massive scope |
| Email with attachment | Custom SMTP | resend SDK (already integrated) | Auth, deliverability, API already set up |
| Collapsible UI | Custom accordion | antd `Collapse` with `items` prop | Already a project dependency; accessibility built in |

**Key insight:** All external dependencies for this phase are already in the project (antd, resend). Only WeasyPrint is new, and its API is a single function call.

---

## Common Pitfalls

### Pitfall 1: WeasyPrint system library missing on Railway
**What goes wrong:** `OSError: cannot load library 'libgobject-2.0-0'` at runtime — WeasyPrint import fails.
**Why it happens:** `python:3.13-slim` base image has no GTK/Pango/Cairo libraries.
**How to avoid:** Add to Dockerfile (before `uv sync`):
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
  && rm -rf /var/lib/apt/lists/*
```
**Warning signs:** Works locally on Windows/Mac (WeasyPrint may find system libs) but fails on Railway.

### Pitfall 2: Resend sender domain not verified
**What goes wrong:** 403 error from Resend — `noreply@coe-dsc.nl` rejected as unverified sender.
**Why it happens:** Resend requires DNS verification for custom domains. `coe-dsc.nl` may not be configured in the Resend dashboard.
**How to avoid:** Use `onboarding@resend.dev` as fallback sender (already used for password reset). Add a `RESEND_SENDER` env var or simply hardcode `onboarding@resend.dev` until domain is verified. The CONTEXT.md explicitly allows this fallback.
**Warning signs:** Email send returns 403 with "domain not verified" in response body.

### Pitfall 3: Invalid mami_code → rec_id mapping (wrong prefix strip)
**What goes wrong:** Recommendations don't display for participants/data/services codes.
**Why it happens:** CONTEXT.md says "strip S- prefix" but only Scheme codes start with `S-`. Participants = `PM-`, Data = `D-`, Services = `SER-`.
**How to avoid:** Use the complete hardcoded `MAMI_CODE_TO_REC_ID` map from Pattern 4 above — 27 entries, verified from mami-framework.json.
**Warning signs:** Recommendations only show for Scheme category codes; others silently produce no rec text.

### Pitfall 4: antd v6 `Collapse.Panel` removed
**What goes wrong:** TypeScript compilation error or runtime error using `<Panel>` or `Collapse.Panel`.
**Why it happens:** antd v6 removed all APIs deprecated in v4/v5. `Panel` subcomponent was deprecated in v5.
**How to avoid:** Use `<Collapse items={[{ key, label, children }]} />` — no subcomponent import needed.
**Warning signs:** TypeScript error `Property 'Panel' does not exist on type 'typeof Collapse'`.

### Pitfall 5: overflow:hidden on heatmap card clips horizontal scroll
**What goes wrong:** `overflowX: "auto"` on the HeatmapMatrix wrapper does nothing; table still clips.
**Why it happens:** Parent div has `overflow: "hidden"` (report.tsx line ~419), which prevents child scroll from working.
**How to avoid:** Change the heatmap card outer div from `overflow: "hidden"` to `overflow: "visible"` (or remove it) and add `overflowX: "auto"` on the `HeatmapMatrix` wrapper div inside the card. The `borderRadius` on the card still works with `overflow: "visible"`.

### Pitfall 6: SVG import in Vite — wrong import style
**What goes wrong:** SVG renders as a broken image or doesn't display.
**Why it happens:** Different import patterns produce different things (React component vs URL string).
**How to avoid:** Follow the existing pattern in `index.tsx`: `import objectsSrc from '../assets/OBJECTS.svg'` then `<img src={objectsSrc} />`. This is consistent with the existing `logoSrc` import pattern. Do NOT use `?url` suffix or `?react` suffix — the project doesn't use them.

### Pitfall 7: WeasyPrint blocking the request thread
**What goes wrong:** Email endpoint takes 2-5 seconds to return while PDF generates.
**Why it happens:** `HTML(string=...).write_pdf()` is CPU-bound synchronous.
**How to avoid:** Always use `background_tasks.add_task(...)` — already the pattern for `_send_reset_email`. Return 202 immediately.

---

## Code Examples

### antd v6 Collapse — minimal single-panel collapsed by default
```typescript
// Source: Ant Design v6 items API (verified current docs pattern)
import { Collapse } from 'antd';

const collapseItems = [
  {
    key: '1',
    label: 'Recommendations for improving your interoperability',
    children: (
      <div>
        <p style={{ fontFamily: "'Rubik', sans-serif", fontSize: "0.875rem", color: "#333" }}>
          Below are suggested steps you could take...
        </p>
        {/* flat list of items */}
      </div>
    ),
  },
];

// defaultActiveKey={[]} = collapsed by default
<Collapse items={collapseItems} defaultActiveKey={[]} />
```

### WeasyPrint PDF from HTML string
```python
# Source: WeasyPrint official docs / verified Python SDK pattern
from weasyprint import HTML

pdf_bytes: bytes = HTML(string=html_content).write_pdf()
# pdf_bytes is bytes — pass as list(pdf_bytes) to Resend attachment
```

### ISO 8601 date in report_generator.py
```python
# Replace in BOTH generate_html_report() and generate_report_data():
"generated_at": datetime.utcnow().isoformat() + "Z",
# Produces: "2026-03-13T14:30:00.123456Z" — safe for new Date() everywhere
```

### SVG import in index.tsx (follow existing pattern)
```typescript
// Consistent with existing logoSrc import pattern in the file:
import objectsSrc from '../assets/OBJECTS.svg';
import linesTopSrc from '../assets/lines-top.svg';
import linesBottomSrc from '../assets/lines-bottom.svg';

// Usage:
<img src={objectsSrc} alt="" aria-hidden="true" style={{ ... }} />
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Collapse.Panel` subcomponent | `Collapse items={[...]}` prop | antd v5 (deprecated) → v6 (removed) | Must use items API — no subcomponent |
| `strftime("%Y-%m-%d %H:%M UTC")` | `isoformat() + "Z"` | This phase | Fixes Railway Invalid Date bug |
| "Schedule an appointment" button | "Mail me the results" button | This phase | Replaces static mailto with API call |

**Deprecated/outdated in this project:**
- `datetime.utcnow().strftime(...)` for `generated_at`: produces non-ISO strings that fail on Linux V8
- `Collapse.Panel` / `<Panel>` import: removed in antd v6 (project uses 6.3.0)

---

## Open Questions

1. **Resend domain verification for `coe-dsc.nl`**
   - What we know: `noreply@coe-dsc.nl` is the desired sender. Resend requires DNS records for custom domains.
   - What's unclear: Whether the domain is already verified in the Resend dashboard.
   - Recommendation: Use `onboarding@resend.dev` as the sender (same as password reset) until domain verification is confirmed. Add `RESEND_SENDER` env var or accept hardcoded fallback for now. CONTEXT.md explicitly permits this.

2. **WeasyPrint font rendering on Railway**
   - What we know: WeasyPrint uses system fonts. `python:3.13-slim` has minimal fonts.
   - What's unclear: Whether the existing HTML report template uses web fonts (Google Fonts) that WeasyPrint can't fetch.
   - Recommendation: The existing `report.html` Jinja2 template may include `<link>` to Google Fonts which WeasyPrint will attempt to fetch. If Railway has no internet access from Docker or if font loading is slow, add `fonts-liberation` to apt packages and test. If PDF font looks wrong, add a `base_url` to WeasyPrint: `HTML(string=html_content, base_url="https://app-url.railway.app").write_pdf()`.

3. **Homepage design reference (Design 1.PNG, Homepage Design.png)**
   - What we know: SVG files exist in assets. Design references mentioned in CONTEXT.md but not accessible to researcher.
   - What's unclear: Exact pixel positioning of the SVGs.
   - Recommendation: The planner should instruct implementer to follow the design reference images. The positioning is "right side of hero" for OBJECTS.svg and "left edge, absolutely positioned" for the line decorations. Absolute positioning on the homepage `<main>` container with `position: "relative"` is the correct approach.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase reads: `report.tsx`, `index.tsx`, `reports.py`, `report_generator.py`, `auth.py`, `mami-framework.json`, `dsi-questionnaire-v2.json`, `pyproject.toml`, `Dockerfile`, `package.json` — verified all current code structure
- Resend official docs (https://resend.com/docs/dashboard/emails/attachments) — attachment format `list(bytes)` verified

### Secondary (MEDIUM confidence)
- WeasyPrint system dependencies: multiple Railway Help Station issues + official WeasyPrint docs confirm `libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev` required on Debian/Ubuntu/slim
- WeasyPrint `HTML(string=...).write_pdf()` returns bytes: multiple verified tutorials confirm this API
- antd v6 Collapse uses `items` prop (not `Panel` subcomponent): confirmed from v5→v6 migration context; Collapse.Panel deprecated in v5, removed in v6

### Tertiary (LOW confidence)
- Exact antd v6 Collapse TypeScript interface: couldn't load source directly; based on confirmed pattern from multiple community sources that items API is current standard

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project; only WeasyPrint is new (documented, stable)
- Architecture: HIGH — codebase read directly; all integration points confirmed
- Pitfalls: HIGH — WeasyPrint Railway issues confirmed from multiple Railway Help Station posts; antd v6 breaking changes confirmed from official migration notes; mami_code mapping verified from actual JSON files

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (30 days — stable stack)
