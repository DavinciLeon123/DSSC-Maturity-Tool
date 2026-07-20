---
phase: 06-demo-readiness-admin-panel-password-reset-and-50-user-scalability
plan: 02
subsystem: backend-auth
tags: [password-reset, email, resend, alembic, fastapi, security]
dependency_graph:
  requires: []
  provides: [password-reset-api, resend-email-integration]
  affects: [backend/app/api/v1/auth.py, backend/app/models/user.py]
tech_stack:
  added: [resend==2.23.0]
  patterns: [BackgroundTasks email dispatch, 60-second cooldown via token expiry derivation, dev fallback log-only mode]
key_files:
  created:
    - backend/alembic/versions/g7b5c4d3e2f1_add_password_reset_fields.py
  modified:
    - backend/app/models/user.py
    - backend/app/core/config.py
    - backend/app/schemas/auth.py
    - backend/app/api/v1/auth.py
    - backend/pyproject.toml
    - backend/uv.lock
decisions:
  - Token stored as plain secrets.token_urlsafe(32) string in DB (not JWT)
  - 60-second cooldown derived from password_reset_expires - 30min + 60s (no extra created_at column)
  - Dev fallback: empty RESEND_API_KEY logs reset URL to console instead of sending email
  - Email uses Resend sandbox sender onboarding@resend.dev (no domain verification needed)
  - Plain text body only (no HTML) per CONTEXT.md locked decision
metrics:
  duration_minutes: 3
  tasks_completed: 2
  files_changed: 6
  completed_date: "2026-03-05"
requirements_satisfied:
  - AUTH-RESET-01
  - AUTH-RESET-02
  - AUTH-RESET-03
  - AUTH-RESET-04
---

# Phase 06 Plan 02: Password Reset Backend Summary

**One-liner:** Self-service password reset with 30-min DB tokens, 60-second cooldown, and Resend email dispatch (dev fallback logs to console).

## What Was Built

Full self-service password reset backend: User model extended with two nullable token fields, Alembic migration written, resend SDK installed, two new auth endpoints implemented with security controls.

### POST /auth/forgot-password
- Returns HTTP 202 always — no email enumeration (unknown addresses get same response as registered ones)
- Generates `secrets.token_urlsafe(32)` token stored in user record with 30-minute expiry
- Enforces 60-second cooldown: if `datetime.utcnow() < (expires - 30min) + 60s`, returns HTTP 429
- Dispatches email via `BackgroundTasks.add_task(_send_reset_email, ...)` (non-blocking)

### POST /auth/reset-password
- Looks up user by token value (plain string match, not JWT decode)
- Validates token not expired (`password_reset_expires < datetime.utcnow()` = expired)
- Hashes new password with `hash_password()`, stores in `hashed_password`
- Nulls both `password_reset_token` and `password_reset_expires` immediately (one-time use)

### Email Helper (`_send_reset_email`)
- With `RESEND_API_KEY` set: sends via `resend.Emails.send()` from `MaMi Checker <onboarding@resend.dev>`
- Without API key: logs reset URL to console via `logging.getLogger(__name__).info()`
- Subject: "Reset your MaMi Checker password", plain text body with greeting, link, 30-min notice

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Add reset token fields, config settings, install resend, write Alembic migration | d0dc681 |
| 2 | Implement forgot-password and reset-password endpoints | 15e454d |

## Key Files

### Created
- `backend/alembic/versions/g7b5c4d3e2f1_add_password_reset_fields.py` — Adds `password_reset_token` (String, nullable) and `password_reset_expires` (DateTime, nullable) columns to `user` table. `down_revision = 'f7b8c9d0e1f2'`.

### Modified
- `backend/app/models/user.py` — Two new Optional fields at end of User class
- `backend/app/core/config.py` — `RESEND_API_KEY: str = ""` and `FRONTEND_URL: str = "http://localhost:5173"`
- `backend/app/schemas/auth.py` — `ForgotPasswordRequest` (EmailStr) and `ResetPasswordRequest` (token + new_password with 12-char validation)
- `backend/app/api/v1/auth.py` — New imports (secrets, resend, BackgroundTasks, settings), `_send_reset_email` helper, two new endpoints
- `backend/pyproject.toml` + `backend/uv.lock` — resend>=2.23.0 added

## Decisions Made

1. **Cooldown derivation without extra column:** 60-second cooldown computed as `expires - 30min + 60s` so no `token_created_at` column needed in DB.
2. **Plain token (not JWT):** Token is `secrets.token_urlsafe(32)` stored as plaintext — simpler, DB-validated, one-time use enforced by nulling after use.
3. **Dev fallback:** Empty `RESEND_API_KEY` logs reset URL to console — no email service needed for local development.
4. **Resend sandbox sender:** Uses `onboarding@resend.dev` — works without domain verification for demo/sandbox use.

## Deviations from Plan

None — plan executed exactly as written.

## User Setup Required

Before the password reset feature works end-to-end in production, the following env vars must be set:

| Variable | Source | Required |
|----------|--------|----------|
| `RESEND_API_KEY` | Resend Dashboard -> API Keys -> Create API Key | For production email sending |
| `FRONTEND_URL` | Deployed frontend URL (e.g. `https://mami-checker.up.railway.app`) | For reset link construction |

Without these, the feature works locally — reset links are logged to console instead of emailed.

## Self-Check: PASSED

All files verified present. Both commits confirmed in git log.
- FOUND: backend/app/models/user.py
- FOUND: backend/app/core/config.py
- FOUND: backend/alembic/versions/g7b5c4d3e2f1_add_password_reset_fields.py
- FOUND: backend/app/schemas/auth.py
- FOUND: backend/app/api/v1/auth.py
- FOUND commit: d0dc681
- FOUND commit: 15e454d
