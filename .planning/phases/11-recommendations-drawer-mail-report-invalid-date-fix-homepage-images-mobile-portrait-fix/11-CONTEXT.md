# Phase 11: Recommendations drawer + mail report + invalid date fix + homepage images + mobile portrait fix — Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Five distinct deliverables on the report page and homepage:

1. **Recommendations drawer** — collapsible section below the heatmap showing personalised improvement recommendations for questions answered NOT_THERE_YET or left unanswered.
2. **Mail me the results** — button in a new "Next steps" right-side panel; emails the report as a PDF attachment via Resend, with a CoE follow-up invite.
3. **Invalid Date fix** — `generated_at` formatted as a plain string in Python is passed to `new Date()` in React and fails on Railway (Linux). Fix the serialisation so it parses reliably cross-environment.
4. **Homepage images** — Add OBJECTS.svg (hero right), lines-top.svg (left-side decoration, upper page), lines-bottom.svg (left-side decoration, lower page) to the existing homepage (`index.tsx`).
5. **Mobile portrait fix** — Heatmap/report content is cut off on the right on narrow screens. Fix via `overflow-x: auto` and responsive handling.

</domain>

<decisions>
## Implementation Decisions

### Recommendations drawer

- **Trigger:** Show recommendations for questions where `answer_value === "NOT_THERE_YET"` OR the question has no answer at all (unanswered).
- **Placement:** Below the heatmap on the report page, as a single antd `Collapse` panel (already available — just not imported on report page yet).
- **Default state:** Collapsed. User expands to see recommendations.
- **Header:** "Recommendations for improving your interoperability"
- **Explanatory text (normal weight, below header inside panel):** "Below are suggested steps you could take in the areas that you have indicated as 'Not yet, but planning to do'. The MAMI document, available on the CoE-DSC website, contains elaborate recommendations for all of the areas."
- **Item format (flat list):** `<dimension_label> — <topic_label> - <recommendation_text>` e.g. "Human Readable/Actionable — Scheme publication & updates - Unless highly sensitive, please consider making your scheme agreements publicly available."
- **Sub-theme derivation:** Pull `dimension_label` and `topic_label` from `mami-framework.json` by matching the question's `mami_code`. Do NOT hardcode labels.
- **Recommendation texts:** 27 hardcoded strings, keyed by the user's ID format (HRA-1.1 … TA-4.2). Researcher must verify the mapping between DB `mami_code` values (e.g. `S-HRA-1.1`) and user IDs (e.g. `HRA-1.1`) in `mami-framework.json`.
- **Data source:** Recommendations are derived client-side from the report data JSON already returned by `GET /initiatives/{id}/report/data`. No new API endpoint needed.

Full recommendation ID → text mapping (27 items):

