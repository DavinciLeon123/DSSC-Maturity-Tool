---
phase: 13
slug: new-questionnaire-config-schema-data-model-migration
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-07-23
---

# Phase 13 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| client → GET /questionnaire/config | Authenticated read of public-to-the-user questionnaire content | Questionnaire structure only (no PII, no secrets) |
| client → former /evidence routes | Previously accepted user-supplied URLs (SSRF surface); this phase removes the surface entirely | None — route deleted |
| client → PUT/GET answer-upsert (initiative-scoped, assessment-first) | Authenticated write/read of an answer via a lazily-created draft Assessment; `initiative_id` could be guessed to target another user's data | Answer score (1-5), question/category IDs |
| client → AnswerCreate.score | Untrusted integer crossing into the DB | Integer score |
| deploy → alembic upgrade head (container startup) | The migration transforms production data; a bug could silently lose or corrupt preserved v1 answers | All pre-migration `questionnaire_answer` rows |
| new `questionnaire_answer.score` (DB layer) | Last line of defense for out-of-range scores if a future write path bypasses Pydantic | Integer score |
| `questionnaire_answer_v1_archive` / admin cascade-delete | Admin hard-delete of a legacy initiative must not silently destroy preserved compliance history | Archived v1 answer rows |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-13-01 | Elevation of Privilege | assessment-keyed answer endpoints (`app/api/v1/questionnaire.py`) | high | mitigate | Ownership re-derived through `Initiative.user_id` on every request (`initiative.user_id != current_user.id` check at lines 112–115, 193–196) before any Assessment lookup/write — assessment identity is never accepted directly from the client, it's looked up via the owned initiative. Same pattern as existing initiative-scoped routes. | closed |
| T-13-02 / T-13-02b | Tampering | `AnswerCreate.score` / `questionnaire_answer.score` column | medium | mitigate | Pydantic `Field(ge=1, le=5)` in `app/schemas/questionnaire.py:9` (schema layer) + DB-level `CHECK (score BETWEEN 1 AND 5)` (`ck_answer_score_range`) added in the `i9d7e6f5a4b3` migration (defense-in-depth). Verified by `test_upgrade_preserves_seeded_v1_answers_and_tags_legacy_initiatives`, which asserts the CHECK rejects an out-of-range insert. | closed |
| T-13-03 | Tampering / Denial of data integrity | the archive-split migration (`i9d7e6f5a4b3`) | high | mitigate | BLOCKING migration-verification tests (`tests/migrations/test_v1_archive_migration.py`) prove every pre-migration row is copied verbatim (count + content + `initiative_id` linkage) against a seeded real-Postgres testcontainer, plus an upgrade→downgrade→upgrade round-trip. All 23 tests pass. | closed |
| T-13-04 | Information Disclosure | `GET /questionnaire/config` | low | accept | Config contains only questionnaire structure (no PII, no secrets); endpoint remains behind `get_current_user` as today. No additional control needed. | closed |
| T-13-05 | Tampering | `config/dssc-questionnaire.json` (filesystem) | low | accept | Config is read-only at runtime, loaded once at lifespan startup; edits require filesystem/deploy access already governed by the CI/branch model (CLAUDE.md). | closed |
| T-13-06 | Information Disclosure / SSRF | former evidence URL-input endpoints | high | mitigate | Removed entirely — model, router, schema, and frontend deleted (only stale bytecode + the historical creation migration remain, as expected). Verified by `test_evidence_removed.py`: routes return 404 (not 405/500), no leftover class references via source-scan, and an AST walk confirms no class definition remains. | closed |
| T-13-07 | Tampering | admin cascade-delete path | low | accept | Removing the evidence cascade-delete line cannot orphan evidence rows because the table itself is dropped; interim (pre-drop) rows become unreferenced but harmless read-only data until the table drop. | closed |
| T-13-08 / T-13-08b | Tampering | `questionnaire_answer_v1_archive` integrity / durability under admin delete | high | mitigate | Archive table carries no FK to `initiative.id` (confirmed in `i9d7e6f5a4b3` — no `ForeignKeyConstraint` referencing `initiative` on the archive table), so admin hard-delete of a legacy initiative cannot cascade-remove preserved history. Archive `answer_value` column is an explicit `sa.String()` (never a native Postgres ENUM), so test and prod schemas do not diverge. | closed |
| T-13-SC | Tampering | package installs (all 4 sub-plans) | n/a | accept | Zero new packages across the phase (RESEARCH Package Legitimacy Audit). No install task in any of the 4 plans. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-13-01 | T-13-04 | Questionnaire config is non-sensitive structural data; existing auth is sufficient. | gsd-secure-phase (retroactive) | 2026-07-23 |
| R-13-02 | T-13-05 | Config file is read-only at runtime; write access already governed by CI/branch protections. | gsd-secure-phase (retroactive) | 2026-07-23 |
| R-13-03 | T-13-07 | Cascade-delete concern moot once the evidence table itself is dropped in this phase. | gsd-secure-phase (retroactive) | 2026-07-23 |
| R-13-04 | T-13-SC | No new dependencies introduced by any of the 4 sub-plans. | gsd-secure-phase (retroactive) | 2026-07-23 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-23 | 11 | 11 | 0 | gsd-secure-phase (L1 grep-depth; register authored at plan time in all 4 sub-plans, asvs_level=1 short-circuit — auditor subagent not spawned) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-23
