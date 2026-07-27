---
phase: 16
slug: report-data-contract-dual-visualization-admin-aggregation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-26
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-xdist (backend); Vitest 4.1.10 + Testing Library (frontend) |
| **Config file** | `backend/pyproject.toml`; `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` |
| **Full suite command** | `cd backend && uv run pytest tests/ -n auto -m "not perf" -q` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/api/test_reports.py tests/api/test_admin.py -q`
- **After every plan wave:** Run the full quick-run command above
- **Before `/gsd-verify-work`:** Full suite must be green, plus a manual check of an actual downloaded PDF (SVG-in-WeasyPrint rendering cannot be automated away locally)
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 16-01-0N | 01 | 0 | RPRT-01 | — | Report response includes a `radar_chart_svg` string containing 6 axis labels | unit/integration | `pytest tests/api/test_reports.py -k radar -x` | ❌ W0 | ⬜ pending |
| 16-01-0N | 01 | 0 | RPRT-02 | — | `priority_list` always has exactly 6 entries, sorted ascending by score, each with `band_label`/`band_color` | unit | `pytest tests/services/test_report_generator.py -k priority_list -x` | ❌ W0 | ⬜ pending |
| 16-01-0N | 01 | 0 | RPRT-03 | — | `get_maturity_band` returns identical band for the same score regardless of caller (SVG generator vs. priority list) | unit | `pytest tests/services/test_report_generator.py -k maturity_band -x` | ❌ W0 | ⬜ pending |
| 16-01-0N | 01 | 0 | RPRT-04 | — | The same `radar_chart_svg`/`priority_list` values appear in both `/report/data`'s JSON and the rendered `report.html` context | integration | `pytest tests/api/test_reports.py -k contract_parity -x` | ❌ W0 | ⬜ pending |
| 16-0N-0N | 0N | N | ADMN-01 | V4 | `/admin/heatmap` excludes initiatives with zero submitted assessments from the average but includes them (as "no data yet") in the per-initiative list; per-initiative report links re-check ownership/admin bypass server-side | integration | `pytest tests/api/test_admin.py -k heatmap_aggregation -x` | ❌ W0 | ⬜ pending |
| 16-0N-0N | 0N | N | RPRT-04 / V4 | V4 | Resolving a report by `assessment_id` re-derives ownership (join `Assessment.initiative_id → Initiative.user_id`), 404 on mismatch, not 403 | integration | `pytest tests/api/test_reports.py -k ownership -x` | ❌ W0 | ⬜ pending |
| 16-0N-0N | 0N | N | (regression) | — | Report/score endpoints resolve the assessment correctly once `Initiative`/`Assessment` transitions from draft to **submitted** — the pre-existing draft-only completion-gate lookup bug (found during research) must not silently persist into this phase's rebuild | integration | `pytest tests/api/test_reports.py -k submitted -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/api/test_reports.py` — new cases exercising a report endpoint against a **submitted** (not draft) assessment; existing fixtures only use draft assessments and would mask the draft-scoped completion-gate bug found during research
- [ ] `backend/tests/services/test_report_generator.py` — new cases for `generate_radar_svg`/`build_priority_list`/`get_maturity_band` (currently only covers the old minimal post-Phase-14 stub)
- [ ] `backend/tests/api/test_admin.py` — rewrite of the heatmap tests for the new aggregation shape (currently only asserts the fixed `{degraded: true, cells: []}` stub)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Radar chart SVG renders correctly inside the mailed PDF (WeasyPrint) | RPRT-04 | WeasyPrint's native libraries aren't installed in this local dev environment (pre-existing, unrelated gap logged since Phase 13); SVG text-rendering fidelity inside a PDF can't be asserted by a unit test | Trigger `/report/mail` (or download `/report/pdf`) against a submitted assessment in CI/Docker or the deployed environment; visually confirm the radar chart and priority list render with correct colors/labels and are not clipped |
| Radar chart SVG scales correctly across the responsive in-app card and the fixed-width PDF page | RPRT-04 | Visual layout correctness across two different container contexts is not a good fit for an assertion-based test | Open the in-app report at a few viewport widths and compare against the PDF rendering |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