| ID | Text |
|----|------|
| HRA-1.1 | Unless highly sensitive, please consider making your scheme agreements publicly available. |
| MRA-1.1 | Please consider publishing your scheme in a machine-readable format by having an actionable sandbox/demo for end-users to interact with. |
| TA-1.1 | Please consider specifying the actor responsible for publishing and updating the scheme, and also specify allowed procedures/actions that the scheme authority can conduct for updating and publishing the scheme. |
| HRA-1.2 | Please consider including conditions in the scheme agreement via various clauses, like settlement clauses, liability clauses or any force majeure clauses. |
| MRA-1.2 | Please consider supporting an automatic way for flagging incidents and an automatic way to track progress of the started disputes. |
| TA-1.2 | Please consider indicating what are the trust anchor(s) that parties can go to for dispute management. |
| HRA-1.3 | Please consider providing traceability tools generating a human readable/actionable record that can be used to achieve legal clarity for any subsequent dispute handling. |
| MRA-1.3 | Please consider providing traceability tools generating a machine readable/actionable record that can be used to achieve automatic flagging of incidents and aid in subsequent dispute handling. |
| TA-1.3 | Please consider specifying a Trust Anchor responsible for the operation/provision of the traceability tools. Also, please consider specifying what is being traced in accordance with the scope of your scheme, to ensure clarity and transparency for the interacting participants and/or 3rd parties joining the scheme. |
| HRA-2.1 | Please consider providing human readable/actionable information regarding your scheme participation, including onboarding and offboarding procedures (to the extent allowed by privacy & sensitivity conditions). |
| MRA-2.1 | Please consider providing code/APIs and/or adjacent testbeds to technically support onboarding and offboarding procedures. Also, please consider to what extent you may publicly disclose the scheme participation, onboarding procedures and access to testbeds. Also, please consider having access management controls in place for any sensitive content, including clear access conditions. |
| TA-2.1 | Please consider specifying trust anchors for onboarding and offboarding procedures. |
| HRA-2.2 | Please consider providing information about existing participants of the scheme via a registry, with access rights limited by sensitivity conditions of the scheme. |
| MRA-2.2 | Please consider providing a machine readable/actionable registry of participant endpoints. |
| TA-2.2 | Please consider specifying Trust Anchors for registry services provision. |
| HRA-3.1 | Please consider providing at least general information regarding data sets available to scheme participants to discover, understand, access and/or visit said data to the extent permitted by sensitivity & privacy conditions, and consider providing explicit descriptions about the access conditions. Also, please consider adhering to the FAIR principles. |
| MRA-3.1 | Please consider ensuring that your member provide information about data/data sets in a machine readable/actionable way, enabling other participants to discover, understand, access and/or visit said data, under specific sensitivity & privacy conditions. |
| TA-3.1 | Please consider specifying trust anchors used for metadata standards, and specifying trust anchors/credibility means for assurance in data characteristics relevant in the context. |
| HRA-3.2 | Please consider NOT providing actual data UNLESS the specified access & usage conditions are met; these conditions should then be documented in a human readable/actionable form. |
| MRA-3.2 | Please consider NOT providing actual data UNLESS the specified access & usage conditions are met AND during a request for data access/visiting an automatic (machine readable/actionable) procedure of authentication & authorization has been properly completed. |
| TA-3.2 | Please consider specifying the Scheme Authority and/or governance mechanisms/procedures as a trust anchor to ensure participants have obtained trusted digital identity means for relying parties to use for authenticating & authorizing to provide data access. |
| HRA-4.1 | Please consider providing (at least general) information regarding services available to the scheme participants and/or 3rd parties (to the extent permitted by sensitivity & privacy conditions). |
| MRA-4.1 | Please consider ensuring you and/or your participants provide (at least general) information regarding services available to other participants and/or 3rd parties in a machine readable/actionable way (to the extent permitted by sensitivity & privacy conditions). |
| TA-4.1 | Please consider specifying Trust Anchors for each service provided under the scheme. |
| HRA-4.2 | Please consider NOT providing actual services UNLESS the specified provision conditions are met; such conditions should then be made human readable/actionable. |
| MRA-4.2 | Please consider NOT providing actual services UNLESS the specified provision conditions are met and any automatic checks to authorize the provision of service are completed. |
| TA-4.2 | Please consider establishing Scheme Authority and/or governance mechanisms & procedures to ensure that trusted service providers adhere to the scheme conditions. |

### Next steps panel (report page — new UI)

- **Layout:** Right-side panel next to the heatmap. Two-column layout: heatmap left, next steps right. On mobile, stacks vertically.
- **Content (from design):**
  - Heading: "Next steps"
  - Four steps listed (with icons/checkmarks): "Review your results", "Discuss with an expert", "Define improvement priorities", "Create improvement plan"
  - **No** "Schedule an appointment" button (explicitly excluded)
  - "Mail me the results" button (primary CTA)
  - Supporting text below button: "Our experts will help you translate your results into concrete actions"
- **Design reference:** Design 1.PNG — right panel.

### Mail me the results

- **Email format:** PDF attachment (not inline HTML).
- **PDF generation:** WeasyPrint is in the stack but NOT YET implemented (deferred from Phase 5, still "NOT STARTED"). This phase must implement basic WeasyPrint PDF generation from the stored `html_content`. Researcher must investigate WeasyPrint setup, dependencies, and Railway deployment compatibility.
- **Sender:** `noreply@coe-dsc.nl` — requires Resend domain verification for `coe-dsc.nl`. Researcher must check if this domain is or can be verified in Resend. Fallback to `onboarding@resend.dev` if domain not verified.
- **Subject:** "Your MAMI Interoperability Heatmap"
- **Email body (Claude drafts — to be reviewed):** The email will include a short intro paragraph, the PDF report attached, and a follow-up invite paragraph such as: "Would you like expert guidance on your results? The Centre of Excellence for Data Sharing and Cloud (CoE-DSC) is available to help you translate your assessment into a concrete improvement plan. Contact us at [CoE-DSC website/email] to schedule a follow-up conversation."
- **Trigger:** Button in the new Next steps panel on the report page. Calls a new backend endpoint (e.g. `POST /initiatives/{id}/report/mail`). Uses the authenticated user's email from JWT — no email input form needed.
- **Pattern to follow:** `_send_reset_email` in `auth.py` using `resend` SDK.

### Invalid Date fix

