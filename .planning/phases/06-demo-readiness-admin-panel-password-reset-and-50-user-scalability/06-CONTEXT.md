# Phase 6: Demo Readiness — Context

**Gathered:** 2026-03-03 (updated 2026-03-03)
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 6 prepares the application for a live public demo with ~50 simultaneous users. It delivers:

1. **Admin Panel** — A protected UI where an Admin can view all users and filled-in questionnaires, delete either, download the full dataset, and reset demo data in one click.
2. **Password Reset** — A self-service email-based reset flow (forgot password → email link → new password).
3. **50-User Scalability** — DB connection pool tuned, answer-endpoint rate limiting added, and infrastructure validated for concurrent load.
4. **Frontend Resilience** — Autosave status indicator with rate-limit feedback, Next-button safety during saves, graceful error pages, submission confirmation screen, and 401 token-expiry redirect.

**Out of scope for Phase 6:**
- URL crawling / SSRF protection (Phase 5)
- PDF export (Phase 5)
- Audit logging / heatmap analytics (Phase 5)
- Design team production frontend (deferred Phase 4.5)

</domain>

<decisions>
## Implementation Decisions

### Admin Panel Layout
- **Structure**: One `/admin` route with **three tabs**: "Users" | "Questionnaires" | "Actions"
- **Users tab**: Table of all registered users. Rows are **expandable** — clicking reveals inline details (participant_type, initiative name, number of answers, initiative status, created_at). Each row has a **Delete** action with a confirmation popup.
- **Questionnaires tab**: Table of all initiatives with their compliance status. Each row has a **Delete** action with confirmation.
- **Actions tab**: Contains two actions only:
  - **Download CSV** button — exports full dataset (users + initiatives + answers) as a streamed CSV file
  - **Reset Demo** button — large, visually distinct (red/warning). Clicking opens an "Are you sure?" confirmation modal before firing `POST /api/v1/admin/reset-demo`. This action is protected by `require_admin()` — only admins see or reach this page.
- **Access**: Entire `/admin` route protected by `require_admin()`. Admin link shown in sidebar only when user role = ADMIN.

### Password Reset Flow
- **Trigger**: "Forgot your password?" link on the login page (below the submit button).
- **Flow**: User enters email → backend generates a 30-minute token (stored in DB) → email sent via Resend → user clicks link → enters new password → password updated, token invalidated → redirected to `/login?reset=success`.
- **Token expiry**: **30 minutes** (not 15 — gives demo attendees room if distracted or email is delayed).
- **On expired/used link**: Show error message "This link has expired or has already been used." with a clickable link back to `/forgot-password` to request a new one.
- **Cooldown**: 60-second cooldown between reset requests. If a token was issued less than 60 seconds ago, reject the new request with "Please wait before requesting another reset link." Backend derives this from the existing `password_reset_expires` field (token created at `expires - 30 min`; if `now < created_at + 60s`, reject).
- **Email infrastructure**: Resend SDK. `RESEND_API_KEY` env var in Railway.
  - **From**: `MaMi Checker <onboarding@resend.dev>` (Resend sandbox — no domain verification required)
  - **Subject**: `Reset your MaMi Checker password`
  - **Body**: Plain text only — no HTML template. Message: greeting, one-line explanation, the reset link, expiry notice ("This link expires in 30 minutes").
  - **Fallback** (no `RESEND_API_KEY`): Log the full reset URL to the backend console (`logger.info()`). User sees the same "check your inbox" UI. Zero setup needed for local dev.
- **New DB fields on User**: `password_reset_token` (nullable str) + `password_reset_expires` (nullable datetime). Alembic migration required.
- **New endpoints**: `POST /api/v1/auth/forgot-password` + `POST /api/v1/auth/reset-password`.
- **Frontend routes**: `/forgot-password` (email form) and `/reset-password?token=...` (new password form). Both follow the existing `login.tsx` inline-style pattern (no Ant Design).

