# Phase 15: Questionnaire Submission API, Wizard UI & Save Reliability - Context

**Gathered:** 2026-07-24
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase rebuilds the questionnaire-taking experience end-to-end for the new 52-question/6-category schema, and makes it actually reliable:

1. **QSTN-02** — the wizard's answer widget becomes a horizontal line of 5 radio circles per question (config-driven labels), each mapped to a 1-5 score. This replaces the old 3-way YES/NOT_THERE_YET/NOT_APPLICABLE pattern entirely.
2. **SAVE-01–04** — autosave becomes genuinely reliable: debounced per-answer saves (not just on Next/Back or unmount), visible failure + retry (not cosmetic), per-user rate limiting (not per-IP), and no silent data loss on tab close/hard refresh.
3. **HIST-01/02** — retaking the questionnaire creates a real, permanently preserved new assessment *version* (the `Assessment.version` field exists today but is never incremented), and the user can view/compare their history of past assessments.

**Out of scope for this phase:** scoring math (Phase 14, done), the radar-chart/priority-list report *rendering* and the frozen report data contract (Phase 16 — this phase's history view only shows a plain comparison table, not the chart), admin aggregation (Phase 16), automated test coverage for the rebuilt subsystems (Phase 17), and auth/security hardening (Phase 18 — SAVE-03's per-user rate-limit key function is the one exception explicitly required here).

</domain>

<decisions>
## Implementation Decisions

### Wizard flow & navigation
- **D-01:** Keep the current one-category-per-page pagination model (6 pages, 8-9 questions each) — matches the existing `WizardPage.tsx` structure, no need to redesign the page-level shape.
- **D-02:** Within a category page, questions can be answered in any order. Next is enabled only once every question on that page has an answer (not before). This still relies on the backend's existing all-answered completion gate (`assert_assessment_complete`, SCOR-04) as the final authority at submit time — the per-page gate is a UX nicety, not a replacement for it.
- **D-03:** Back navigation is fully free — the user can jump back to any earlier category and change an already-saved answer at any point before final submission (matches the existing Back-button/state-merge behavior in `WizardPage.tsx`).
- **D-04:** Progress indicator shows both a category-level stepper (e.g. "Category 3 of 6") and an overall answered-count (e.g. "27 of 52 answered").

