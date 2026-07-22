# Phase 13: New Questionnaire Config Schema & Data Model Migration - Context

**Gathered:** 2026-07-22
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the schema and data foundation that Phases 14-16 build on top of:

1. A new universal 52-question / 6-category questionnaire config (JSON), replacing MAMI's 27-question/4×3/DSI-SP-split config entirely (QSTN-01, QSTN-03, QSTN-04, QSTN-05-placeholder).
2. A new `Assessment` entity + new answer table shaped for a 1-5 score, laying the foundation Phase 15 needs for versioned retakes (HIST-01/02) — without implementing the retake UX itself.
3. An Alembic migration that moves existing v1.0 MAMI initiative/answer data into a read-only archive, preserving it without deleting anything (MIGR-01).
4. Full removal of the evidence/URL-per-question subsystem — tables, endpoints, services, frontend (MIGR-02).

**Out of scope for this phase:** scoring math (Phase 14), wizard UI / autosave (Phase 15), report visualization (Phase 16). This phase only needs those downstream phases to have a stable, correct schema to build against — it does not implement their behavior.

</domain>

<decisions>
## Implementation Decisions

### V1.0 Data Preservation Strategy
- **D-01:** Old MAMI answers (3-way enum: YES/NOT_THERE_YET/NOT_APPLICABLE) are migrated into a new **separate archive table** (`questionnaire_answer_v1_archive` or equivalent), not kept in the same table as new answers. This is a new pattern for this repo — the existing precedent (`f6a4b3c2d1e9_dsi_sp_questionnaire_foundation.py`) used same-table-plus-version-discriminator for a same-shape change (enum remap), but here the answer *shape* itself changes (3-way categorical → 1-5 numeric), which the user judged too different to overload into one table/column.
- **D-02:** `questionnaire_answer` (going forward) becomes purely the new 1-5-score shape. It does not need to carry legacy enum columns.
- **D-03:** `Initiative` gets its own version/schema tag (e.g. `schema_version` or `is_legacy` — exact naming left to planning) so "is this an old MAMI initiative" is a cheap filter without joining to answers. This also sets up cheap filtering once Phase 15 adds multiple `Assessment` rows per `Initiative`.
- **D-04:** MIGR-01's "queryable read-only" requirement is satisfied by **DB-level access only** in this phase — no new admin endpoint or UI to browse old MAMI submissions. If that's ever needed, it's a future ask, not part of Phase 13.
- **D-05 (compliance_report table):** Not explicitly discussed as its own question — the old `compliance_report` table is not named in MIGR-01, but per "never delete" as the operating principle throughout this discussion, it should be left as-is (no drop, no forced migration) unless it directly blocks the new schema. Flag this assumption to the researcher/planner rather than treating it as fully settled.

