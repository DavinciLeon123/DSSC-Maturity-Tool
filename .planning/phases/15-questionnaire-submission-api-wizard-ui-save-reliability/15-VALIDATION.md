---
phase: 15
slug: questionnaire-submission-api-wizard-ui-save-reliability
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-24
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Backend: pytest 9.1.1 + pytest-xdist, real-Postgres via `testcontainers[postgres]` fixtures (`backend/tests/conftest.py`). Frontend: Vitest 4.1.10 + Testing Library (installed Phase 12; only `TopNav.test.tsx` exists today — no wizard/questionnaire component tests yet) |
| **Config file** | `backend/pyproject.toml` `[tool.pytest.ini_options]`; `frontend/vite.config.ts`/vitest config (standard Vitest setup per existing `TopNav.test.tsx`) |
| **Quick run command** | `cd backend && uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` |
| **Full suite command** | `cd backend && uv run pytest tests/ -n auto -m "not perf" -q` (staging-onward gate per CLAUDE.md) |
| **Estimated runtime** | ~30-60 seconds (per Phase 13/14 precedent at similar test-file count) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/ -n auto -m "not perf and not benchmark" -q`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -n auto -m "not perf" -q`
- **Before `/gsd-verify-work`:** Full suite must be green, plus the manual-only UAT items below walked through conversationally
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 15-0X-0X | TBD | TBD | SAVE-03 | T-15-01 | `get_user_or_ip_key` returns a JWT-derived per-user key for a valid Bearer token, falls back to IP for missing/malformed tokens — never trusts a spoofable client header | unit | `pytest tests/api/test_questionnaire_answers.py -k rate_limit -x` | ❌ W0 (new test, new function) | ⬜ pending |
| 15-0X-0X | TBD | TBD | HIST-01 | T-15-03 | Retake creates `version = max(existing)+1`; concurrent-race case does not produce duplicate/skipped version numbers | unit + integration | `pytest tests/api/test_questionnaire_answers.py -k version_increment -x` | ❌ W0 (new test, new logic) | ⬜ pending |
| 15-0X-0X | TBD | TBD | HIST-02 | T-15-04 | `GET /initiatives/{id}/assessments` returns only the requesting user's submitted assessments with correct `dimension_scores`; 404/403 on non-owned/nonexistent initiative | integration | `pytest tests/api/test_initiatives.py -k assessment_history -x` (or new `test_assessment_history.py`) | ❌ W0 (greenfield endpoint) | ⬜ pending |
| 15-0X-0X | TBD | TBD | HIST-01 (existing regression) | — | Existing `test_questionnaire_answers.py`/`test_questionnaire_schemas.py` assertions that hardcode `version == 1` are updated for the new increment logic | unit | `pytest tests/api/test_questionnaire_answers.py tests/schemas/test_questionnaire_schemas.py -x` | ✅ (existing files, need updates) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*(Exact task IDs are assigned by the planner; rows above map to the requirement/behavior each must cover, per RESEARCH.md's Phase Requirements → Test Map and Wave 0 Gaps.)*

---

## Wave 0 Requirements

- [ ] `backend/tests/api/test_questionnaire_answers.py` — add version-increment test cases (creates a submitted assessment, then a second draft, asserts `version == 2`) and a direct unit test of the new `get_user_or_ip_key` function (not just an HTTP-level test) per RESEARCH.md Pitfall 1's warning
- [ ] `backend/tests/api/test_initiatives.py` (or a new `test_assessment_history.py`) — covers the new `GET /initiatives/{id}/assessments` endpoint: empty list for no submissions, correct ordering, ownership check (404/403), scores match `compute_dimension_scores` output
- [ ] No new frontend test infrastructure required this phase — existing Vitest setup is untouched; new component tests for the rebuilt wizard are explicitly deferred to Phase 17 (TEST-02) per CONTEXT.md's phase boundary

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Radio-scale renders 5 config-driven options mapped to scores 1-5, horizontal layout | QSTN-02 | Visual/interaction — no Vitest component tests exist yet for this subtree (Phase 17's job) | Open the wizard, confirm each question shows 5 circles in a horizontal row with config-driven labels; select each option and confirm the correct 1-5 score is captured |
| Per-answer save fires ~1.5s after selection without Next/Back | SAVE-01 | Timing-dependent browser behavior, not practically unit-testable | Answer a question, wait ~2s without clicking Next/Back, confirm the `AutosaveBadge` transitions `saving → saved` and the answer persists on refresh |
| Failed save shows retry, blocks Next/Submit until resolved | SAVE-02 | Requires simulating a network failure and observing UI state transitions | Block the answer-save network call (devtools), confirm badge shows amber "retrying" then red "Save failed" with a `Retry save` button, confirm Next/Submit stay disabled until retry succeeds |
| beforeunload flush survives tab close | SAVE-04 | Cannot be automated in jsdom/pytest — requires a real browser and an actual unload event (Phase 17/Playwright's job) | Answer a question, close the tab within the debounce window (<1.5s), reopen and log back in, confirm the answer was saved |
| Resume at last-viewed category after tab close/hard refresh | D-08 (SAVE-04-adjacent) | Requires an actual browser navigation/reload cycle | Navigate to category 4 without answering, hard-refresh, confirm the wizard resumes on category 4 (not category 1) with prior answers pre-filled |
| Retake confirmation dialog + blank-draft behavior | HIST-01 | UI flow requiring visual confirmation of dialog copy and state reset | Click "Start new assessment" on a submitted initiative, confirm the dialog appears with the locked copy, confirm accepting starts a fully blank draft (no answers carried forward) |
| History page list + comparison table render across multiple versions | HIST-02 | Visual/interaction, no component tests yet | Submit two assessment versions for one initiative, visit the history page, confirm both versions list correctly and the comparison table shows per-dimension scores side by side |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`test_questionnaire_answers.py` additions, `test_initiatives.py`/`test_assessment_history.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
