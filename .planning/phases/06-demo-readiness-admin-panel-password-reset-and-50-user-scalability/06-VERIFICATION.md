---
phase: 06-demo-readiness-admin-panel-password-reset-and-50-user-scalability
verified: 2026-03-06T12:00:00Z
status: human_needed
score: 9/9 must-haves verified
re_verification: false
human_verification:
  - test: "Password reset email delivery"
    expected: "User receives email at registered address with a working /reset-password?token=... link within 30 seconds; link expires after 30 minutes; clicking it twice fails on second use"
    why_human: "Requires live Resend API key and an actual inbox; dev fallback logs to console only"
  - test: "50-user concurrency under load"
    expected: "50 simultaneous answer saves complete without HTTP 5xx; DB pool does not exhaust"
    why_human: "Requires load testing tool (k6/locust) against a live Railway deployment; cannot verify statically"
  - test: "Autosave 429 badge and 3-second auto-reset"
    expected: "Saving rapidly triggers 'Too many saves — slow down' badge; badge resets to idle after 3 seconds; no re-submission of the last answer occurs"
    why_human: "Requires browser interaction with rate-limiting active; timer behaviour only verifiable at runtime"
  - test: "Session expiry redirect and banner"
    expected: "Expiring or revoking a JWT mid-session causes the next API call to redirect to /login?session=expired showing the amber 'Your session expired' banner"
    why_human: "Requires manipulating a live token; cannot be verified statically"
  - test: "Admin panel full flow"
    expected: "Admin can view expandable user rows, delete a user (row disappears), download CSV (file opens in spreadsheet), click Reset Demo (modal appears, confirms, non-admin rows vanish)"
    why_human: "Multi-step browser interaction; expandable row render and modal confirm require visual inspection"
---

# Phase 6: Demo Readiness Verification Report

**Phase Goal:** Application is ready for a live public demo with ~50 simultaneous users: admins can manage and export all data, users can reset their password via email, the database connection pool is tuned for concurrency, and the frontend handles slow saves (with rate-limit feedback), session expiry, and submission gracefully
**Verified:** 2026-03-06T12:00:00Z
**Status:** human_needed — all automated checks pass; 5 items require live/browser verification
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Admin can view all users (expandable rows with initiative details) and all questionnaire submissions in a 3-tab protected admin panel, and delete either | VERIFIED | `frontend/src/routes/_app/admin.tsx`: 3-tab Tabs component (users/questionnaires/actions), expandedRowRender with initiative details, Popconfirm Delete on both tabs; beforeLoad guard redirects non-ADMIN to /dashboard |
| 2 | Admin can download the complete dataset as a single CSV file from the Actions tab | VERIFIED | `admin.tsx` Actions tab has Download CSV button calling `api.get("/admin/export", { responseType: "blob" })` with blob-to-anchor download; backend `GET /admin/export` streams CSV via StreamingResponse |
| 3 | Admin can reset all demo data via a single confirmed action in the Actions tab | VERIFIED | `admin.tsx` handleResetDemo calls Modal.confirm then `POST /api/v1/admin/reset-demo`; backend deletes all non-ADMIN users with cascade |
| 4 | User can request a password reset via email link (30-min expiry, 60-sec cooldown), set a new password, and log in successfully | VERIFIED (automated path) | Backend: `POST /auth/forgot-password` (202, 30-min token, 60-sec cooldown, BackgroundTasks Resend); `POST /auth/reset-password` (token lookup, expiry check, hash_password, null token); Frontend: `/forgot-password` and `/reset-password` pages wired to these endpoints |
| 5 | 50 simultaneous users can fill in and save questionnaire answers without DB connection pool exhaustion | VERIFIED (config only) | `session.py`: `pool_size=10, max_overflow=20, pool_pre_ping=True, pool_recycle=1800`; endpoint rate-limited at 60/min per IP via `@limiter.limit("60/minute")` |
| 6 | The wizard shows a live 4-state autosave status at all times; Next button disabled while save is in-flight | VERIFIED | `WizardPage.tsx`: `AutosaveBadge` component with 4 states (saving/saved/failed/rate-limited); `isNextDisabled = !isCurrentTopicComplete \|\| isSaving \|\| badgeState === "saving"` |
| 7 | An expired or invalid JWT redirects the user to /login with a visible "session expired" message | VERIFIED | `api.ts` 401 interceptor: `window.location.href = "/login?session=expired"`; `login.tsx`: amber banner rendered when `(search as Record<string,string>).session === "expired"` |
| 8 | After submitting the questionnaire, the user sees a clear confirmation screen with a CTA to generate their report | VERIFIED | `WizardPage.tsx`: `submitted` state set by `submitMutation.onSuccess`; early return renders confirmation div with "Your submission is complete" heading and "Generate Report" button navigating to /dashboard |
| 9 | Network errors and server errors show a user-friendly error message rather than a blank screen | VERIFIED | `api.ts` 5xx propagated via `Promise.reject`; WizardPage `submitError` shown as red error div; forgot/reset-password pages show inline error messages on network failure |

