---
phase: 02-questionnaire-and-scoring
verified: 2026-02-17T00:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: null
gaps: []
human_verification:
  - test: Fill in answers, close browser tab, reopen questionnaire page
    expected: All previously entered answers appear pre-filled on reload
    why_human: Session persistence requires live PostgreSQL, auto-save mutations, and browser reload
  - test: Select COMPLY_EXPLAIN, leave rationale blank, wait for auto-save
    expected: Backend returns 422; questionnaire.tsx has no onError handler so may fail silently
    why_human: Error handling for failed mutations needs human observation
  - test: Click Get Compliance Score with some NO answers
    expected: FindingsPanel appears with CRITICAL/NON_CRITICAL counts and per-finding MAMI codes
    why_human: Requires live ZEN Engine evaluation and React rendering
  - test: Answer q_S-HRA-1.3 (critical_override=false MUST) with NO and score
    expected: Finding is NON_CRITICAL not CRITICAL demonstrating override end-to-end
    why_human: Requires complete DB + ZEN Engine + frontend stack running
---

# Phase 2: Questionnaire and Scoring Verification Report

**Phase Goal:** Users can fill in the MAMI questionnaire, save and resume answers, and have their responses scored against MoSCoW compliance rules
**Verified:** 2026-02-17
**Status:** passed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can view the full MAMI questionnaire organized by category and dimension, fill in answers, and return later to find their answers preserved | VERIFIED | questionnaire.tsx loads config via useQuery, renders 4 category tabs, QuestionnaireForm per dimension; savedAnswers loaded on mount into formData; auto-save via useMutation on every answer change; GET /questionnaire/initiatives/{id}/answers returns saved rows for resume |
| 2 | User can mark a question NOT_APPLICABLE or answer with comply or explain and provide free-text rationale | VERIFIED | NotApplicableWidget.tsx renders YES/NO/COMPLY_EXPLAIN/NOT_APPLICABLE; ComplyExplainWidget.tsx renders YES/NO/COMPLY_EXPLAIN; both show textarea when COMPLY_EXPLAIN selected; model_validator in AnswerCreate rejects COMPLY_EXPLAIN without rationale |
| 3 | Questionnaire structure is defined in a JSON config file and changes to questions require no code deploys | VERIFIED | config/questionnaire-v1.json contains all 20 questions grouped by category/dimension; loaded at startup into app.state.questionnaire_config; served via GET /questionnaire/config; no question data hardcoded in Python |
| 4 | Each saved answer row records the questionnaire version it was answered against | VERIFIED | QuestionnaireAnswer model has questionnaire_version: str field; AnswerCreate requires questionnaire_version; questionnaire.tsx passes config.version in every saveAnswer() call; migration creates questionnaire_version column as NOT NULL |
| 5 | Scoring produces a list of CRITICAL and NON_CRITICAL findings; MUST-level questions default to CRITICAL unless overridden in config | VERIFIED | mami-scoring.json JDM has hitPolicy first with 8 rules: critical_override=false fires before MoSCoW rules; MUST+NO/COMPLY_EXPLAIN produce CRITICAL; SHOULD+NO/COMPLY_EXPLAIN produce NON_CRITICAL; score_all_answers() evaluates per-answer via async_evaluate; ScoreResponse has critical_count and non_critical_count |

**Score:** 5/5 truths verified

---

### Required Artifacts

#### Phase 02-01: Config Foundation

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| config/mami-framework.json | MAMI code catalog with MoSCoW levels and critical_override flags | VERIFIED | 20 codes across 4 categories x 3 dimensions; all codes have id, category, dimension, moscow_level, critical_override; 3 codes have critical_override: false (S-HRA-1.3, PP-MRA-2.1, D-TA-3.1); SHOULD codes present per category |
| config/questionnaire-v1.json | Versioned questionnaire structure | VERIFIED | version: 1.0; 4 categories; 20 questions; 3 have answer_type: not_applicable_allowed |
| config/scoring/mami-scoring.json | JDM decision file for ZEN Engine | VERIFIED | 3 nodes; hitPolicy: first; 8 rules in correct priority order; single-answer input format (answer.moscow_level, answer.answer_value, answer.critical_override) |
| backend/app/services/mami_config.py | Config loader with load_mami_config(), load_questionnaire_config() | VERIFIED | 24 lines; Path(__file__) chain resolution; 3 functions |
| backend/app/main.py | FastAPI app with lifespan startup loading all three configs + ZEN engine | VERIFIED | asynccontextmanager lifespan loads all 3 singletons into app.state; lifespan= passed to FastAPI; 4 routers registered |
| backend/app/core/deps.py | get_mami_config, get_questionnaire_config, get_zen_engine | VERIFIED | All 3 deps return from request.app.state; existing auth deps preserved |

