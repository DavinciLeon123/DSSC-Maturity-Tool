---
phase: 09-ux-improvements-initiative-registration-on-dashboard-responsive-design-and-expanded-report-heatmap
plan: "02"
subsystem: frontend-dashboard
tags: [dashboard, initiative, registration, antd, react, ux]
dependency_graph:
  requires: [optional-contact-fields-on-initiative]
  provides: [inline-initiative-registration-on-dashboard, dashboard-questionnaire-cta]
  affects: [frontend/src/routes/_app/dashboard.tsx]
tech_stack:
  added: []
  patterns: [antd Select/Input/Tag for inline form, hasNoInitiative state pattern for 404 detection, conditional CTA based on initiative.status]
key_files:
  created: []
  modified: [frontend/src/routes/_app/dashboard.tsx]
decisions:
  - SECTOR_OPTIONS copied exactly from initiative.tsx (Healthcare/Finance/Government/Energy/Education/Transport/Agriculture/Other)
  - hasNoInitiative state set only on HTTP 404 from GET /initiatives/me — other errors remain silent (pre-existing behaviour)
  - handleGenerateReport preserved — kept as secondary action alongside new questionnaire CTA
  - Loading state shown only when !hasNoInitiative && !initiative && !error (avoids flash between fetch and 404 detection)
  - regForm uses plain controlled state (not antd Form) — consistent with initiative.tsx pattern and lighter weight
metrics:
  duration: ~2 min
  completed_date: "2026-03-09"
  tasks_completed: 1
  files_modified: 1
---

# Phase 09 Plan 02: Dashboard Inline Initiative Registration — Summary

Dashboard rewritten to serve as the single entry point for initiative registration: shows an inline Name + Sector form when the user has no initiative, and shows initiative details with a "Start Questionnaire" / "Retake Questionnaire" CTA once registered. The "Role: USER/ADMIN" label is removed entirely.

## What Was Done

### Task 1: Remove role label and add inline initiative registration form

**`frontend/src/routes/_app/dashboard.tsx`:**

1. **Removed Role label** — deleted the `<p>Role: {user.role}</p>` paragraph from the welcome card entirely.

2. **Expanded Initiative interface** — replaced minimal `{ id, name, status }` with `FullInitiative` that includes `sector`, `sector_other`, `contact_name`, `contact_email`, `organization`, `description` (all optional except id/name/status).

3. **Added `hasNoInitiative` state** — catches HTTP 404 from `GET /initiatives/me` and sets `hasNoInitiative(true)`. Previously the catch block was silent.

4. **Added registration form state** — `regForm`, `regLoading`, `regError` for the inline form.

5. **Added `handleRegisterInitiative`** — `POST /initiatives` with `{ name, sector, sector_other? }`, sets initiative on success and clears `hasNoInitiative`.

6. **Added `SECTOR_OPTIONS` constant** — copied from `initiative.tsx`: Healthcare, Finance, Government, Energy, Education, Transport, Agriculture, Other.

7. **Inline registration form rendered** when `hasNoInitiative && !initiative`:
   - Card: "Register Your Initiative" heading + subtitle
   - antd Input for Initiative Name
   - antd Select for Sector (SECTOR_OPTIONS)
   - Conditional Input for "Other" sector detail
   - Submit Button (type="primary", loading state)
   - Error Alert on failure

8. **Initiative details + CTA rendered** when `initiative` is set:
   - Card showing initiative name, antd Tag for status
   - Sector display (with sector_other if present)
   - "Start Questionnaire" button when `initiative.status !== "submitted"`
   - "Retake Questionnaire" button when `initiative.status === "submitted"`
   - Both navigate to `/questionnaire`
   - Preserved "Generate Compliance Report" button (secondary action)

## Deviations from Plan

None — plan executed exactly as written.

## Success Criteria Status

- [x] TypeScript build passes with no errors (`tsc -b && vite build` succeeded)
- [x] "Role: USER" / "Role: ADMIN" text absent from dashboard output
- [x] Inline form renders with Name + Sector fields for users with no initiative
- [x] Form submits via POST /initiatives with only name + sector
- [x] On success, initiative details card replaces the form
- [x] "Start Questionnaire" shown when initiative.status !== "submitted"
- [x] "Retake Questionnaire" shown when initiative.status === "submitted"

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| frontend/src/routes/_app/dashboard.tsx exists | FOUND |
| Commit 1131030 exists | FOUND |
| Build passes (tsc -b && vite build) | PASSED |
