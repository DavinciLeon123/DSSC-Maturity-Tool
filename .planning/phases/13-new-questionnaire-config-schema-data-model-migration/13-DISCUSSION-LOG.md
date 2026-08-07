# Phase 13: New Questionnaire Config Schema & Data Model Migration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-22
**Phase:** 13-new-questionnaire-config-schema-data-model-migration
**Areas discussed:** V1.0 data preservation strategy, Assessment/versioning foundation, New config schema shape & placeholder depth, Evidence & participant_type removal scope

---

## V1.0 Data Preservation Strategy

### Q: How should old 3-way-enum MAMI answers and new 1-5 DSSC answers coexist in the DB?

| Option | Description | Selected |
|--------|-------------|----------|
| Same table, version-discriminated | Follow existing f6a4b3c2d1e9 precedent: add nullable columns, keep old enum column, distinguish via questionnaire_version | |
| Separate archive table | Rename/copy old rows into questionnaire_answer_v1_archive; questionnaire_answer becomes purely the new 1-5 shape | ✓ |
| Let Claude decide | | |

**User's choice:** Separate archive table.

### Q: Should Initiative get its own version/schema tag, or is old-vs-new tracked purely at the answer level?

| Option | Description | Selected |
|--------|-------------|----------|
| Tag Initiative too | Cheap filter without joining to answers; sets up for Phase 15 multi-assessment | ✓ |
| Answer-level only | Initiative untouched, only per-answer questionnaire_version distinguishes | |
| Let Claude decide | | |

**User's choice:** Tag Initiative too.

### Q: Is DB-level access enough for MIGR-01's "queryable read-only", or add a minimal admin endpoint?

| Option | Description | Selected |
|--------|-------------|----------|
| DB-level only | No new endpoint in Phase 13 — matches schema+migration scope | ✓ |
| Minimal admin endpoint | Simple read-only list/detail endpoint, admin-only | |
| Let Claude decide | | |

**User's choice:** DB-level only.

---

## Assessment/Versioning Foundation

### Q: Should Phase 13 introduce the 1-initiative-to-many-assessments structure now, or defer to Phase 15?

| Option | Description | Selected |
|--------|-------------|----------|
| Introduce Assessment entity now | New Assessment table now; answers key off assessment_id; avoids a second migration in Phase 15 | ✓ |
| Keep Initiative flat, defer to Phase 15 | Answers stay keyed to initiative_id; Phase 15 does the versioning migration later | |
| Let Claude decide | | |

**User's choice:** Introduce Assessment entity now.

### Q: Does the Assessment row exist during in-progress answering (draft), or only at submission?

| Option | Description | Selected |
|--------|-------------|----------|
| Assessment created at first answer (draft state) | status=draft on first answer, submitted on completion, mirrors Initiative lifecycle | ✓ |
| Assessment created only on submission | Answers held against initiative directly until complete | |
| Let Claude decide | | |

**User's choice:** Assessment created at first answer (draft state).

---

## New Config Schema Shape & Placeholder Depth

### Q: How much placeholder content should Phase 13 stub?

| Option | Description | Selected |
|--------|-------------|----------|
| Stub all 52 questions across 6 categories | Full structural skeleton at real size | ✓ |
| Stub a smaller representative sample | e.g. 2 categories, faster to write/review | |
| Let Claude decide | | |

**User's choice:** Stub all 52 questions across 6 categories.

### Q: Are the 5 answer-option labels custom per-question from day one, or a shared default set?

| Option | Description | Selected |
|--------|-------------|----------|
| Shared default label set, per-question override capable | One default 5-label set reused; schema supports per-question overrides for real content later | ✓ |
| Fully custom per-question labels from day one | Every placeholder question gets distinct labels | |
| Let Claude decide | | |

**User's choice:** Shared default label set, per-question override capable.

### Q: One config file for the whole questionnaire, or one per category?

| Option | Description | Selected |
|--------|-------------|----------|
| Single file (e.g. dssc-questionnaire.json) | All 6 categories/52 questions nested inside one file | ✓ |
| One file per category | 6 separate files, merged at startup | |
| Let Claude decide | | |

**User's choice:** Single file (e.g. dssc-questionnaire.json).

---

## Evidence & Participant_type Removal Scope

### Q: Should evidence_url data be archived read-only or dropped outright?

| Option | Description | Selected |
|--------|-------------|----------|
| Drop outright | Table, model, endpoints, frontend deleted entirely, no archive | ✓ |
| Archive read-only like the rest | Copy rows into an archive table before dropping live table | |
| Let Claude decide | | |

**User's choice:** Drop outright.

### Q: Should participant_type columns be fully dropped, or kept nullable on old rows?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep nullable on old rows, stop using going forward | Historical reference retained; new rows never populate it | ✓ |
| Drop columns entirely | Historical DSI/SP info recoverable only via archived question_id prefixes | |
| Let Claude decide | | |

**User's choice:** Keep nullable on old rows, stop using going forward.

---

## Claude's Discretion

- Exact naming of the new `schema_version`/`is_legacy`-style column on `Initiative`.
- Exact naming/shape of the archive table (`questionnaire_answer_v1_archive` vs. alternatives).
- Whether `compliance_report` needs any touch at all beyond "don't delete it" — not explicitly asked as its own question; inferred from the "never delete" principle running through the rest of the discussion, flagged in CONTEXT.md as an assumption for the researcher to confirm.
- Exact `Assessment.status` enum values and version/date field naming.

## Deferred Ideas

None — discussion stayed within phase scope.
