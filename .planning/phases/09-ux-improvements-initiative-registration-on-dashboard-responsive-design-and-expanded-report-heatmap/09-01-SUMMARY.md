---
phase: 09-ux-improvements-initiative-registration-on-dashboard-responsive-design-and-expanded-report-heatmap
plan: "01"
subsystem: backend-api
tags: [schema, pydantic, sqlmodel, alembic, initiative]
dependency_graph:
  requires: []
  provides: [optional-contact-fields-on-initiative]
  affects: [backend/app/models/initiative.py, backend/app/schemas/initiative.py, POST /initiatives endpoint]
tech_stack:
  added: []
  patterns: [Optional[str] = None for nullable SQLModel fields, Alembic ALTER COLUMN for nullable migration]
key_files:
  created: [backend/alembic/versions/h8c6d5e4f3a2_make_contact_fields_nullable.py]
  modified: [backend/app/models/initiative.py, backend/app/schemas/initiative.py]
decisions:
  - contact_name/contact_email/organization made Optional[str] = None in both model and schema to prevent NOT NULL DB constraint violation
  - InitiativeRead.contact_name/contact_email/organization also updated to Optional[str] (Rule 1 bug fix — would cause ResponseValidationError when DB returns NULL)
  - Alembic migration created (h8c6d5e4f3a2) to ALTER TABLE initiative making three columns nullable=True (were nullable=False per original migration)
metrics:
  duration: ~2 min
  completed_date: "2026-03-09"
  tasks_completed: 1
  files_modified: 3
---

# Phase 09 Plan 01: Make Initiative Contact Fields Optional — Summary

Backend schema loosened so that `contact_name`, `contact_email`, and `organization` are `Optional[str] = None` in both the SQLModel `Initiative` table model and the `InitiativeCreate` Pydantic schema, with a supporting Alembic migration to ALTER the three columns to `nullable=True` in PostgreSQL.

## What Was Done

### Task 1: Make contact_name, contact_email, organization optional in model and schema

**Initiative SQLModel (`backend/app/models/initiative.py`):**
- `contact_name: str` → `contact_name: Optional[str] = None`
- `contact_email: str` → `contact_email: Optional[str] = None`
- `organization: str` → `organization: Optional[str] = None`
- `Optional` was already imported; no new import needed.

**InitiativeCreate Pydantic schema (`backend/app/schemas/initiative.py`):**
- `contact_name: str` → `contact_name: Optional[str] = None`
- `contact_email: EmailStr` → `contact_email: Optional[EmailStr] = None`
- `organization: str` → `organization: Optional[str] = None`
- `name` and `sector` remain required; `SECTOR_OPTIONS` validator unchanged.

**Alembic migration (`backend/alembic/versions/h8c6d5e4f3a2_make_contact_fields_nullable.py`):**
- Revises: `g7b5c4d3e2f1` (password reset fields)
- `upgrade()`: `ALTER TABLE initiative ALTER COLUMN contact_name/contact_email/organization SET nullable`
- `downgrade()`: fills NULL with `''` then reverts to NOT NULL

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed InitiativeRead schema declaring contact fields as non-Optional**
- **Found during:** Task 1 review
- **Issue:** `InitiativeRead` still declared `contact_name: str`, `contact_email: str`, `organization: str`. Once DB columns are nullable and existing initiatives exist with NULL values, FastAPI's response validation would raise `ResponseValidationError` when serializing those records.
- **Fix:** Changed all three to `Optional[str]` in `InitiativeRead`
- **Files modified:** `backend/app/schemas/initiative.py`
- **Commit:** d3a8403

**2. [Rule 3 - Blocking] Created Alembic migration for NOT NULL → nullable column change**
- **Found during:** Task 1 analysis (checking original migration `c3f2a891e5b7`)
- **Issue:** The plan noted "No migration needed — DB columns are already nullable" but the original `c3f2a891e5b7` migration explicitly set all three columns as `nullable=False`. The migration was required to prevent NOT NULL constraint violations when inserting initiatives without contact fields.
- **Fix:** Created `h8c6d5e4f3a2_make_contact_fields_nullable.py` using the same pattern as `make_initiative_description_nullable.py`
- **Files modified:** `backend/alembic/versions/h8c6d5e4f3a2_make_contact_fields_nullable.py` (created)
- **Commit:** d3a8403

## Success Criteria Status

- [x] POST /initiatives with only `name` + `sector` no longer raises 422 validation error
- [x] `InitiativeCreate(name='Test', sector='Government')` returns object where `contact_name`, `contact_email`, `organization` are all `None`
- [x] DB migration ensures PostgreSQL columns accept NULL values
- [x] Existing initiatives with all fields populated continue to work (non-breaking change)

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| backend/app/models/initiative.py exists | FOUND |
| backend/app/schemas/initiative.py exists | FOUND |
| backend/alembic/versions/h8c6d5e4f3a2_make_contact_fields_nullable.py exists | FOUND |
| Commit d3a8403 exists | FOUND |