### Assessment/Versioning Foundation
- **D-06:** Phase 13 introduces the `Assessment` entity now, not deferred to Phase 15. New table: `initiative_id` FK, version/date field, `status` (draft/submitted, mirroring `Initiative`'s existing draft/active/submitted lifecycle). New `questionnaire_answer` rows key off `assessment_id`, not `initiative_id` directly. Rationale (user-confirmed): avoids a second migration/refactor of the answer table when Phase 15 lands — Phase 15 only needs to add "create new Assessment on retake" behavior on top of an already-correct schema.
- **D-07:** An `Assessment` row is created at the **first answer** (draft state), not only at submission. `status=draft` on first answer, flips to `status=submitted` on full completion. This matches `Initiative`'s current lifecycle and gives Phase 15's autosave requirements (SAVE-01–04) a stable row to write against from question 1 — Phase 13 doesn't implement autosave, but must not design a schema that blocks it.
- **Note for Phase 14/15/16 planners:** this Assessment-first schema is a load-bearing decision for those phases — Phase 14's scoring must read per-`Assessment` (not per-`Initiative`), Phase 15's retake/history features are built directly on `Assessment` rows, Phase 16's report data contract is per-`Assessment`.

### New Config Schema Shape & Placeholder Depth
- **D-08:** Placeholder content stubs **all 52 questions across all 6 categories** (not a smaller sample) — full structural skeleton at real size, using generic placeholder text (e.g. "Category 3 – Question 5"). This is deliberately sized to prove the schema scales and to give Phase 15's wizard realistic pagination/volume to build and test against, ahead of real content (QSTN-05) landing later with no schema change required.
- **D-09:** Answer-option labels use a **shared default 5-label set** (mapped 1-5) reused across all placeholder questions, while the schema itself supports per-question custom label overrides (required by QSTN-03 for when real content arrives). Placeholder content does not need distinct per-question labels — that's a content-authoring task for later, not a Phase 13 schema concern.
- **D-10:** The new config lives in a **single JSON file** (e.g. `config/dssc-questionnaire.json`) containing all 6 categories and 52 questions nested inside — not split one-file-per-category. This matches QSTN-04's "no split" framing directly (no reason to partition by participant type or category the way the old dsi/sp files did).

### Evidence & Participant_type Removal Scope
- **D-11:** Evidence data is **dropped outright**, not archived. `evidence_url` table, model, endpoints (`backend/app/api/v1/evidence.py`), and frontend (`frontend/src/lib/evidence.ts`, `EvidenceInput.tsx`) are deleted entirely with no archive step. Rationale: MIGR-01 only names "initiative and answer data" as requiring preservation; evidence was a secondary feature (free-text URLs, no scoring impact) with no compliance-relevant history worth keeping.
- **D-12:** `participant_type` columns on `Initiative` and `User` are **kept, made nullable, and simply stop being populated/enforced** going forward — not dropped from the schema. Old MAMI initiatives/users retain their DSI/SP tag for historical reference; new Initiatives/Users never set it. No column-drop migration needed.

### Claude's Discretion
- Exact naming of the new `schema_version`/`is_legacy`-style column on `Initiative` (D-03).
- Exact naming and shape of the archive table (`questionnaire_answer_v1_archive` vs. alternative naming) (D-01).
- Whether `compliance_report` needs any touch at all, beyond "don't delete it" (D-05) — flagged as an assumption for the researcher to confirm against the actual migration mechanics, not a fully closed decision.
- Exact `Assessment.status` enum values and version/date field naming (D-06/D-07) — "version/date field" and "draft/submitted" were discussed at a conceptual level; concrete column names and types are an implementation detail for planning.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project/Milestone Context
- `.planning/PROJECT.md` — v2.0 milestone goals, full-replacement framing, Key Decisions table
- `.planning/REQUIREMENTS.md` — QSTN-01/03/04/05, MIGR-01/02 full requirement text and Traceability table
- `.planning/ROADMAP.md` §Phase 13 — phase goal and success criteria this CONTEXT.md elaborates on; also see §Phase 14/15/16 for how this phase's schema decisions (Assessment entity, archive table) are consumed downstream
- `.planning/phases/12-test-retrofit-stabilize-existing-flows/12-CONTEXT.md` — prior phase; established Postgres-testcontainer test infra this phase's migration should be tested against

### Codebase State (from this session's scouting — no `.planning/codebase/*.md` maps exist in this repo; referenced in Phase 12's CONTEXT but the directory doesn't exist here, likely lost or never created during the MaMi-Compliance-Checker → DSSC-Maturity-Tool relocation — flagging as a gap for the researcher, not something to re-create speculatively)
- `backend/app/services/mami_config.py` — current config loading (`CONFIG_DIR` via `Path(__file__).parent` chain, `load_questionnaire_configs()` DSI/SP dict pattern) — to be replaced by a single-file loader per D-10
- `backend/app/core/deps.py:47-57` — FastAPI dependency wiring for config (`get_questionnaire_config(s)`) — needs updating for the new single universal config
- `config/dsi-questionnaire-v2.json`, `config/sp-questionnaire-v2.json`, `config/questionnaire-v1.json` — existing config files being replaced; `config/mami-framework.json` and `config/scoring/mami-scoring.json` are Phase 14's concern (scoring), not this phase's, but must not be broken by this phase's model changes
- `backend/app/models/initiative.py:26-40` (`Initiative`, `ParticipantType` enum lines 12-14) — gets `schema_version`/`is_legacy` column (D-03) and nullable `participant_type` (D-12)
- `backend/app/models/questionnaire.py:14-31` (`QuestionnaireAnswer`) — becomes the new 1-5-score-shaped table (D-02); old rows migrate to the new archive table (D-01)
- `backend/app/models/evidence.py`, `backend/app/schemas/evidence.py`, `backend/app/api/v1/evidence.py` — full deletion target (D-11)
- `backend/app/models/user.py:6-15` — `participant_type` field, kept nullable per D-12
- `backend/app/db/base.py` — imports all table models for Alembic autogenerate; needs updating (remove `EvidenceURL` import, add new `Assessment`/archive-table models)
- `backend/alembic/versions/f6a4b3c2d1e9_dsi_sp_questionnaire_foundation.py` — precedent example of a data-preserving migration (add columns + remap values in place); this phase's migration is a *different* pattern (archive-table split, D-01) since the answer shape itself changes, not just its values
- `backend/alembic/versions/h8c6d5e4f3a2_make_contact_fields_nullable.py` — current migration head; this phase's new migration(s) chain from here
- `backend/app/services/scoring_engine.py` — reads `{mami_code, moscow_level, answer_value, critical_override}` per answer; Phase 13 must keep an equivalent lookup path available (or explicitly hand off the interface change) for Phase 14, since `answer_value`'s shape (enum → 1-5) is a hard breaking change regardless of this phase's other decisions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Path(__file__).parent`-chain config resolution pattern (`mami_config.py`) — reuse the same resolution style for the new single-file config loader.
- `Initiative.status` enum (draft/active/submitted) — direct precedent for the new `Assessment.status` field (D-07).
- FastAPI lifespan pattern (config cached on `app.state` at startup, not re-read per request) — apply the same pattern to the new questionnaire config.

### Established Patterns
- Data-preserving migrations in this repo add nullable columns and remap/copy data rather than dropping — but this phase introduces the *first* archive-table-split pattern (D-01), since `f6a4b3c2d1e9` only ever remapped values within the same column shape.
- `questionnaire_version` per-row versioning (already present on `QuestionnaireAnswer`) is the existing precedent this phase's `Initiative`-level and `Assessment`-level versioning (D-03, D-06) extends to a coarser grain.

### Integration Points
- `backend/app/api/v1/questionnaire.py:29` (`get_questionnaire_config_endpoint`) — currently selects DSI vs SP config by `participant_type`; this selection logic is removed entirely per D-10/QSTN-04.
- `backend/app/api/v1/admin.py` (lines 66-91 cascade-delete, 313 `type_filter` query param, plus 3 admin list endpoints) — evidence cascade-delete logic removed (D-11); `participant_type` filter/display logic can stay for historical initiatives but should not apply to new ones (D-12).
- `backend/app/api/v1/reports.py` and `backend/app/services/report_generator.py` — currently join evidence by `mami_code` into HTML reports; this join is removed entirely (D-11). This file is Phase 16's primary rebuild target, but Phase 13 must not leave it broken against the new schema in the interim.

</code_context>

<specifics>
## Specific Ideas

No specific UI/content examples were given — this phase is schema/migration only, no user-facing surface. The user's decisions consistently favored: never deleting compliance-relevant data (initiative/answer), but not over-preserving secondary data (evidence) beyond what's explicitly required; and designing the schema now to avoid a second migration when Phase 15 lands, rather than deferring versioning design.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope (schema + migration). No scope-creep topics came up.

### Reviewed Todos (not folded)
None — no pending todos existed to review (`.planning/todos/pending/` is empty).

</deferred>

---

*Phase: 13-new-questionnaire-config-schema-data-model-migration*
*Context gathered: 2026-07-22*