**Score:** 9/9 truths verified (5 additionally require human/runtime confirmation)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/db/session.py` | SQLAlchemy engine with tuned pool config | VERIFIED | `pool_size=10, max_overflow=20, pool_pre_ping=True, pool_recycle=1800` all present |
| `backend/app/api/v1/questionnaire.py` | Rate-limited upsert endpoint | VERIFIED | `@limiter.limit("60/minute")` decorator present; `request: Request` is first parameter (correct slowapi order) |
| `backend/app/api/v1/initiatives.py` | Submit endpoint | VERIFIED | `POST /{initiative_id}/submit` sets `InitiativeStatus.submitted`, returns 200 |
| `backend/app/models/user.py` | User model with reset token fields | VERIFIED | `password_reset_token: Optional[str] = None` and `password_reset_expires: Optional[datetime] = None` present |
| `backend/alembic/versions/g7b5c4d3e2f1_add_password_reset_fields.py` | DB migration for reset fields | VERIFIED | Both nullable columns added; `down_revision = 'f7b8c9d0e1f2'` matches actual HEAD (`make_initiative_description_nullable.py` has `revision = 'f7b8c9d0e1f2'`) |
| `backend/app/core/config.py` | RESEND_API_KEY and FRONTEND_URL settings | VERIFIED | Both fields present with correct defaults (`""` and `"http://localhost:5173"`) |
| `backend/app/api/v1/auth.py` | forgot-password + reset-password endpoints | VERIFIED | Both endpoints implemented with cooldown logic, BackgroundTasks email dispatch, token nulling |
| `backend/app/schemas/auth.py` | ForgotPasswordRequest + ResetPasswordRequest schemas | VERIFIED | Both present with `field_validator` for 12-char minimum on new_password |
| `backend/app/api/v1/admin.py` | All 6 admin endpoints | VERIFIED | GET /admin/users, DELETE /admin/users/{id}, GET /admin/initiatives, DELETE /admin/initiatives/{id}, GET /admin/export, POST /admin/reset-demo all present with `_admin: User = Depends(require_admin)` |
| `backend/app/main.py` | admin_router registered | VERIFIED | `from app.api.v1.admin import router as admin_router` and `app.include_router(admin_router, prefix="/api/v1")` both present |
| `frontend/src/lib/api.ts` | 401 interceptor with session=expired redirect | VERIFIED | `window.location.href = "/login?session=expired"` in 401 branch |
| `frontend/src/routes/_auth/login.tsx` | Session-expired and reset-success banners + forgot-password link | VERIFIED | `sessionExpired` amber banner, `resetSuccess` green banner, and "Forgot your password?" link all present |
| `frontend/src/components/questionnaire/WizardPage.tsx` | AutosaveBadge + Next button safety + submission confirmation | VERIFIED | `AutosaveBadge` component with 4 states; `isNextDisabled` includes `badgeState === "saving"`; `submitted` early-return with confirmation screen |
| `frontend/src/routes/_auth/forgot-password.tsx` | Email form calling POST /auth/forgot-password | VERIFIED | Form POSTs to `/auth/forgot-password`, shows success state after 202 |
| `frontend/src/routes/_auth/reset-password.tsx` | New password form with token from URL | VERIFIED | Reads `?token=` via `useSearch`; POSTs to `/auth/reset-password`; redirects to `/login?reset=success` on success; guards against missing token |
| `frontend/src/routes/_app/admin.tsx` | Admin panel with 3-tab layout | VERIFIED | `createFileRoute("/_app/admin")` with beforeLoad ADMIN guard; 3 tabs via Ant Design `Tabs items`; expandable rows; Popconfirm deletes; CSV download; Modal.confirm reset |
| `frontend/src/components/layout/Sidebar.tsx` | Conditional Admin link for ADMIN role | VERIFIED | `useQuery` for `/auth/me`; `isAdmin = currentUser?.role === "ADMIN"`; Admin entry spread into navItems only when isAdmin |
| `frontend/src/routeTree.gen.ts` | All 4 new routes registered | VERIFIED | `/_auth/forgot-password`, `/_auth/reset-password`, `/_app/admin` all imported and registered in route tree |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/db/session.py` | PostgreSQL | `create_engine` pool kwargs | WIRED | `pool_size=10` confirmed in file |
| `backend/app/api/v1/questionnaire.py` | slowapi limiter | `@limiter.limit` + `request: Request` first param | WIRED | Decorator on line 35; `request: Request` is first positional param on line 37 |
| `backend/app/api/v1/auth.py` | `resend.Emails.send()` | `BackgroundTasks.add_task(_send_reset_email)` | WIRED | `background_tasks.add_task(...)` in forgot_password endpoint; `_send_reset_email` calls `resend.Emails.send(params)` when `api_key` is non-empty |
| `backend/app/api/v1/auth.py` | `user.password_reset_token = None` | After successful reset use | WIRED | Lines 183-184: `user.password_reset_token = None` and `user.password_reset_expires = None` after password hash |
| `backend/app/api/v1/auth.py` | 60-second cooldown | `timedelta(seconds=60)` derivation | WIRED | `token_created_at = expires - timedelta(minutes=30); if now < token_created_at + timedelta(seconds=60): raise 429` |
| `backend/app/api/v1/admin.py` | `require_admin()` | `Depends(require_admin)` on every endpoint | WIRED | `_admin: User = Depends(require_admin)` present on all 6 endpoints |
| `DELETE /admin/users/{id}` | cascade delete tables | manual child-first order | WIRED | `_delete_initiative_children` deletes QuestionnaireAnswer → EvidenceURL → ComplianceReport; then initiative, then user |
| `frontend/src/lib/api.ts` | `/login?session=expired` | Axios 401 interceptor | WIRED | `window.location.href = "/login?session=expired"` confirmed |
| `frontend/src/routes/_app/questionnaire.tsx (WizardPage)` | `POST /initiatives/{id}/submit` | `submitMutation.mutateAsync()` on Finish | WIRED | `api.post(\`/initiatives/${initiativeId}/submit\`)` in WizardPage.tsx line 140; called from `handleNext` when `isFinish` is true |
| `frontend/src/routes/_app/questionnaire.tsx (WizardPage)` | 429 handling | `onError` checks `status === 429` | WIRED | Line 127: `if (status === 429)` sets badge to "rate-limited" and calls `setTimeout(..., 3000)` |
| `frontend/src/routes/_app/admin.tsx` | `GET /api/v1/admin/export` | `api.get(..., { responseType: "blob" })` + createObjectURL download | WIRED | `handleExport` function on lines 111-125 |
| `frontend/src/routes/_app/admin.tsx` | `POST /api/v1/admin/reset-demo` | `useMutation` + `Modal.confirm` | WIRED | `resetDemoMutation.mutateAsync()` called inside `Modal.confirm.onOk` |
| `frontend/src/routes/_auth/forgot-password.tsx` | `POST /api/v1/auth/forgot-password` | `fetch` with JSON body | WIRED | `fetch(..."/auth/forgot-password"...)` with `{ email }` body |
| `frontend/src/routes/_auth/reset-password.tsx` | `POST /api/v1/auth/reset-password` | `fetch` with `{ token, new_password }` | WIRED | Lines 44-49: `fetch(..."/auth/reset-password"...)` with token from URL and newPassword |
| `frontend/src/components/layout/Sidebar.tsx` | `/admin` route | conditional `isAdmin` in navItems | WIRED | `...(isAdmin ? [{ label: "Admin", to: "/admin" }] : [])` spread |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ADMN-DEMO-01 | 06-03, 06-06 | Admin can view all users with expandable initiative details | SATISFIED | `GET /admin/users` returns `AdminUserRow[]` with initiative fields; frontend expandedRowRender shows participant_type, initiative_name, initiative_status, answer_count |
| ADMN-DEMO-02 | 06-03, 06-06 | Admin can delete users (hard delete, cascade) | SATISFIED | `DELETE /admin/users/{id}` with child-first cascade; Popconfirm in Users tab; ADMIN rows show "Protected" |
| ADMN-DEMO-03 | 06-03, 06-06 | Admin can view and delete questionnaire submissions | SATISFIED | `GET /admin/initiatives` and `DELETE /admin/initiatives/{id}`; Questionnaires tab with Popconfirm |
| ADMN-DEMO-04 | 06-03, 06-06 | Admin can export all data as CSV | SATISFIED | `GET /admin/export` StreamingResponse; frontend blob download with auth header |
| ADMN-DEMO-05 | 06-03, 06-06 | Admin can reset demo data (wipe non-admin users) | SATISFIED | `POST /admin/reset-demo`; Actions tab with Modal.confirm confirmation |
| AUTH-RESET-01 | 06-02, 06-05 | Login page has Forgot password? link | SATISFIED | `/forgot-password` link present in login.tsx |
| AUTH-RESET-02 | 06-02, 06-05 | User can request reset email with cooldown | SATISFIED | `POST /auth/forgot-password`: 202, 30-min token, 60-sec cooldown (429); frontend shows success message |
| AUTH-RESET-03 | 06-02, 06-05 | User can set new password via token link | SATISFIED | `POST /auth/reset-password`: validates token + expiry, hashes password, nulls token; redirects to /login?reset=success |
| AUTH-RESET-04 | 06-02, 06-05 | Graceful error for invalid/expired token | SATISFIED | Backend returns 400; reset-password.tsx shows `data.detail` as red error |
| INFR-SCALE-01 | 06-01 | DB connection pool tuned for 50 concurrent users | SATISFIED | `pool_size=10, max_overflow=20` in session.py |
| INFR-SCALE-02 | 06-01 | Answer endpoint rate-limited (60/min per IP) | SATISFIED | `@limiter.limit("60/minute")` on upsert_answer with correct `request: Request` first param |
| INFR-SCALE-03 | 06-01 | Railway 512MB memory requirement documented | SATISFIED | Comment in session.py: "Railway: ensure service has 512MB+ memory (verified via Railway dashboard)" |
| UX-RESIL-01 | 06-04 | 4-state autosave badge; Next disabled while saving | SATISFIED | AutosaveBadge with saving/saved/failed/rate-limited states; isNextDisabled includes `badgeState === "saving"` |
| UX-RESIL-02 | 06-04 | 401 JWT expiry redirects to /login?session=expired with banner | SATISFIED | api.ts interceptor + login.tsx amber banner |
| UX-RESIL-03 | 06-04 | Finish button submits; confirmation screen shown | SATISFIED | submitMutation calls POST /submit; `submitted` state triggers confirmation screen with "Generate Report" CTA |
| UX-RESIL-04 | 06-04 | Network/server errors show user-friendly message | SATISFIED | Promise.reject propagation from api.ts; submitError div in WizardPage; inline error handling in auth forms |