### Autosave timing & tab-close safety (SAVE-01/04)
- **D-05:** Autosave triggers per-answer (not per-topic/batch), debounced ~1-2s after each selection. This matches the backend's existing `PUT /questionnaire/initiatives/{id}/answers/{question_id}` shape (already per-question) — no batching endpoint needed.
- **D-06:** Clicking Next or Back always flushes any pending debounced save immediately first — Next/Back is a synchronous safety net on top of the debounce, never a way to skip past an unsent save.
- **D-07:** A `beforeunload` handler forces any still-pending debounced save through before the tab actually closes/refreshes (conceptually `navigator.sendBeacon`-style "fire on unload" — exact mechanism, e.g. `sendBeacon` vs. `fetch(..., {keepalive: true})` given the PUT endpoint needs auth headers and a JSON body, is Claude's/researcher's call; sendBeacon's own limitations, notably no custom headers, are a real research question, not settled here).
- **D-08:** On returning after a tab close/hard-refresh, the user lands back on the wizard at the **last category they were viewing**, not category 1, with all previously-saved answers pre-filled. This requires persisting "last viewed category" somewhere (e.g. on the draft `Assessment` row, or a lightweight new column/field) — exact storage location is Claude's discretion during planning.

### Save failure & retry UX (SAVE-02)
- **D-09:** On save failure: automatic retry with backoff first; if that's exhausted and still failing, surface a manual "Retry" button. The existing `AutosaveBadge` component already has the visual states (`idle/saving/saved/failed/rate-limited`) but currently does nothing on `onError` besides changing badge text (WizardPage.tsx `onError` ~161-172) — this phase makes the retry mechanism real, wiring it into the badge's existing states rather than replacing the component.
- **D-10:** A persistently-failing save **blocks** the Next button (and, per D-12 below, the Submit action) until it succeeds — never silently allows navigation past an unsaved answer.
- **D-11:** No dismiss/override path. Retry is the *only* way past a failed save — there is no "Continue anyway" escape hatch, even for a demo/edge-case scenario. This is a deliberate, strict reading of SAVE-02 ("no silent fire-and-forget saves").
- **D-12:** The same block-until-saved rule applies to the final Submit action, not just Next between categories — Submit is blocked if any answer save is still pending or failed, on top of (not instead of) the backend's existing 422 completion gate.

### Retake flow & versioning (HIST-01)
- **D-13:** Starting a retake is an **explicit user action** — a "Start new assessment" button with a confirmation dialog, not the current implicit behavior (today, simply navigating to `/questionnaire` after submission silently creates a new draft `Assessment` row). The confirmation should make clear this begins a new permanent version in the user's history.
- **D-14:** A new retake draft starts **fully blank** — no answers copied forward from the previous submitted assessment. The user answers all 52 questions fresh; this is deliberately not an "edit the old one" experience.
- **D-15 (fills the versioning gap):** `Assessment.version` must actually be computed and incremented on creation — e.g. `max(existing versions for this initiative) + 1` — rather than always defaulting to 1 as `_get_or_create_draft_assessment` does today (`backend/app/api/v1/questionnaire.py` ~line 66). This is the core mechanism HIST-01 needs; the DB schema and the one-draft-at-a-time unique constraint (`uq_assessment_one_draft_per_initiative`) already support it, only the version-assignment logic is missing.

### History view (HIST-02)
- **D-16:** The history view shows **both**: (a) a list/table of past assessment versions (date, version #, overall average score) linking out to each version's report, **and** (b) a simple side-by-side per-dimension score comparison table across all versions — a plain table, not a chart. The richer radar/priority-list visualization stays Phase 16's job; this phase's comparison table is intentionally the "boring" tabular version of "compare scores across versions."
- **D-17:** The history view lives on a **new dedicated page/route** (e.g. `/assessments` or `/history`), linked from the dashboard — not inlined into the existing single-initiative dashboard card. This is greenfield: no history UI, no list-assessments endpoint, exists today at all (`backend/app/api/v1/initiatives.py` currently only has create/get-mine/update/submit).

### Claude's Discretion
- Exact debounce interval within the ~1-2s range (D-05).
- Exact mechanism for the beforeunload forced-flush — `sendBeacon` vs. `fetch(keepalive: true)` vs. another approach, given the existing PUT endpoint requires an auth header (D-07). Flag this explicitly for the researcher.
- Exact retry backoff schedule/attempt count before falling back to the manual button (D-09).
- Exact storage location for "last viewed category" (D-08) — new `Assessment` column vs. derived from most-recently-updated answer vs. other approach.
- Exact new endpoint shape for listing an initiative's past assessments (e.g. `GET /initiatives/{id}/assessments`) and its response schema (D-16/D-17).
- Exact route path/naming for the new history page (`/assessments` vs `/history` vs other) (D-17).
- Fate of the legacy frontend files that no longer match the backend shape at all — `frontend/src/lib/questionnaire.ts` (still typed for the old `YES/NOT_THERE_YET/NOT_APPLICABLE`/`mami_code` shape), `AnswerButtonGroup.tsx`, `QuestionCard.tsx` — full rebuild is assumed given QSTN-02's new answer scale, but exact file-level restructuring is a planning decision, not a user preference.
- Exact new key function for SAVE-03's per-user rate limiting on the answer-save endpoint (`backend/app/api/v1/questionnaire.py` currently uses `slowapi`'s `get_remote_address`, IP-keyed, 60/minute) — switching to a `current_user.id`-based key function and choosing an appropriate limit given the new per-answer-debounced save pattern (more frequent, smaller requests than today's per-topic save) is Claude's/researcher's call.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project/Milestone Context
- `.planning/PROJECT.md` — v2.0 milestone goals, Key Decisions table, current state through Phase 14
- `.planning/REQUIREMENTS.md` — QSTN-02, SAVE-01/02/03/04, HIST-01/02 full requirement text and Traceability table
- `.planning/ROADMAP.md` §Phase 15 — phase goal and success criteria this CONTEXT.md elaborates on; also see §Phase 16 (depends on Phase 15) for how this phase's Assessment/history data is consumed into the real report contract and admin aggregation

### Prior Phase Context (load-bearing decisions this phase builds on)
- `.planning/phases/13-new-questionnaire-config-schema-data-model-migration/13-CONTEXT.md` — D-06/D-07 there established the Assessment-first schema (draft created at first answer, `status` draft/submitted) this phase's retake/history logic extends
- `.planning/phases/14-scoring-engine-replacement/14-CONTEXT.md` — D-06 there: "fully answered" is determined by comparing distinct answered `question_id`s against the full config, scoped to a specific `Assessment.id` — this phase's per-page/per-submit save-gates (D-02/D-12) sit on top of, not instead of, that existing completion gate

### Codebase State (from this session's scouting)
- `frontend/src/components/questionnaire/WizardPage.tsx` — current wizard; per-topic save-on-Next/Back only (no debounce), `useRef`-based fire-and-forget unmount save (lines ~232-254), `AutosaveBadge` component (lines 19-82) with cosmetic-only `failed`/`retrying` states (`onError` at ~161-172 does not actually retry) — primary rebuild target for D-05 through D-12
- `frontend/src/lib/questionnaire.ts` — still typed for the pre-Phase-13 answer shape (`AnswerValue = "YES"|"NOT_THERE_YET"|"NOT_APPLICABLE"`, `mami_code`/`followup_selections`); does not match the live backend `AnswerCreate` schema (`category_id`/`score`) at all — must be rewritten for QSTN-02
- `frontend/src/components/questionnaire/AnswerButtonGroup.tsx`, `QuestionCard.tsx` — implement the old 3-way answer pattern; replacement target for the new 5-option radio-circle scale (QSTN-02)
- `frontend/src/routes/_app/questionnaire.tsx` — TanStack Router route wrapping `WizardPage`
- `frontend/src/routes/_app/dashboard.tsx` — single initiative-card view (lines ~281-320), "Start/Retake Questionnaire" button navigates straight to `/questionnaire` with no confirmation today (D-13 changes this); needs a new link to the history page (D-17)
- `backend/app/api/v1/questionnaire.py` — `PUT /questionnaire/initiatives/{id}/answers/{question_id}` (lines 90-181, `upsert_answer`): ownership check, blocks edits once `initiative.status == submitted`, validates against config, calls `_get_or_create_draft_assessment` (lines 41-87) which always creates `version=1` (D-15's gap), then does a Postgres upsert keyed by `uq_answer_per_question_v2`. `GET /questionnaire/initiatives/{id}/answers` (184-213) returns rows for the current draft only. `@limiter.limit("60/minute")` at line 93 is `slowapi`, IP-keyed via `get_remote_address` (line 19) — SAVE-03's rate-limit-per-user rework target
- `backend/app/models/assessment.py` (lines 23-31) — `Assessment`: `id`, `initiative_id` (FK), `version` (default=1, never incremented today), `status` (draft/submitted), `created_at`, `submitted_at`. Migration `i9d7e6f5a4b3` (lines 105-111) adds a partial unique index `uq_assessment_one_draft_per_initiative` on `(initiative_id) WHERE status='draft'` — blocks two simultaneous drafts, but nothing prevents multiple `submitted` rows accumulating (which is exactly what HIST-01/02 needs to build on)
- `backend/app/api/v1/initiatives.py` (lines 79-115, `submit_initiative`) — `POST /initiatives/{id}/submit` already exists, flips `initiative.status` and the current draft `Assessment.status`/`submitted_at`; called by `WizardPage.tsx`'s `submitMutation` (lines 175-179, invoked at line 264). No GET-history/list-assessments endpoint exists anywhere in this file today — greenfield for D-16/D-17
- `backend/app/services/dimension_scoring.py` — `assert_assessment_complete`/`get_current_assessment` (lines 43-59, 62-88) currently only ever look at the most-recent *draft* assessment; a comment (lines 48-51) explicitly flags "no submitted-assessment history exists yet (Phase 15's job)" — this phase is what fills that gap
- `backend/app/main.py` (lines 5-7, 54-56) — app-wide `slowapi` `Limiter(key_func=get_remote_address)` setup; `backend/app/api/v1/auth.py` (lines 25, 60) shows the existing `@limiter.limit(...)` decorator pattern to follow for the new per-user-keyed limit
- `config/dssc-questionnaire.json` — 52 questions/6 categories (9/9/9/9/8/8), `default_options`/per-question `options` arrays mapping label→1-5 score — the source of truth for QSTN-02's radio-circle labels

### Frontend conventions to reuse
- `frontend/src/routes/_app/admin.index.tsx` (line 38) — `message.useMessage()` antd toast pattern; `dashboard.tsx` — inline `Alert` error pattern. No shared retry-button/toast component exists yet — D-09's retry UI should extend the existing `AutosaveBadge` rather than introduce a third error-display convention.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AutosaveBadge` component (`WizardPage.tsx` lines 19-82) already models the right state machine (`idle/saving/saved/failed/rate-limited`) — extend it with real retry wiring (D-09) rather than building a new status component.
- Postgres `INSERT ... ON CONFLICT DO UPDATE` upsert pattern (`questionnaire.py` lines 155-171) for per-question answer saves — already exactly per-answer-shaped, ready for a debounced-per-answer save call (D-05) with no backend change needed to the upsert itself.
- `_get_or_create_draft_assessment` (`questionnaire.py` lines 41-87) is the natural place to add version-increment logic (D-15).
- App-wide `slowapi` `Limiter` — adding a per-user key function is additive, following the existing `@limiter.limit(...)` decorator convention already used on login and answer-save.

### Established Patterns
- Assessment-first schema (Phase 13) and the completion-gate pattern (Phase 14, `assert_assessment_complete`) are both load-bearing precedents this phase must build on, not around — e.g. D-12's submit-block should compose with the existing 422 gate rather than duplicate its logic.
- FastAPI lifespan/dependency-injection pattern for config (`get_dssc_questionnaire_config`) is the existing precedent for however the new history-listing endpoint resolves category/question metadata for its comparison table.

### Integration Points
- The new history endpoint(s) will live in `backend/app/api/v1/initiatives.py` alongside `submit_initiative`, most naturally as `GET /initiatives/{id}/assessments` (exact path is Claude's discretion, D-16/D-17).
- The new history page will need a scoring readout per past version — likely reusing `dimension_scoring.py`'s `compute_dimension_scores` against each *submitted* `Assessment.id`, not just the current draft (a change of scope for that service, since today it's only ever called against the current draft).

</code_context>

<specifics>
## Specific Ideas

No literal visual mockups or copy were provided during this discussion — decisions here are behavioral/structural (flow, save timing, retry strictness, versioning mechanics), not pixel-level design. `ROADMAP.md` flags this phase with `UI hint: yes`, so a follow-up `/gsd-ui-phase` design pass is expected to cover the actual radio-circle visual styling, wizard page layout details, and history-table presentation — this discussion deliberately stayed at the behavior/data level rather than pre-empting that.

The one strong, repeated theme across all four areas: **strictness over convenience** on data integrity. The user consistently chose the option that most aggressively prevents silent data loss or accidental permanent actions — blocking Next/Submit on failed saves with no override (D-10/D-11/D-12), requiring an explicit confirmed action to start a retake rather than letting it happen implicitly (D-13), and starting retakes blank rather than pre-filled (D-14) so a "compliant-looking" carried-forward answer can never mask an unreviewed question.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope (wizard rebuild, save reliability, retake/history). No scope-creep topics came up.

### Reviewed Todos (not folded)
None — no pending todos existed to review (`.planning/todos/pending/` is empty).

</deferred>

---

*Phase: 15-questionnaire-submission-api-wizard-ui-save-reliability*
*Context gathered: 2026-07-24*
