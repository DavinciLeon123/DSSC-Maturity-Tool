# Relocation Note: Phase 12 was planned and executed in the wrong repository

**Date:** 2026-07-22

Phase 12 (this directory's CONTEXT/RESEARCH/PATTERNS/VALIDATION/PLAN/SUMMARY/
VERIFICATION/UAT files), and the "v2.0 DSSC Maturity Scan for Dataspaces"
milestone it belongs to (`.planning/PROJECT.md`, `.planning/ROADMAP.md`,
`.planning/REQUIREMENTS.md`), were originally discussed, researched, planned,
and executed against a checkout of `MaMi-Compliance-Checker` — the wrong
repository. That milestone was always intended for this fork
(`DSSC-Maturity-Tool`), which existed specifically to host it; the work
landed in the source repo by mistake. It was reverted from
`MaMi-Compliance-Checker` (commit `c8d54fe`, a forward revert — no force-push,
no history rewrite) and relocated here.

## What is unchanged from the original planning

Every technical claim in `12-CONTEXT.md`, `12-RESEARCH.md`, `12-PATTERNS.md`,
`12-VALIDATION.md`, and the five `12-0N-PLAN.md`/`12-0N-SUMMARY.md` pairs is
accurate as written — `DSSC-Maturity-Tool`'s initial commit (`a7e9e9f`) is a
byte-for-byte fork of the exact same `MaMi-Compliance-Checker` codebase state
these documents were written against (verified via empty `git diff`), so the
research, pitfalls, patterns, and executed test code all apply unchanged.

## What changed in the relocation (this repo's context these docs don't have)

Unlike `MaMi-Compliance-Checker` at the time Phase 12 was planned there, this
repo (`DSSC-Maturity-Tool`) had **already independently added**, since its
2026-07-20 fork and before this milestone existed here:

- A 5-workflow CI/CD pipeline (`pr.yml`, `staging.yml`, `main.yml`,
  `release.yml`, `security.yml`) with branch protection on `staging`/`main`.
- A starter backend test suite: `tests/test_health.py`,
  `tests/test_privacy_canary.py`, `tests/benchmark/test_scoring_regression.py`,
  `tests/perf/test_scoring_perf.py`.
- `tests/conftest.py` with `mami_codes`/`make_answers` fixtures (no DB).
- Backend dev-dependency group: ruff, mypy, pytest, pytest-xdist,
  pytest-benchmark, pip-audit, httpx (no testcontainers/faker/pytest-asyncio/
  pytest-mock/pytest-cov, no frontend test tooling at all).

So the plans' premise — "this codebase has never had test infrastructure...
zero test coverage today" (12-01-PLAN.md, 12-VALIDATION.md, 12-PATTERNS.md) —
was true for `MaMi-Compliance-Checker` when written, but is **not** true for
this repo. Read those "zero coverage" statements as historical context for why
Phase 12 was scoped the way it was, not as a claim about this repo's state.

**How the actual integration (this feature branch,
`feature/test-retrofit-auth-admin-reports`) differs from what the plans
describe doing "from scratch":**

| Plan said (create from scratch) | Actually done here (merge, additive) |
|---|---|
| Create `backend/tests/conftest.py` | Merged Postgres/testcontainer/client/admin_client fixtures into the existing `conftest.py` alongside its `mami_codes`/`make_answers` fixtures — no fixture name collisions |
| Add `[dependency-groups].dev` in `pyproject.toml` | Added `pytest-asyncio`, `pytest-cov`, `pytest-mock`, `faker`, `testcontainers[postgres]` to the existing group; bumped `pytest`/`httpx` version floors to the audited versions |
| Add `[tool.pytest.ini_options]` | Added `asyncio_mode = "auto"` alongside the existing `testpaths`/`markers` (perf/benchmark) |
| Create `backend/tests/test_smoke.py` | **Skipped as redundant** — this repo's existing `tests/test_health.py` already proves the lifespan-aware `TestClient` chain works (container→schema→lifespan→HTTP is N/A here since no container was needed for that proof); enhanced it with the one additional assertion `test_smoke.py` had (`app.state.mami_config`/`zen_engine` populated) instead of duplicating the file |
| Create `.github/workflows/test.yml` | **Not created** — instead added a `frontend-test` job to the existing `pr.yml`/`staging.yml`/`main.yml`/`release.yml` (this repo had no frontend test job at all), and let the existing `test`/`quality-gate` jobs pick up the new `backend/tests/api/*`/`services/*` files automatically (no exclusion marker on them, same as the pre-existing test files) |
| — (not anticipated in the original plans) | Added a "Install WeasyPrint system dependencies" step to all 4 CI workflows that run pytest — discovered locally (see `12-UAT.md` Gap `G-12-1`) that `weasyprint` (a pre-existing runtime dependency, not new) fails to import without native Pango/GLib libraries, which neither this repo's nor the original repo's CI installed |

## Open item carried over from `12-UAT.md`

`G-12-1`: the Postgres-backed test suite was verified genuinely green
locally in *this* repo (Docker is available here) as part of landing this PR —
see the PR description / CI run for the actual result, superseding the
"could not verify, no Docker" finding recorded against the original
`MaMi-Compliance-Checker` session.
