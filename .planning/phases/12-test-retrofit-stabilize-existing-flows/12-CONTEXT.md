# Phase 12: Test Retrofit — Stabilize Existing Flows - Context

**Gathered:** 2026-07-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Add automated regression test coverage for the subsystems this v2.0 milestone does NOT rebuild — auth (registration, login, lockout, password reset), admin management (user/initiative CRUD, cascade-delete, CSV export), and PDF/email report delivery — so that Phases 13-18's rebuild of the questionnaire/scoring/report subsystems can't silently break these existing flows. This phase has no v1 requirement of its own; it exists purely as a safety net protecting delivery of the rest of the milestone.

No new user-facing capability is added here. No questionnaire, scoring, or wizard code is touched.

</domain>

<decisions>
## Implementation Decisions

### Test Database Strategy
- **D-01:** Backend tests run against a real Postgres instance (test container/docker), not SQLite in-memory. Rationale: `admin.py` uses raw SQL and Postgres-native features (native ENUM type, `pg_insert().on_conflict_do_update()` upsert) that SQLite cannot faithfully reproduce — and Phase 13 changes the exact `answer_value` ENUM column this suite needs to catch regressions in. TESTING.md's original SQLite suggestion is superseded by this decision for this project.

### CI Integration
- **D-02:** This phase stands up CI (GitHub Actions) from scratch — no `.github/` directory exists today. The regression suite must run automatically on every PR/push, not just locally, since the whole point of the safety net is to block bad merges automatically as Phases 13-18 land. Scope: a workflow that spins up Postgres (service container or equivalent), runs backend pytest and frontend Vitest, and fails the check on any regression.

### Test Data Strategy
- **D-03:** Use synthetic, factory-built fixtures modeled on the production schema shape (multiple initiatives/answers/evidence rows per user) rather than a sanitized export of real production data. No PII exposure risk, no scrubbing pipeline needed, faster to set up. "Production-shaped" (per ROADMAP.md success criteria) means schema-realistic fixture data, not an actual data export.

### Bugs Discovered While Writing Tests
- **D-04:** Characterize-only scope. If writing these auth/admin/PDF regression tests surfaces existing bugs unrelated to the wizard/save issues already scoped for Phase 15, pin the current (even if imperfect) behavior as the test baseline and log the bug as a backlog item — do not fix it inline in this phase. Keeps Phase 12 tightly scoped to "add a safety net," not an implicit bug-fixing pass. Exception: nothing in this phase should ever intentionally test-lock a bug as "correct forever" — log discovered bugs clearly so a future phase can decide to fix them.

### Claude's Discretion
- Exact GitHub Actions workflow structure (single job vs. matrix, Postgres service container config, caching strategy for pip/npm) is left to planning/execution — no specific CI YAML shape was discussed.
- Specific fixture factory design (e.g., `pytest` fixtures vs. `factory_boy`) is left to planning.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Codebase State (what exists today, to be characterized not changed)
- `.planning/codebase/TESTING.md` — current zero-coverage state, suggested frameworks/patterns (pytest, Vitest); this phase's Postgres-over-SQLite decision (D-01) supersedes its SQLite suggestion
- `.planning/codebase/CONCERNS.md` — specific fragile areas to prioritize: bare exception handling in `reports.py` (line ~64), manual cascade-delete in `admin.py` (lines 66-91), password reset token exposure in `auth.py` (line ~109), report generation performance (`reports.py` lines 68-173)
- `.planning/codebase/CONVENTIONS.md` — naming, error-handling, and module-organization conventions to follow in new test files

### Stack Decisions (from milestone research)
- `.planning/research/STACK.md` — confirms pytest + pytest-asyncio + pytest-cov + pytest-mock (backend) and Vitest + `@testing-library/react` + jsdom (frontend) as the chosen unit-test stack; Playwright is out of scope for this phase (Phase 17)
- `.planning/research/PITFALLS.md` — pitfall #6 (test retrofit sequencing): "regression tests for auth/admin/PDF *first* (stable code, safety net), new tests for scoring/config *after* the swap" — this phase IS that first step

### Project/Milestone Context
- `.planning/PROJECT.md` — v2.0 milestone goals and full replacement framing
- `.planning/REQUIREMENTS.md` — this phase maps to no specific REQ-ID (foundational, see Traceability note)
- `.planning/ROADMAP.md` §Phase 12 — phase goal and success criteria this CONTEXT.md elaborates on

No prior-phase CONTEXT.md files apply — this is the first phase of a new milestone (v1.0's archived phase context, under `.planning/milestones/v2.0-phases/`, is MAMI-specific and superseded by the full-replacement decision).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None yet — no test infrastructure exists in the repo (no `frontend/vitest.config.ts`, no `backend/tests/`, no pytest config in `pyproject.toml`). This phase creates that infrastructure from scratch.

### Established Patterns
- Backend error handling: `HTTPException` with explicit `status_code` is the norm everywhere except `reports.py`'s bare `except Exception` — tests should assert current (even if imperfect) status codes/behavior per D-04.
- Backend structure: `app/services/` (business logic), `app/api/v1/` (route handlers), `app/models/` (SQLModel), `app/schemas/` (Pydantic) — new `backend/tests/` should mirror this with `tests/services/`, `tests/api/`, etc., per TESTING.md's suggested layout.
- Frontend: components co-locate tests as `[FileName].test.tsx` per TESTING.md's suggested convention — apply this for any frontend test added in this phase.

### Integration Points
- `backend/app/api/v1/admin.py` lines 66-91 (`_delete_initiative_children`, cascade-delete) — primary target for admin regression tests per ROADMAP.md success criterion #2.
- `backend/app/api/v1/reports.py` lines 29-65 (`_send_report_email`) and `backend/app/services/report_generator.py` — primary target for PDF/email regression test per success criterion #3.
- `backend/app/api/v1/auth.py` — registration, login, lockout, password reset — primary target for auth regression tests per success criterion #1.

</code_context>

<specifics>
## Specific Ideas

No specific idea/example was given beyond the discussed decisions — the user is comfortable with standard characterization-test approaches for this phase, per the "Recommended" options chosen in every discussion round.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Fixing bugs discovered during this phase's test-writing is explicitly deferred per D-04, not lost — log each as a backlog item when found.)

### Reviewed Todos (not folded)
None — no pending todos existed to review (`.planning/todos/pending/` is empty).

</deferred>

---

*Phase: 12-test-retrofit-stabilize-existing-flows*
*Context gathered: 2026-07-22*