### 50-User Scalability
- **DB connection pool**: Explicitly configure SQLAlchemy engine with `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, `pool_recycle=1800`. Current default (pool_size=5) will exhaust under 50 concurrent users. Change in `backend/app/db/session.py`.
- **Rate limiting on answer endpoints**: Apply `slowapi` limiter to `PUT /questionnaire/initiatives/{id}/answers/{qid}` — 60 requests/minute per user. Prevents hammering while allowing fast survey completion.
- **Railway deployment**: Ensure service has 512MB+ memory. Vertical scaling is sufficient for 50 users.

### Frontend Resilience — Autosave & Save Safety
- **Autosave badge**: Visible in the wizard header at all times. States:
  - `Saving...` — grey/neutral, shown while mutation is in-flight
  - `Saved ✓` — green, shown on success
  - `Save failed — retrying` — amber, shown on generic save error (network, 5xx)
  - `Too many saves — slow down` — amber, shown specifically on 429 (rate limit hit); auto-retries after 3 seconds
- **Next button safety**: Next button is **disabled while `Saving...`** (mutation is pending). Re-enabled on either `Saved ✓` or `Save failed`. This prevents users from advancing before their answer is confirmed saved under load.
- **Silent proceed on save-failed**: If save failed and user clicks Next (after re-enable), they proceed silently. The autosave badge already communicated the failure — no additional warning shown.

### Frontend Resilience — Other
- **401 token-expiry redirect**: Axios 401 interceptor clears localStorage and redirects to `/login?session=expired`. Login page shows amber banner: "Your session expired. Please log in again."
- **Submission confirmation screen**: After `POST /initiatives/{id}/submit` succeeds, show a dedicated screen: "Your submission is complete — you can now generate your compliance report." Primary CTA button: "Generate Report" (navigates to `/dashboard` where the generate button lives).
- **Graceful error pages**: Axios `Promise.reject` propagates 5xx to TanStack Query `isError`; wizard shows user-friendly error message for submit failures. No full-page error boundary required.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `require_admin()` dependency in `backend/app/core/deps.py`: Already implemented — all admin endpoints use `Depends(require_admin)` directly
- `slowapi` Limiter: Already wired in `main.py` (`_rate_limit_exceeded_handler` registered) — router only needs `@limiter.limit()` decorator + `request: Request` param
- `login.tsx` inline style pattern: New auth pages (forgot-password, reset-password) copy this exactly — no Ant Design, uses `var(--color-navy)`, `var(--color-green)`, `var(--border-radius-sm)`
- Ant Design `Table` + `Popconfirm` + `Tabs`: Admin panel uses these for tables, row-level delete confirmation, and tab switching

### Established Patterns
- TanStack Router file-based routing: New routes in `_auth/` follow `createFileRoute("/_auth/name")` pattern; `routeTree.gen.ts` regenerates on dev server start (committed manually per STATE.md)
- Password validation: `backend/app/schemas/auth.py` enforces 12-char minimum + common password blocklist — reset-password form matches this (12-char `minLength`)
- Backend upsert: `pg_insert on_conflict_do_update` for answers — relevant to understanding answer endpoint rate limiting scope
- Auth response pattern: `forgot-password` always returns 202 regardless of email existence (prevents email enumeration)

### Integration Points
- `backend/app/db/session.py`: Pool kwargs added here — single-file change
- `backend/app/api/v1/auth.py`: Two new endpoints appended; `resend` import added
- `backend/app/models/user.py`: Two new nullable fields; corresponding Alembic migration
- `frontend/src/lib/api.ts`: 401 interceptor modified to append `?session=expired`
- `frontend/src/routes/_app/questionnaire.tsx` (WizardPage): Autosave badge + Next-button disable + submit mutation added
- `frontend/src/routes/_auth/login.tsx`: `?session=expired` banner (06-04) + `?reset=success` banner + "Forgot password?" link (06-05) — 06-05 depends on 06-04, edits login.tsx sequentially

</code_context>

<specifics>
## Specific Items (Full List)

### From the Product Owner:
1. Admin Panel — View all users (expandable rows with initiative details)
2. Admin Panel — Delete users (hard delete, cascade, with confirmation)
3. Admin Panel — View all filled-in questionnaires
4. Admin Panel — Delete questionnaires independently (with confirmation)
5. Admin Panel — Download entire dataset (CSV, streamed, one-click in Actions tab)
6. Admin Panel — Reset demo data (Actions tab, admin-only, "Are you sure?" modal)
7. User self-service password reset (email-based, forgot password flow)
8. Infrastructure robustness for 50 simultaneous users

### Additional (Claude):
9. DB connection pool tuning — `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, `pool_recycle=1800`
10. Rate limiting on answer endpoints (60 req/min per user via slowapi) with specific "Too many saves" badge
11. Resend email integration — plain text, `MaMi Checker <onboarding@resend.dev>`, console fallback
12. Autosave badge with 4 states (Saving / Saved / Save failed / Too many saves)
13. Next button disabled while save is in-flight
14. Submission confirmation screen — "Generate Report" CTA
15. 401 session-expiry interceptor with banner
16. Expired/used reset link: error + link back to /forgot-password
17. 60-second cooldown between reset requests

</specifics>

<deferred>
## Deferred Ideas

- **Soft delete for users**: Hard delete for demo simplicity. Revisit before going to full production.
- **Refresh tokens / token renewal**: JWT is 24h with no refresh. Fine for demo. Refresh token flow improves long-session UX in production.
- **Sentry / error monitoring**: Post-demo analysis tooling — not required for demo itself.
- **Branded email domain** (e.g., `noreply@coe-dsc.nl`): Requires DNS verification in Resend. Deferred until post-demo when domain is confirmed.
- **Aggregate compliance heatmap (Phase 5)**: Admin analytics across all initiatives.
- **Audit logging (Phase 5)**: Insert-only audit log for all admin and user actions.
- **PDF export (Phase 5)**: WeasyPrint PDF download.

</deferred>

---

*Phase: 06-demo-readiness-admin-panel-password-reset-and-50-user-scalability*
*Context gathered: 2026-03-03*
