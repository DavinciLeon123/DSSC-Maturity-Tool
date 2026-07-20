---
phase: 10-survey-completion-text-fix-scroll-to-top-on-wizard-navigation-remove-my-initiative-tab-100-user-scalability-equal-width-heatmap-pills-admin-aggregated-heatmap
plan: "02"
subsystem: backend
tags: [scalability, admin, heatmap, db-pool, api]
dependency_graph:
  requires: []
  provides: [GET /admin/heatmap, db-pool-40-connections]
  affects: [backend/app/db/session.py, backend/app/api/v1/admin.py]
tech_stack:
  added: []
  patterns: [raw-sql-group-by, pydantic-response-models, require-admin-dependency, flat-codes-array-traversal]
key_files:
  created: []
  modified:
    - backend/app/db/session.py
    - backend/app/api/v1/admin.py
decisions:
  - "DB pool raised to pool_size=15, max_overflow=25 (total 40) for 100-user peak concurrency"
  - "Admin heatmap derives dimension keys dynamically from mami_config codes array (not hardcoded must/should/could)"
  - "code_lookup built from flat codes array (category/dimension/topic per code) — matches actual mami-framework.json structure"
metrics:
  duration: "~12 min"
  completed: "2026-03-10"
  tasks: 2
  files: 2
---

# Phase 10 Plan 02: DB Pool Tuning + Admin Aggregated Heatmap Summary

**One-liner:** DB connection pool raised to 40 total connections for 100-user concurrency; GET /admin/heatmap aggregates yes/not_yet/n_a counts per topic cell across all submitted initiatives.

## What Was Built

### Task 1: DB Connection Pool Tuning (commit: 601bda6)

Updated `backend/app/db/session.py`:
- `pool_size`: 10 -> 15
- `max_overflow`: 20 -> 25
- Total max connections: 30 -> 40

Rationale: single uvicorn worker, connections held only during query execution. 100 concurrent users at peak simultaneous save operations are served by the expanded pool without exhaustion.

### Task 2: GET /admin/heatmap Endpoint (commit: 1abee49)

Added to `backend/app/api/v1/admin.py`:

**Response models:**
- `AdminHeatmapCell(yes, not_yet, n_a)` — aggregated counts per topic/dimension cell
- `AdminHeatmapResponse(total_submitted, matrix, topic_structure)` — full heatmap payload

**Endpoint:** `GET /admin/heatmap`
- Protected by `Depends(require_admin)` — returns 403 for non-admin users
- Counts submitted initiatives via `SELECT COUNT(*) FROM initiative WHERE status = 'submitted'`
- Aggregates answer counts with SQL GROUP BY on `mami_code, answer_value`, filtering `WHERE i.status = 'submitted'`
- Builds `code_lookup` from the flat `codes` array in mami_config (correct structure for mami-framework.json)
- Derives dimension keys dynamically from mami_config (not hardcoded) — actual values: `human_readable`, `machine_readable`, `trust_anchors`
- Reuses `_build_topic_structure` from `report_generator.py` for consistent topic structure
- Returns matrix shaped as `{category: {dimension: {topic_id: AdminHeatmapCell}}}`

**Imports added:** `Dict`, `Request` from stdlib/fastapi; `_build_topic_structure` from report_generator.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected mami_config traversal pattern for code_lookup**
- **Found during:** Task 2
- **Issue:** Plan specified building `code_lookup` from `mami_config.get("categories", [])` with nested `dimensions -> recommendations` hierarchy. The actual mami-framework.json uses a flat `codes` array with `category`, `dimension`, `topic` fields per code entry.
- **Fix:** Replaced the nested categories traversal with a flat `mami_config.get("codes", [])` loop. Also replaced hardcoded `dimensions = ["must", "should", "could"]` with dynamic derivation from the codes array (actual values: `human_readable`, `machine_readable`, `trust_anchors`).
- **Files modified:** `backend/app/api/v1/admin.py`
- **Commit:** 1abee49 (included in task commit)

## Success Criteria Verification

- [x] DB pool: pool_size=15, max_overflow=25 (total 40 connections)
- [x] GET /admin/heatmap endpoint exists, protected by require_admin
- [x] Returns matrix of yes/not_yet/n_a counts per cell
- [x] Only submitted initiatives counted in aggregation (WHERE i.status = 'submitted')
- [x] No new Python packages added (all existing imports)
- [x] Python syntax valid (ast.parse passes)

## Self-Check: PASSED

Files verified:
- FOUND: backend/app/db/session.py (pool_size=15, max_overflow=25)
- FOUND: backend/app/api/v1/admin.py (get_admin_heatmap, require_admin, status='submitted')

Commits verified:
- 601bda6: chore(10-02): tune DB connection pool for 100-user concurrency
- 1abee49: feat(10-02): add GET /admin/heatmap aggregated heatmap endpoint
