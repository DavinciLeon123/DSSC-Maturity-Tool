---
phase: 14
slug: scoring-engine-replacement
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-24
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-xdist (parallel) + pytest-asyncio (auto mode) |
| **Config file** | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd backend && uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` |
| **Full suite command** | `cd backend && uv run pytest tests/ -n auto -m "not perf" -q` (staging-onward gate per CLAUDE.md) |
| **Estimated runtime** | ~30-60 seconds (per CLAUDE.md's ~3 min full-workflow figure for a similarly-sized Phase 12/13 suite) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/ -n auto -m "not perf and not benchmark" -q`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -n auto -m "not perf" -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | SCOR-01 | — | `dimension_score = sum/count` per category, 1.0-5.0 range | unit | `pytest tests/services/test_dimension_scoring.py -x` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | SCOR-02 | — | No question/category weighting anywhere | unit | `pytest tests/services/test_dimension_scoring.py -x` (equal-answer, different-question-count categories both average correctly) | ❌ W0 | ⬜ pending |
| 14-0X-0X | TBD | TBD | SCOR-03 | — | ZEN/MoSCoW fully removed from codebase + dependency manifest | static/negative | `pytest tests/test_zen_removed.py -x` (mirrors Phase 13's `test_evidence_removed.py` AST-walk/substring-scan pattern) | ❌ W0 | ⬜ pending |
| 14-0X-0X | TBD | TBD | SCOR-04 | T-14-01 | 422 on incomplete assessment for all 5 score/report endpoints | integration | `pytest tests/api/test_reports.py tests/api/test_scoring.py -x` | ❌ W0 (`test_scoring.py` does not exist yet) | ⬜ pending |
| 14-0X-0X | TBD | TBD | SCOR-04 (access control) | T-14-01 | Ownership check (`403`) fires before the completion-gate `422` — no endpoint reordering that leaks initiative existence/completeness | integration | `pytest tests/api/test_scoring.py -k ownership -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*(Exact task IDs are assigned by the planner; rows above map to the requirement/behavior each must cover, per RESEARCH.md's Phase Requirements → Test Map.)*

---

## Wave 0 Requirements

- [ ] `tests/services/test_dimension_scoring.py` — new file; covers SCOR-01/02 via unit tests for `compute_dimension_scores`/`assert_assessment_complete` against the existing `session` fixture + `make_answer`/`make_assessment` factories (no factory changes needed)
- [ ] `tests/api/test_scoring.py` — new file; does not exist today. D-04's full response-shape change to `/initiatives/{id}/score` currently has **zero** existing test coverage (confirmed by RESEARCH.md directory listing) — needs at minimum a happy-path test, a 422-incomplete test, and an ownership-check-fires-first test
- [ ] `tests/test_zen_removed.py` — new file (recommended, not optional per Validation Sign-Off below); mirrors Phase 13's `test_evidence_removed.py` AST-walk/substring-scan pattern to lock in SCOR-03 as a regression-proof static check, rather than relying on ruff/mypy incidentally catching orphaned imports

---

## Manual-Only Verifications

*None — every phase behavior (dimension scoring math, ZEN/MoSCoW removal, completion gating, existing endpoint adaptation) has a direct automated-test path per the map above. The old frontend rendering against the now-changed/absent JSON fields (per CONTEXT.md's accepted interim breakage) is explicitly out of scope for this phase's verification — Phase 15/16 own that UI.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`test_dimension_scoring.py`, `test_scoring.py`, `test_zen_removed.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