**Orphaned requirement IDs:** ADMN-DEMO-01 through 05, AUTH-RESET-01 through 04, INFR-SCALE-01 through 03, and UX-RESIL-01 through 04 (16 IDs total) do not appear in `.planning/REQUIREMENTS.md`. They are defined only in the ROADMAP.md phase block and PLAN frontmatter. This is not a blocker — the requirements exist and are covered by the implementation — but REQUIREMENTS.md was not updated to include Phase 6 requirements in its traceability table.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/routes/_auth/forgot-password.tsx` | 9 | `const navigate = useNavigate()` declared but `navigate()` never called in the component body | Info | Dead code; does not affect functionality; `navigate` is imported from TanStack Router but redirect after success was omitted (the page shows a static success state instead, which is acceptable UX) |

No blockers or warnings found. The `placeholder` string at reset-password.tsx line 87 is an HTML input placeholder attribute — not a code stub.

---

## Human Verification Required

### 1. Password Reset Email Delivery

**Test:** With `RESEND_API_KEY` set to a valid key, request a password reset for a real email address.
**Expected:** Email arrives in inbox within 30 seconds from `MaMi Checker <onboarding@resend.dev>` with subject "Reset your MaMi Checker password"; plain text body contains the reset link; link works; using the same link a second time shows "Invalid or expired reset token".
**Why human:** Requires live Resend API credentials and an actual inbox; dev fallback only logs the link to the console.

### 2. 50-User Concurrency Under Load

**Test:** Use a load-testing tool (k6 or locust) to simulate 50 concurrent users each saving a questionnaire answer simultaneously against the Railway deployment.
**Expected:** All 50 requests return 200; no 500/503 errors; no DB pool exhaustion log entries.
**Why human:** Cannot verify pool behaviour statically; requires a live deployed environment with real PostgreSQL.

### 3. Autosave 429 Badge and 3-Second Auto-Reset

**Test:** In a browser session on the questionnaire page, rapidly click answer buttons to trigger the 60/min rate limit.
**Expected:** Badge transitions: idle → Saving... → Too many saves — slow down (amber); returns to idle after 3 seconds; Next button re-enables; no duplicate submission of the throttled answer.
**Why human:** Timer behaviour and badge state transitions require browser interaction; rate limit cannot be triggered in a static check.

### 4. Session Expiry Redirect and Banner

**Test:** Log in, then in another browser tab invalidate the JWT (or wait for expiry / manually clear the token on the server side), then trigger any API call in the app.
**Expected:** The app immediately redirects to /login; the amber "Your session expired. Please log in again." banner is visible above the Sign In form.
**Why human:** Requires manipulating a live token; the redirect path exists in code but can only be observed at runtime.

### 5. Admin Panel Full Flow

**Test:** Log in as ADMIN, navigate to /admin, and: (a) expand a user row to verify initiative details appear inline; (b) delete a non-admin user and confirm the row disappears; (c) click Download CSV and open the file; (d) click Reset Demo Data, confirm the modal, and verify non-admin rows are gone from the Users tab.
**Expected:** All actions complete without errors; sidebar shows Admin link only for the ADMIN account (not for a regular user account).
**Why human:** Multi-step browser interaction; expandable row rendering and Ant Design modal confirm require visual inspection against a live DB.

---

## Summary

All 9 observable success criteria from the ROADMAP.md are confirmed VERIFIED through static code analysis. All 16 plan-level must-haves pass all three verification levels (exists, substantive, wired). The Alembic migration chain is correct (`g7b5c4d3e2f1` revises `f7b8c9d0e1f2`, which is the actual current HEAD). The resend SDK is installed. The routeTree.gen.ts is up to date with all 4 new routes (`/forgot-password`, `/reset-password`, `/admin`). No blocker anti-patterns were found.

The only gap is that the 16 Phase 6 requirement IDs are not backfilled into REQUIREMENTS.md, but this does not block the implementation from working.

Five items require live or browser-based confirmation before the demo: email delivery, concurrency under load, the 429 rate-limit badge, session expiry redirect, and the full admin panel workflow.

---

_Verified: 2026-03-06T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
