# CLAUDE.md

Guidance for Claude Code (and humans) working in this repo.

## Branch model

| Branch | Purpose | Protected | Deploy |
|---|---|---|---|
| `feature/*` | Active dev, cut from `staging` | No | Local only |
| `staging` | Integration, PR-merged only | Yes (PR + CI) | Railway auto-deploys the Integration environment when CI is green |
| `main` | Release-ready | Yes (PR + CI + 2 approvals) | Manual Railway redeploy from the dashboard |

Flow: `feature/*` → PR into `staging` (CI gates) → `staging` → PR into `main` (CI + human approval) → tag `vX.Y.Z` → release workflow.

**Railway wiring is not a GitHub Actions step.** The standard, most reliable way to do
"auto-deploy on green CI" is to let Railway's own GitHub integration watch the `staging`
branch with its "wait for CI to pass" setting enabled — not to have `staging.yml` call out
to Railway's API. `main`'s environment should have auto-deploy left off; deploy it manually
from the Railway dashboard when ready. See "Setup checklist" below — this isn't wired up yet
because no Railway project exists for this repo.

## The 5 GitHub Actions workflows

All live in `.github/workflows/`. Each bullet below maps to one job of the same name unless noted.

### 1. `pr.yml` — every PR into `main` or `staging`
- `backend-lint` — `ruff check` + `ruff format --check`
- `backend-typecheck` — `mypy app --ignore-missing-imports`
- `frontend-lint` / `frontend-typecheck` — `eslint` / `tsc -b --noEmit`
- `security-audit` — `pip-audit` (3 attempts, backend) + `npm audit --audit-level=high` (frontend)
- `test` — `pytest -n auto -m "not perf and not benchmark"` (perf/benchmark excluded to keep PR feedback fast)
- `perf-gate` — `pytest -m perf` (dedicated job, **no** `-n auto` — pytest-benchmark's timing needs a single worker)
- `docs-freshness` — regenerates `docs/api/openapi.json` from the FastAPI app and fails on any `git diff`

### 2. `staging.yml` — push to `staging` (i.e. after a PR merges)
Same jobs as `pr.yml`, except:
- `test` includes the `benchmark`-marked regression suite (`-m "not perf"` instead of excluding it too)
- `docker-build` (needs lint + test green) — builds and pushes `backend`/`frontend` images to `ghcr.io` tagged `:staging`
- `sbom` (needs `docker-build`) — generates CycloneDX + SPDX SBOMs for both images, commits them to `docs/security/` (commit message includes `[skip ci]` to avoid a push-triggered loop)

### 3. `main.yml` — push to `main`
Same quality jobs as `staging.yml` (full lint/type/audit/test/docs/perf), plus:
- `docker-build-and-sbom` — builds both images locally (no registry push — `main` deploys manually), generates SBOMs, uploads them as a workflow artifact with 90-day retention

### 4. `release.yml` — push of tag `v*`
- `quality-gate` — full lint/mypy/tests including the privacy canary (see below), plus frontend lint/typecheck/`npm audit --omit=dev`
- `build-and-publish` — builds the backend image, pushes it under a temporary `:VERSION-prebuild` tag, generates a CycloneDX SBOM from that pushed image, then builds a second image `FROM` it with `/sbom.json` baked in and pushes that as the real `:VERSION` and `:latest` tags; frontend image is pushed normally; assembles an on-prem deployment bundle (`docker-compose.prod.yml`, `.env.example`, `DEPLOYMENT.md`, `nginx/`, `README.md` as `QUICKSTART.md`) into a zip; publishes a GitHub Release with the bundle + SBOM attached

### 5. `security.yml` — manual dispatch, push to `staging`, PRs into `main`
- `pip-audit` / `npm-audit` — same pattern as above
- `zap-scan` — OWASP ZAP authenticated API scan against the Integration (staging) deployment's OpenAPI spec. Skips cleanly (`if: secrets.STAGING_URL != ''`) until secrets exist — see "Setup checklist"

## Local quality gate (pre-PR)

Run from `backend/`:

```bash
uv run ruff check --fix . ; uv run ruff format .
uv run ruff check . && uv run ruff format --check . && uv run mypy app --ignore-missing-imports && uv run pytest tests/ -n auto -m "not perf and not benchmark" -q
```

## Key design choices carried over

- `-n auto` (xdist) instead of `-x` — fail-fast doesn't combine cleanly with parallel workers.
- `perf` and `benchmark` are pytest markers (see `backend/pyproject.toml`), not directory names — `perf` runs in its own single-worker job (pytest-benchmark + xdist don't mix); `benchmark` is excluded on PRs and included from `staging` onward, so PR feedback stays fast while regressions are still caught before shared branches.
- Docs-freshness as a CI gate, not just a convention — regenerate + `git diff --exit-code` is a cheap, reusable pattern (here: `docs/api/openapi.json`, the FastAPI schema).
- SBOM generation happens twice in the release flow: once for local scanning, once baked into the shipped image.
- `--omit=dev` on the frontend audit **only in `release.yml`** — don't fail a release over vulnerabilities in build-only tooling (vite, esbuild, eslint) that never ships. `pr.yml`/`staging.yml`/`main.yml`/`security.yml` audit the full frontend dependency tree, dev included, to keep visibility during regular development.

## Setup checklist (not yet wired up)

These need real infrastructure this environment doesn't have — the workflows are written to
degrade gracefully (skip, not hard-fail) until they're filled in:

- **Railway**: create a project, connect this repo, point the Integration environment's service at the `staging` branch with "wait for CI" enabled. Leave `main`'s environment on manual deploy.
- **`security.yml`'s `zap-scan` job** needs repo secrets: `STAGING_URL`, `STAGING_SCAN_EMAIL`, `STAGING_SCAN_PASSWORD` (a dedicated non-admin account on the Integration deployment — don't reuse a real admin's credentials).
- **GHCR**: no extra secret needed — `staging.yml`/`main.yml`/`release.yml` all use the built-in `GITHUB_TOKEN`, which already has `packages: write` once granted at the job level (already set).

## Notes / things I did differently than the spec, and why

- **No retrieval/RAG system exists in this app** (it's a rules-engine-scored questionnaire tool, not an LLM/embeddings product), so there's no real Recall@10/NDCG@5 metric to gate on. The `benchmark`-marked test (`tests/benchmark/test_scoring_regression.py`) instead locks in the ZEN scoring engine's output distribution over a synthetic answer set as a regression check — deterministic and exact-match, not percentage-threshold, since a rules engine has no "5% tolerance" concept the way a ranking metric does.
- **"Privacy canary" reframed**: there's no prompt/completion content in this app. `tests/test_privacy_canary.py` instead asserts `SECRET_KEY`/`DATABASE_URL`/`ADMIN_PASSWORD` never leak into validation-error responses, 404s, or the OpenAPI schema. It's intentionally DB-independent (validation/404 paths short-circuit before any query runs), so it doesn't need a Postgres service container.
- **"Scan API key" reframed as scan-account login**: this app has JWT user auth, not a separate API-key mechanism. `zap-scan` logs in with a dedicated scan account's email/password to get a bearer token, rather than fabricating an API-key feature that doesn't exist in `app/core/security.py`.
- **No HuggingFace model caching** — this app doesn't use any HF models (ZEN Engine is a rules engine, not ML), so that design choice from the source brief doesn't apply here. Add it back if the tool ever grows an ML/embeddings feature.
- **The codebase had never been linted before this setup.** Turning on `ruff`/`mypy` as hard PR gates against unlinted code would have broken on the very first PR, so I ran the auto-fix pass now: 145 lint issues auto-fixed, ~10 genuine mypy findings fixed by hand (mostly `int | None` narrowing after DB inserts, one real `zip()` missing `strict=True`), a few config exceptions added deliberately (`UP042` ignored — `str`+`Enum` → `StrEnum` touches SQLAlchemy column serialization and shouldn't happen via autofix; FastAPI's `Depends()`/`Query()`/etc. added to `extend-immutable-calls` since ruff's B008 otherwise flags idiomatic FastAPI DI as a bug).
- **`uv.lock` had 49 known vulnerabilities across 13 packages** (starlette, pyjwt, pillow, python-multipart, urllib3, weasyprint, etc.) before this setup — all pre-existing, none introduced by this change. Ran `uv lock --upgrade` within the *existing* pyproject.toml version constraints (no constraint changes) and re-verified the full test suite — now zero known vulnerabilities. Flagging this since it's a real fix bundled into what was nominally a CI-setup task.
- **No test suite existed at all.** Added minimal scaffolding (`tests/test_health.py`, `tests/perf/test_scoring_perf.py`, `tests/benchmark/test_scoring_regression.py`, `tests/test_privacy_canary.py`) so every CI gate is real and green on day one, not fabricated. These are a starting point, not coverage — there's no test yet that touches the database (auth, initiatives, scoring endpoints are all untested). First real addition to this repo should probably be a Postgres-backed test fixture.
- **`main` currently has one collaborator (you).** The 2-approval rule on `main` will block your own merges until you add a second reviewer or use an admin override to merge. Flagging this now so it's not a surprise on the first PR into `main`.
- **Default branch**: set to `staging` on GitHub (see below), since that's where `feature/*` branches are cut from and where PRs should land by default.
