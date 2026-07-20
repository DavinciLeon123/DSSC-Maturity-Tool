# Phase 9: UX Improvements — Context

**Gathered:** 2026-03-09
**Status:** Ready for planning
**Source:** User specification (chat message)

<domain>
## Phase Boundary

Six UX improvements to streamline the user journey, clean up the dashboard, and improve the report and questionnaire for mobile. No new backend features — changes are primarily frontend with minor backend adjustments if needed.

</domain>

<decisions>
## Implementation Decisions

### 1. Initiative Registration on Dashboard
- **Requirement:** The two-step process (account creation → separate initiative registration) should collapse into one. Register the initiative directly on the Dashboard page.
- **Required fields:** Initiative Name + Sector (dropdown) — these two are REQUIRED.
- **Optional fields:** All other initiative fields (organization, contact name, participant type, etc.) become optional.
- **UX:** Show a registration form inline on the Dashboard when the user has no initiative yet. Once submitted, the Dashboard shows initiative details.

### 2. Remove Role Label
- **Requirement:** Remove the "Role: USER / ADMIN" text from the Dashboard page.

### 3. Initiative Details + Questionnaire CTA on Dashboard
- **Requirement:** After initiative registration, the Dashboard shows initiative details (name, sector, etc.).
- **CTA — no questionnaire taken:** "Start Questionnaire" button.
- **CTA — questionnaire already completed:** "Retake Questionnaire" button (same action, different label).

### 4. Post-Questionnaire Flow
- **Requirement:** After pressing "Generate Report" on the "Your submission is complete" page, the user should be taken directly to the `/report` page — NOT to the Dashboard.
- **Completion page text change:** "Thank you for completing the MAMI Questionnaire. You can now view your MAMI Interoperability heatmap."
- **Button label change:** "Generate heatmap" (was "Generate Report").

### 5. Expanded Report Heatmap
- **Requirement:** The report heatmap currently shows only top-level categories (Scheme, Participants, Data, Services). It should be expanded to show BOTH top-level AND second-level categories (topics).
- **Scoring:** Chips (yes/not_yet/n_a) appear at the second-level (topic) row, not the top-level row.
- **Top-level rows:** Act as group headers — no chip, just label.

### 6. Mobile Responsive Design
- **Scope:** Questionnaire wizard and the /report page.
- **Target:** Works well on mobile viewport (375px+).
- **Approach:** CSS/inline-style responsive adjustments — collapse two-column layouts to single column on small screens.

### Claude's Discretion
- Which existing route/component handles the "submission complete" page
- How to detect "questionnaire already completed" status (likely from initiative.status === "SUBMITTED")
- How to get second-level (topic) data from the backend for the expanded heatmap
- Whether the backend matrix already groups by topic or needs an update

</decisions>

<specifics>
## Specific Requirements

- Registration inline on dashboard: only "Initiative Name" and "Sector" are required; all other fields optional
- Completion page CTA button: "Generate heatmap" → navigates to `/report`
- Completion page body text: "Thank you for completing the MAMI Questionnaire. You can now view your MAMI Interoperability heatmap."
- Dashboard removes "Role: USER/ADMIN" text entirely
- Heatmap second-level rows have chips; top-level rows are group headers only
- Mobile breakpoint: 375px minimum, target 768px as the collapse threshold for two-column layouts

</specifics>

<deferred>
## Deferred Ideas

- Admin dashboard UX improvements (out of scope for this phase)
- PDF export / report download (was Phase 5, still deferred)
- Evidence crawling (still Phase 5)

</deferred>

---

*Phase: 09-ux-improvements*
*Context gathered: 2026-03-09 via user specification*
