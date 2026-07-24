# Backend Test Suite

## Structure

- `test_health.py` — health-check + lifespan-population smoke test (no DB).
- `test_privacy_canary.py` — asserts secrets never leak into error responses (no DB).
- `benchmark/`, `perf/` — scoring-engine regression/latency suites (no DB; see
  CLAUDE.md for how these gate CI). The ZEN-engine-based tests that lived here
  were removed in Phase 14 Plan 04 (SCOR-03); Phase 17 (TEST-01) owns writing
  equal-weight-scoring replacements — see `.planning/phases/14-scoring-engine-replacement/deferred-items.md`.
- `conftest.py` — one fixture family: `postgres_container`/`engine`/`session`/
  `client`/`admin_client`/`user_client` (real Postgres via testcontainers,
  added for the tests below). (`mami_codes`/`make_answers` removed in Phase 14
  Plan 04 alongside the ZEN engine they fed.)
- `factories.py` — plain fixture-factory functions (not `factory_boy`) producing
  schema-realistic synthetic data via `faker` — `User`, `Initiative`,
  `QuestionnaireAnswer`, `ComplianceReport`. (`EvidenceURL`/`make_evidence`
  removed in Phase 13 Plan 02 per MIGR-02 — the evidence subsystem no longer
  exists.)
- `api/` — one file per `app/api/v1/*.py` router under characterization test
  (`test_auth.py`, `test_admin.py`, `test_reports.py`).
- `services/` — pure-function/transform-level tests (`test_report_generator.py`)
  that don't need HTTP/`TestClient`.

## Prerequisite: a local Docker-API-compatible daemon (for `api/` and `factories.py`-based tests only)

`api/test_auth.py`, `api/test_admin.py`, and `api/test_reports.py` run against a
**real Postgres instance**, not SQLite — spun up automatically per test session
via [`testcontainers-python`](https://testcontainers-python.readthedocs.io/)'s
`PostgresContainer`. This is deliberate: `app/api/v1/admin.py` uses raw SQL
against Postgres-native features (native `ENUM` type on
`questionnaire_answer.answer_value`, `pg_insert().on_conflict_do_update()`
upserts) that SQLite cannot faithfully reproduce.

`test_health.py`, `test_privacy_canary.py`, `benchmark/`, and `perf/` do **not**
need Docker — only the Postgres-backed `api/` suite does.

Install **one** of the following before running the full suite locally:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS/Windows/Linux)
- [Colima](https://github.com/abiquo/colima) (macOS, lightweight CLI-only alternative)
- [Podman](https://podman.io/) (Docker-API compatible via `podman machine` + the
  `DOCKER_HOST` env var pointed at Podman's socket)

Confirm the daemon is running:

```bash
docker info
```

If this command fails or times out, the `api/` tests fail immediately with:

```
docker.errors.DockerException: ... / testcontainers.exceptions.ContainerConnectException: Could not find a valid Docker environment.
```

That means the daemon is not installed/running — not a bug in the test suite
or application code. **CI runners already provide Docker** (GitHub Actions
`ubuntu-latest` ships it preinstalled) — this setup step is for local
development only.

`weasyprint` (used by `api/test_reports.py`'s PDF-generation path) also needs
native Pango/GLib system libraries on top of the Python package — see
[WeasyPrint's install docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation)
if you hit `OSError: cannot load library 'libgobject-2.0-0'` locally. On
Ubuntu/Debian (including CI): `apt-get install libpango-1.0-0 libpangoft2-1.0-0
libgdk-pixbuf-2.0-0 libcairo2`. On macOS: `brew install pango`.

## Running the suite

```bash
cd backend
uv run pytest tests/ -n auto -m "not perf and not benchmark" -q  # PR-gate subset (matches CI)
uv run pytest                                                     # full suite, including perf/benchmark
uv run pytest --cov=app --cov-report=term-missing                 # with coverage
```