#### Phase 02-02: Answer Storage and Frontend

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| backend/app/models/questionnaire.py | QuestionnaireAnswer SQLModel with UniqueConstraint | VERIFIED | UniqueConstraint(initiative_id, question_id, name=uq_answer_per_question); questionnaire_version field; AnswerValue enum has all 4 values |
| backend/app/schemas/questionnaire.py | AnswerCreate with model_validator, AnswerRead | VERIFIED | model_validator(mode=after) raises ValueError for COMPLY_EXPLAIN without rationale; AnswerRead has from_attributes=True |
| backend/app/api/v1/questionnaire.py | GET /questionnaire/config, PUT /answers/{qid}, GET /answers | VERIFIED | 3 endpoints; pg_insert with on_conflict_do_update targeting uq_answer_per_question; ownership check (403); GET /answers for resume |
| backend/alembic/versions/b3f7c9a1d2e8_add_questionnaire_answers_table.py | Migration creating questionnaire_answer table | VERIFIED | create_table with 9 columns; UniqueConstraint; 3 indexes; down_revision: c3f2a891e5b7 (correct chain) |
| frontend/src/routes/_app/questionnaire.tsx | Questionnaire page with category tabs and auto-save | VERIFIED | 183 lines; useQuery for config and savedAnswers; useMutation for auto-save; 4 tabs; QuestionnaireForm per dimension; handleGetScore + FindingsPanel |
| frontend/src/components/questionnaire/QuestionnaireForm.tsx | RJSF form wrapper with custom widgets | VERIFIED | AJV8 validator passed; customWidgets registered; buildSchema/buildUiSchema map answer_type to correct widget |
| frontend/src/components/questionnaire/NotApplicableWidget.tsx | Custom RJSF widget for NOT_APPLICABLE toggle | VERIFIED | Renders all 4 options; composite {value, rationale} for COMPLY_EXPLAIN; rationale textarea visible when COMPLY_EXPLAIN selected |
| frontend/src/components/questionnaire/ComplyExplainWidget.tsx | Custom RJSF widget for comply-or-explain with rationale | VERIFIED | Renders YES/NO/COMPLY_EXPLAIN; same composite object pattern; rationale textarea |

#### Phase 02-03: Scoring Engine

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| backend/app/services/scoring_engine.py | score_all_answers() using per-answer ZEN evaluation | VERIFIED | engine.async_evaluate called per answer; asyncio.gather for concurrency; only FINDING-status results returned |
| backend/app/api/v1/scoring.py | POST /initiatives/{id}/score returning FindingRead list | VERIFIED | score_all_answers called with engine + assembled answers; code_lookup from mami_config; ownership check; ScoreResponse with critical_count, non_critical_count |
| frontend/src/lib/scoring.ts | triggerScoring() API call function | VERIFIED | api.post to /initiatives/initiativeId/score; named import consistent with api.ts |
| frontend/src/components/questionnaire/FindingsPanel.tsx | Findings display with CRITICAL/NON_CRITICAL counts | VERIFIED | 66 lines; filters critical/non-critical separately; per-finding MAMI code + severity; fully-compliant message when no findings |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| backend/app/main.py | config/mami-framework.json | lifespan calls load_mami_config() | WIRED | mami_config.py resolves path via Path(__file__) chain; called in lifespan function |
| backend/app/core/deps.py | backend/app/main.py | request.app.state.mami_config | WIRED | All 3 deps read from request.app.state; app.state populated by lifespan |
| backend/app/main.py | zen.ZenEngine | zen_engine instantiated in lifespan | WIRED | zen.ZenEngine with file-system loader stored in app.state.zen_engine |
| frontend/src/routes/_app/questionnaire.tsx | backend/app/api/v1/questionnaire.py | PUT /api/v1/questionnaire/initiatives/{id}/answers/{qid} | WIRED | saveAnswer() URL matches router path; questionnaire_version and mami_code passed correctly |
| frontend/src/routes/_app/questionnaire.tsx | backend/app/api/v1/questionnaire.py | GET /api/v1/questionnaire/config | WIRED | fetchQuestionnaireConfig() URL matches router path; called in useQuery on mount |
| backend/app/api/v1/questionnaire.py | backend/app/models/questionnaire.py | pg_insert upsert on QuestionnaireAnswer | WIRED | pg_insert(QuestionnaireAnswer).on_conflict_do_update targeting uq_answer_per_question |
| backend/app/api/v1/scoring.py | backend/app/services/scoring_engine.py | await score_all_answers(engine, answers) | WIRED | score_all_answers imported and awaited with engine singleton from get_zen_engine dep |
| backend/app/services/scoring_engine.py | config/scoring/mami-scoring.json | engine.async_evaluate(mami-scoring.json, ...) | WIRED | Literal key used; ZEN loader resolves via scoring_dir / key |
| frontend/src/routes/_app/questionnaire.tsx | frontend/src/lib/scoring.ts | triggerScoring(initiativeId) on button click | WIRED | handleGetScore() calls triggerScoring; button onClick={handleGetScore} |