- **Root cause:** `generated_at` is returned as a plain string `"2026-03-13 14:30 UTC"` from `report_generator.py`. `new Date("2026-03-13 14:30 UTC")` fails on Railway (Linux V8 engine).
- **Fix:** Change the backend to return `generated_at` as a proper ISO 8601 string (e.g. `datetime.utcnow().isoformat() + "Z"`) instead of the formatted string. Update the frontend to display it with `toLocaleString()` as currently written. Alternatively, if the formatted string is needed in HTML reports, keep two separate fields or format client-side.
- **Scope:** Fix in `report_generator.py` (lines ~49 and ~204) and ensure `ReportRead.generated_at` is typed as `datetime` (already is per `schemas/report.py`) so FastAPI serialises it as ISO 8601 automatically.

### Homepage images

- **Files:** All three already exist in `frontend/src/assets/`: `OBJECTS.svg`, `lines-top.svg`, `lines-bottom.svg`.
- **OBJECTS.svg:** Hero section, right side — large decorative geometric triangular mesh illustration. Positioned to the right of the headline text, occupying roughly the right half of the hero area.
- **lines-top.svg:** Left-side decorative bracket/line element for the upper half of the page (hero + feature sections). Absolutely positioned on the left edge, non-interactive.
- **lines-bottom.svg:** Left-side decorative bracket/line element for the lower half of the page (questionnaire overview + "Ready to explore" sections). Absolutely positioned on the left edge, non-interactive.
- **Design reference:** Homepage Design.png — follow placement exactly.
- **File:** `frontend/src/routes/index.tsx` (homepage/landing page).

### Mobile portrait fix

- **Problem:** Heatmap table and report content are cut off on the right in phone portrait mode.
- **Root cause likely:** `overflow: "hidden"` on outer container in `report.tsx` (line ~419), combined with fixed-width table columns.
- **Fix scope:** Heatmap table container gets `overflowX: "auto"` so it scrolls horizontally on narrow screens. The rest of the report header/pill row should also be checked for similar clipping.
- **Claude's Discretion:** Exact breakpoint(s) and whether to reflow any elements vs scroll-only.

### Claude's Discretion

- Loading/sending state on the "Mail me the results" button (spinner, disabled state while sending).
- Exact styling of the recommendations flat list (bullet points, dividers, typography).
- Exact email body copy (beyond the CoE invite paragraph pattern above).
- Error state if email send fails.

</decisions>

<specifics>
## Specific Ideas

- Design 1.PNG: Shows the report layout with right-side "Next steps" panel and bottom collapsible drawer ("Hier komt een kop" placeholder = recommendations header in final design).
- Homepage Design.png: Shows the full homepage layout with all three SVGs in context.
- The 27 recommendations are hardcoded content provided by the user — they do not come from any backend API. Store them as a static map in the frontend.
- The "Mail me the results" flow: user clicks button → POST to backend → backend generates PDF → sends via Resend → returns 202. No polling needed for MVP.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `antd Collapse`: Not yet used on report page, but antd is fully set up. Import and use for the recommendations drawer.
- `resend` SDK: Already integrated in `backend/app/api/v1/auth.py` — `_send_reset_email` is the pattern to follow for `_send_report_email`.
- `RESEND_API_KEY`: Already an env var in the project.
- `ComplianceReport.html_content`: Stored HTML in DB, available for PDF generation.
- `frontend/src/assets/OBJECTS.svg`, `lines-top.svg`, `lines-bottom.svg`: All present, just need referencing.

### Established Patterns
- Email: `resend.Emails.send(params)` with `"from"`, `"to"`, `"subject"`, `"text"` keys. Attachments use `"attachments": [{"filename": "...", "content": base64_bytes}]`.
- Report data API: `GET /initiatives/{id}/report/data` returns answers with `mami_code` and `answer_value`. Recommendations drawer reads this client-side — no new endpoint needed for the drawer itself.
- `mami-framework.json` at `config/mami-framework.json`: Contains all 27+ codes with `id`, `dimension_label`, `topic_label`. Loaded via FastAPI `app.state` (lifespan). The researcher must confirm the mami_code → recommendation ID mapping (codes use `S-HRA-1.1` format; user IDs use `HRA-1.1` format — likely strip the `S-` prefix).
- antd design tokens: `colorPrimary #06004f` (navy), `colorSuccess #399e5a` (green), `borderRadius 8px`.

### Integration Points
- `report.tsx`: Add two-column layout (heatmap + Next steps panel), recommendations drawer below both.
- `reports.py` or new endpoint: `POST /initiatives/{id}/report/mail` — generate PDF, send email, return 202.
- `report_generator.py` lines ~49 and ~204: Change `generated_at` to ISO 8601 format.
- `index.tsx` (homepage): Import and place the three SVGs per design.

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-recommendations-drawer-mail-report-invalid-date-fix-homepage-images-mobile-portrait-fix*
*Context gathered: 2026-03-13*
