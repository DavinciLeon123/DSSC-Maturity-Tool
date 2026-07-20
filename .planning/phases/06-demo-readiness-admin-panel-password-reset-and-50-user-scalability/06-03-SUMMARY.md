---
phase: 06-demo-readiness-admin-panel-password-reset-and-50-user-scalability
plan: "03"
subsystem: backend-admin-api
tags: [admin, api, demo-management, cascade-delete, csv-export]
dependency_graph:
  requires:
    - app.core.deps.require_admin
    - app.db.session.get_session
    - app.models.user.User
    - app.models.initiative.Initiative
    - app.models.questionnaire.QuestionnaireAnswer
    - app.models.evidence.EvidenceURL
    - app.models.report.ComplianceReport
  provides:
    - GET /api/v1/admin/users
    - DELETE /api/v1/admin/users/{user_id}
    - GET /api/v1/admin/initiatives
    - DELETE /api/v1/admin/initiatives/{initiative_id}
    - GET /api/v1/admin/export
    - POST /api/v1/admin/reset-demo
  affects:
    - backend/app/main.py
tech_stack:
  added: []
  patterns:
    - FastAPI StreamingResponse for CSV download
    - Manual cascade delete order (no DB-level CASCADE FK)
    - Pydantic BaseModel response schemas for admin views
key_files:
  created:
    - backend/app/api/v1/admin.py
  modified:
    - backend/app/main.py
decisions:
  - "get_session imported from app.db.session (not re-exported by app.core.deps)"
  - "require_admin used as per-endpoint function parameter dependency (not router-level dependency)"
  - "CSV export has 8 honest columns (no empty evidence_url placeholder column)"
  - "Manual cascade delete order enforced: QuestionnaireAnswer -> EvidenceURL -> ComplianceReport -> Initiative -> User"
  - "DELETE /admin/users refuses to delete ADMIN role users (403 guard)"
metrics:
  duration: "8 minutes"
  completed: "2026-03-05"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
requirements_covered:
  - ADMN-DEMO-01
  - ADMN-DEMO-02
  - ADMN-DEMO-03
  - ADMN-DEMO-04
  - ADMN-DEMO-05
---

# Phase 06 Plan 03: Admin API Module Summary

**One-liner:** Six protected admin endpoints (list/delete users and initiatives, CSV export, demo reset) using manual child-first cascade delete and StreamingResponse CSV delivery.

## What Was Built

Created `backend/app/api/v1/admin.py` and registered it in `main.py`. The admin module provides six REST endpoints all protected by the `require_admin()` FastAPI dependency.

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/v1/admin/users | List all users with initiative status + answer count |
| DELETE | /api/v1/admin/users/{user_id} | Hard-delete user and all their data |
| GET | /api/v1/admin/initiatives | List all initiatives with owner email + answer count |
| DELETE | /api/v1/admin/initiatives/{initiative_id} | Delete initiative and child rows (user untouched) |
| GET | /api/v1/admin/export | Stream CSV of all users+initiatives+answers |
| POST | /api/v1/admin/reset-demo | Delete all non-admin users and their data |

### Key Implementation Details

**Cascade delete order** (no DB-level CASCADE FK — manual order required):
1. QuestionnaireAnswer rows (for each initiative)
2. EvidenceURL rows (for each initiative)
3. ComplianceReport rows (for each initiative)
4. Initiative row
5. User row (for full user delete; skipped for initiative-only delete)

**CSV export:** StreamingResponse with `text/csv` content-type, 8 columns per row (`user_email`, `initiative_name`, `participant_type`, `initiative_status`, `question_id`, `mami_code`, `answer_value`, `followup_other`). One row per questionnaire answer. Evidence URLs excluded (separate table, not in scope).

**Admin protection:** Every endpoint has `_admin: User = Depends(require_admin)` — 403 Forbidden for non-admin tokens.

**Admin self-protection:** DELETE /admin/users refuses to delete users with `role == "ADMIN"` (returns 403).

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create admin.py with all admin endpoints | 92005bf | backend/app/api/v1/admin.py |
| 2 | Register admin router in main.py | a754c7e | backend/app/main.py |

## Deviations from Plan

### Auto-fixed Issues

None - plan executed exactly as written.

**Import note applied:** The plan correctly noted that `get_session` is not re-exported from `app.core.deps`. Confirmed by reading `deps.py` — imported directly from `app.db.session` as instructed.

## Self-Check: PASSED

- FOUND: backend/app/api/v1/admin.py
- FOUND: 06-03-SUMMARY.md
- FOUND: commit 92005bf (Task 1 - admin.py)
- FOUND: commit a754c7e (Task 2 - main.py registration)