---

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| QUES-01: Display MAMI questionnaire organized by category/dimension | SATISFIED | None |
| QUES-02: Save and resume answers across sessions | SATISFIED | None |
| QUES-03: YES/NO/COMPLY_EXPLAIN answer types | SATISFIED | None |
| QUES-04: NOT_APPLICABLE option on applicable questions | SATISFIED | None |
| QUES-05: Free-text rationale for COMPLY_EXPLAIN | SATISFIED | None |
| QUES-06: Config-driven questionnaire structure | SATISFIED | None |
| QUES-07: Each answer records questionnaire version | SATISFIED | None |
| SCOR-01: MoSCoW scoring producing CRITICAL/NON_CRITICAL findings | SATISFIED | None |
| SCOR-02: Per-recommendation CRITICAL override in config | SATISFIED | None |
| SCOR-03: CRITICAL/NON_CRITICAL finding output | SATISFIED | None |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| backend/app/schemas/questionnaire.py | 28-29 | answered_at and updated_at typed as str but model fields are datetime | Info | Pydantic v2 from_attributes=True serializes datetime to ISO string; no runtime bug but type annotation is misleading |
| frontend/src/routes/_app/questionnaire.tsx | 62-84 | useMutation has no onError handler | Warning | If backend rejects COMPLY_EXPLAIN without rationale (422), save fails silently from user perspective; data integrity is preserved but UX is degraded |

No TODO/FIXME/PLACEHOLDER comments found. No empty return null implementations. No stub handlers.

---

### Human Verification Required

#### 1. Answer Persistence Across Sessions

**Test:** Fill in 3-4 answers on the questionnaire page, close the browser tab completely, reopen and navigate to /questionnaire
**Expected:** All previously entered answers appear pre-filled
**Why human:** Session persistence requires live PostgreSQL, successful auto-save mutations, and browser reload

#### 2. COMPLY_EXPLAIN Silent Failure UX

**Test:** Select Comply or Explain on a question, leave the rationale textarea blank, wait 1-2 seconds for auto-save
**Expected:** Some user-visible indication that the save failed (error message or toast)
**Why human:** The useMutation in questionnaire.tsx has no onError handler - the 422 from the backend causes a silent failure. Needs human observation to confirm impact.

#### 3. Scoring End-to-End

**Test:** Answer several questions with NO for MUST-level codes and some with YES, click Get Compliance Score
**Expected:** FindingsPanel appears with correct CRITICAL count and per-finding list showing the failed MAMI codes
**Why human:** Requires live ZEN Engine evaluation and React rendering

#### 4. critical_override Override Path

**Test:** Answer q_S-HRA-1.3 (code S-HRA-1.3, critical_override: false, moscow_level: MUST) with NO, then score
**Expected:** Finding for S-HRA-1.3 appears as NON_CRITICAL, not CRITICAL
**Why human:** Requires complete stack: DB for saved answers, ZEN Engine for JDM evaluation, frontend for display

---

### Gaps Summary

No blocking gaps. All 5 observable truths are verified with substantive implementations that are correctly wired together.

Two minor observations that do not block the phase goal:

1. AnswerRead schema types answered_at and updated_at as str while the model has datetime fields. Pydantic v2 handles this transparently via from_attributes serialization. No data corruption risk, just a misleading type annotation.

2. The auto-save useMutation has no onError handler. If the server-side COMPLY_EXPLAIN validation fires (422), the failure is silent in the UI. The data integrity guarantee holds (no invalid data is stored), but the user does not receive feedback that their save failed. This is a UX quality gap, not a functional gap.

---

_Verified: 2026-02-17_
_Verifier: Claude (gsd-verifier)_
