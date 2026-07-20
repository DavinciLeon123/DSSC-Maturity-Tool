# Phase 8: Figma design cleanup and Compliance Report styling - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 9 Figma alignment gaps across the frontend and replace the backend compliance report with a Figma-spec design. No new features — only visual alignment and content corrections.

The 9 items in scope:
1. "Question X of X" pill → move to top-right corner of the question card (currently inline next to topic label)
2. Progress tracker left sidebar → show topic (sub-category) names under the active category
3. Questionnaire navigation → "Vorige" / "Volgende" → "Previous" / "Next" (+ "Voltooien" → "Finish")
4. Login page → add CoE DSC logo
5. Register page → add CoE DSC logo
6. Forgot-password page → add CoE DSC logo
7. Homepage → add CoE DSC logo
8. Homepage → replace Dutch text with English, restyle to match Figma (see Figma URL below)
9. Compliance Report → full restyle to match Figma design (see Figma URL below)

</domain>

<decisions>
## Implementation Decisions

### Compliance Report (item 9) — Full redesign
- **Figma URL:** https://www.figma.com/design/V3v7Oq6DfXMpQ86llyVCQ0/MAMI-tool?node-id=154-4667
- **Scoring model:** Switch from CRITICAL/NON_CRITICAL to yes / not yet / n/a
  - Backend maps: YES → "yes" (green chip), NOT_THERE_YET → "not yet" (blue chip), NOT_APPLICABLE → "n/a" (grey chip)
  - Remove severity/MoSCoW language from report output
