# Phase 1: Foundation - Context

**Gathered:** 2026-02-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Running API with authentication, RBAC, DSI initiative registration, OpenAPI spec, basic React front-end shell with coe-dsc.nl branding, and Docker Compose deployment. This phase delivers the skeleton that all subsequent phases build on.

</domain>

<decisions>
## Implementation Decisions

### Auth behavior
- Rate limit after 5 failed login attempts (temporary lockout)
- JWT session duration: 24 hours
- No email verification for MVP (added to backlog for future version)
- Password rules: Claude's discretion

### Admin account creation
- Claude's discretion on approach (seed script vs first-user-is-admin)

### Initiative registration
- Fields: name, description, sector/domain, contact person (name + email), organization
- Sector field: predefined dropdown with "Other" free-text option
- Status workflow: Draft → Active → Submitted
- All fields editable anytime (until submitted)
- One initiative per user for MVP

### UI shell & branding
- Sidebar navigation layout (dashboard-style)
- Landing page with MAMI framework intro + call-to-action (register/login)
- Extract actual colors from coe-dsc.nl website
- CoE-DSC / TNO branding on landing page

### Claude's Discretion
- Admin account creation method
- Password complexity rules
- Exact sidebar navigation items
- Loading states and error pages
- Responsive behavior

</decisions>

<specifics>
## Specific Ideas

- Landing page should explain what MAMI is and why DSI leaders should assess their initiative
- Dashboard-style layout with sidebar — suggests a "home" or "overview" view after login
- Status workflow (Draft → Active → Submitted) implies the initiative card/page should show current status prominently

</specifics>

<deferred>
## Deferred Ideas

- Email verification — future version (noted by user)
- Password reset flow — not discussed, likely v2

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-02-14*