- **Layout:** Two-column — heatmap matrix left + "Next steps" card right
- **Heatmap:** Replace old `<table>` with chip/pill rows per category × 3 dimensions
  - Chip colors: yes = `rgba(57,158,90,0.2)` bg + checkmark icon; not yet = `rgba(61,82,213,0.2)` bg + clock icon; n/a = `rgba(204,204,204,0.8)` bg + dash icon
  - Category name as bold label on left (Rubik SemiBold 18px, #06004f)
  - Column headers: "Human readability" / "Machine readability" / "Trust anchors" — dark navy header row
  - Divider lines between categories
- **Next steps panel:** Static — 4 fixed steps always shown (not dynamic):
  1. Review your results
  2. Discuss with an expert
  3. Define improvement priorities
  4. Create improvement plan
  - Panel background: `#cfe7d6` (light green card), 16px radius
  - "Schedule an appointment" button → `mailto:info@coe-dsc.nl`
- **Page structure:** Move from standalone HTML (opened in new tab) to a React route `/report` inside the `_app` layout
  - Backend still generates the report data (JSON or HTML template can be adapted)
  - Frontend renders the report as a React page at `/_app/report`
  - "Generate Compliance Report" on dashboard navigates to `/report` (not opens new tab)
- **Styling:** White nav header with CoE DSC logo + hamburger/Menu; light green page background (`rgba(57,158,90,0.1)` over white); Rubik font throughout; #06004f dark blue text
- **Footer:** Dark navy footer with "Follow us" socials + Contact / Privacy & cookies / Newsletter links

### Homepage (item 7+8)
- **Figma URL:** https://www.figma.com/design/V3v7Oq6DfXMpQ86llyVCQ0/MAMI-tool?node-id=154-3458
- **Logo:** Replace "CoE DSC" text with `<img src={logo}>` using `frontend/src/assets/logo-coe-dsc.svg`
- **Hero headline:** "MAMI - Minimal Agreements for Maximum Interoperability"
- **Hero subtitle:** "A practical self-assessment tool that helps you understand and improve the interoperability of your initiative"
- **Nav buttons:** "Log In" (link to /login) + "Register" (green button, link to /register)
- **Hero CTA buttons:** "Start the check" (green, /login) + "Create an account" (outline white, /register)
- **"How it works" section heading:** "How does it work?"
- **Step cards (3 steps):**
  - Step 01: "Register your initiative" — "Create an account and register your Data Sharing Initiative (DSI) or Service Provider (SP) initiative."
  - Step 02: "Complete the questionnaire" — "Work through the structured MAMI questionnaire with Yes / Not yet / Not applicable answers per topic."
  - Step 03: "Receive your report" — "Generate an instant interoperability heatmap with your current compliance level."
- **MAMI section heading:** "The MAMI questionnaire gives you an immediate overview of your current level of interoperability."
- **MAMI section body:** "Across four key domains (Scheme, Participants, Data and Services), you will assess whether you already comply, plan to comply or it's not applicable. Your answers are visualised in a clear interoperability heatmap."
- **MAMI section CTA button:** "Get started" (or "Begin now" → use "Get started")
- **Overall colours and layout:** Mirror the Figma (node 154-3458) as closely as possible — executor should use the Figma URL directly if the MCP tool is available

### Progress tracker — sub-categories (item 2)
- Topics expand ONLY under the active/current category (accordion style)
- Topics are informational only — NOT clickable for navigation
- Active topic indicator: bold Rubik font + small navy accent dot or left-border accent
- Completed/pending categories show only the category name label (no topics expanded)
- Component to update: `frontend/src/components/questionnaire/StepPills.tsx`

### Questionnaire navigation labels (item 3)
- "← Vorige" → "← Previous"
- "Volgende →" → "Next →"
- "Voltooien →" → "Finish →"
- File: `frontend/src/components/questionnaire/WizardPage.tsx` lines ~534, ~553

### Question X of X pill position (item 1)
- Currently: inline next to topic label (flex row with topic h4)
- Target: top-right corner of the question card header
- The card header row currently has: category title (left) + autosave badge (right)
- Move pill to top-right, next to or replacing autosave badge position — autosave badge can go below or swap position
- File: `frontend/src/components/questionnaire/WizardPage.tsx` lines ~401-463

### Logo on auth screens (items 4–6)
- SVG file: `frontend/src/assets/logo-coe-dsc.svg` (already on disk)
- Add logo image above the "CoE-DSC / TNO" text label on all 4 auth screens
- Files: login.tsx, register.tsx, forgot-password.tsx, reset-password.tsx
- Size: ~76×32px (matching Figma header logo size) — Claude's discretion on exact sizing

### Claude's Discretion
- Exact pixel layout for the /report React page (infer from Figma screenshot captured above)
- Whether to keep the Jinja2 template or replace entirely with React rendering
- Report data fetching pattern (reuse existing `/initiatives/{id}/report` API or adapt)
- Logo sizing on auth screens
- Homepage layout details not covered by the Figma URL (executor should pull from Figma node 154-3458)

</decisions>

<specifics>
## Specific Ideas

- Figma report screenshot shows: left card = white bg, 16px radius, heatmap with navy header bar spanning columns; right card = `#cfe7d6` light green, timeline-style Next Steps with numbered circles
- The "not yet" chip uses a clock icon (icon-park-outline:time); "yes" uses material-symbols:check-rounded; "n/a" uses octicon:dash-16 — use Unicode/CSS equivalents or inline SVGs in the HTML report
- Report page title: "Your assessment results" (Rubik Medium 35px)
- The `/report` route should live inside `_app` so it gets the TopNav — no need for a separate header
- "Schedule an appointment" mailto should open email client with subject pre-filled: `mailto:info@coe-dsc.nl?subject=MAMI%20Assessment%20Consultation`

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/assets/logo-coe-dsc.svg`: SVG logo — import and render as `<img>` in auth screens and homepage nav
- `frontend/src/components/questionnaire/WizardPage.tsx`: Contains Question X of Y chip (lines 447-463), nav buttons (lines 518-555), all Dutch strings
- `frontend/src/components/questionnaire/StepPills.tsx`: Category-only progress sidebar — needs topic expansion logic added
- `frontend/src/routes/index.tsx`: Full Dutch homepage — needs content replacement + Figma layout alignment
- `backend/app/templates/report.html`: Current Jinja2 report template — replace or restyle
- `backend/app/services/report_generator.py`: Generates report context — may need scoring model update (YES/NOT_THERE_YET/NOT_APPLICABLE mapping)

### Established Patterns
- Auth screens all use: dark navy bg `#06004f`, white card `borderRadius: 16px`, Rubik font, antd Input/Button/Alert components
- `_app.tsx` layout wraps all authenticated routes with TopNav — adding `/report` route here gets nav for free
- TanStack Router file-based routing: create `frontend/src/routes/_app/report.tsx` to add `/report` route
- `routeTree.gen.ts` is auto-generated by Vite dev server on file change — do NOT manually edit after adding new route file

### Integration Points
- Dashboard `handleGenerateReport()` currently does `api.post(...report)` → opens Blob URL in new tab
  - Change to: `navigate({ to: '/report' })` after storing report data (or fetch on mount in /report page)
- Report API: `POST /initiatives/{id}/report` returns HTML string or JSON — executor should decide whether to adapt to JSON or keep HTML
- StepPills receives `categories`, `currentCategoryIndex`, `completedCategoryIds` — needs `currentTopicIndex` prop added to highlight active topic

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-figma-design-cleanup-and-compliance-report-styling*
*Context gathered: 2026-03-07*
