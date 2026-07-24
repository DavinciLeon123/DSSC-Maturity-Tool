# Phase 15: Questionnaire Submission API, Wizard UI & Save Reliability - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-24
**Phase:** 15-questionnaire-submission-api-wizard-ui-save-reliability
**Areas discussed:** Wizard flow & navigation, Autosave timing & tab-close safety, Save failure & retry UX, Retake flow & history view

---

## Wizard flow & navigation

| Option | Description | Selected |
|--------|-------------|----------|
| One category per page (current model) | Matches existing WizardPage structure, natural save checkpoint per category | ✓ |
| One question at a time | Simplest page, but 52 steps is a lot of Next-clicks | |
| Single continuous scroll (all 52 on one page) | No pagination, better overview but very long page | |

**User's choice:** One category per page (current model)

| Option | Description | Selected |
|--------|-------------|----------|
| Any order, Next enabled only once all answered | Flexible, still enforces completion before advancing | ✓ |
| Any order, Next always enabled (can skip ahead) | More permissive, risks confusing submit-time 422 | |
| Strict top-to-bottom within the page | Most rigid | |

**User's choice:** Any order, Next enabled only once all answered

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, freely, any time before submit | Matches existing Back button behavior | ✓ |
| Yes, but only the immediately preceding category | More restrictive | |
| No, once Next is clicked the category is locked | Simplest state model, regression from current wizard | |

**User's choice:** Yes, freely, any time before submit

| Option | Description | Selected |
|--------|-------------|----------|
| Category-level progress ("Category 3 of 6") | Simple stepper | |
| Question-level progress ("27 of 52 answered") | More granular | |
| Both — category stepper plus overall question count | Combines both | ✓ |

**User's choice:** Both — category stepper plus overall question count
**Notes:** Wizard structure stays close to the existing model; the real rebuild need is the answer widget (QSTN-02) and the payload shape, not the page-level flow.

---

## Autosave timing & tab-close safety

| Option | Description | Selected |
|--------|-------------|----------|
| Save each answer individually, debounced (~1-2s) | Matches backend's per-question PUT shape | ✓ |
| Batch all changed answers on the page, debounced | Fewer requests, but delays individual save confirmation | |
| Save immediately on every answer change, no debounce | Fastest feedback, but bursts of requests | |

**User's choice:** Save each answer individually, debounced (~1-2s after selection)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — Next/Back always flushes pending saves first | Guarantees no answer lost on navigation | ✓ |
| No — rely purely on the debounce timer | Simpler, but creates a loss window | |

**User's choice:** Yes — Next/Back always flushes pending saves first

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — beforeunload handler fires a synchronous save (sendBeacon) | Closes the last real SAVE-04 gap | ✓ |
| No — accept a small re-entry risk | Simpler, no beforeunload wiring | |

**User's choice:** Yes — beforeunload handler fires a synchronous save (sendBeacon) for any pending answer
**Notes:** Exact unload-safe save mechanism (sendBeacon vs fetch keepalive, given auth header needs) flagged as a research question, not settled here.

| Option | Description | Selected |
|--------|-------------|----------|
| Back at the last category viewed, answers pre-filled | Most seamless resume | ✓ |
| Back at category 1, answers pre-filled | Simpler, no position tracking needed | |

**User's choice:** Back on the wizard, at the last category they were on, with all saved answers pre-filled

---

## Save failure & retry UX

| Option | Description | Selected |
|--------|-------------|----------|
| Automatic retry with backoff, manual retry button if it keeps failing | Best of both — resolves transient issues silently, surfaces persistent ones | ✓ |
| Manual retry button only, no automatic attempts | Most transparent, more clicks | |
| Automatic retry with backoff only, no manual button | Risk of no escape if retries exhaust | |

**User's choice:** Automatic retry with backoff, manual retry button if it keeps failing

| Option | Description | Selected |
|--------|-------------|----------|
| Block Next until the failed save succeeds or is dismissed | Prevents moving on with an unsaved answer | ✓ |
| Allow navigation, show a persistent warning banner | Less disruptive, risks submit-without-realizing | |

**User's choice:** Block Next until the failed save succeeds or is dismissed

| Option | Description | Selected |
|--------|-------------|----------|
| Retry is the only way past it — no dismiss/override | Strongest guarantee against silent data loss | ✓ |
| Allow an explicit "Continue anyway" override with a clear warning | More forgiving, cuts against SAVE-02's intent | |

**User's choice:** Retry is the only way past it — no dismiss/override option

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — Submit is blocked the same way if any save is pending/failed | Consistent with the Next-button rule | ✓ |
| No special handling — Submit already fails via the existing 422 gate | Relies on an indirect, more confusing failure path | |

**User's choice:** Yes — Submit is blocked the same way if any save is still pending/failed
**Notes:** Strong, consistent preference throughout this area for blocking over convenience — no silent or overridable data loss anywhere in the save path.

---

## Retake flow & history view

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit "Start new assessment" button with a confirmation dialog | Deliberate action for a permanent new version | ✓ |
| Implicit — navigating to the questionnaire after submission just starts a new draft (current behavior) | Zero extra UI, but risk of accidental retake | |

**User's choice:** Explicit "Start new assessment" button with a confirmation dialog

| Option | Description | Selected |
|--------|-------------|----------|
| Blank — the user answers all 52 questions fresh | Matches a genuine re-scan framing | ✓ |
| Pre-filled with the previous assessment's answers, editable | Faster, but risks stale/unreviewed answers | |

**User's choice:** Blank — the user answers all 52 questions fresh

| Option | Description | Selected |
|--------|-------------|----------|
| A list/table of past versions linking to each version's report | Keeps score-comparison visualization as Phase 16's job | |
| A list/table PLUS a simple side-by-side per-dimension comparison table | Goes further, gives "compare across versions" a concrete non-charted answer now | ✓ |

**User's choice:** A list/table of past versions PLUS a simple side-by-side per-dimension score comparison table across all versions

| Option | Description | Selected |
|--------|-------------|----------|
| New dedicated page/route (e.g. /assessments or /history), linked from dashboard | Keeps dashboard's current layout clean | ✓ |
| Expand the existing dashboard initiative card in place | No new route, but risks crowding the card | |

**User's choice:** New dedicated page/route (e.g. /assessments or /history), linked from the dashboard
**Notes:** Same strictness theme as the save-failure area — retaking is treated as a deliberate, permanent, auditable action, not a casual one.

---

## Claude's Discretion

- Exact debounce interval within the ~1-2s range
- Exact beforeunload-safe save mechanism (sendBeacon vs. fetch keepalive vs. other), given the PUT endpoint needs an auth header
- Exact retry backoff schedule/attempt count before falling back to the manual button
- Exact storage location for "last viewed category"
- Exact new history-listing endpoint shape/path and response schema
- Exact route path/naming for the new history page
- Fate/restructuring of legacy frontend files that no longer match the backend shape (`questionnaire.ts`, `AnswerButtonGroup.tsx`, `QuestionCard.tsx`)
- Exact new per-user rate-limit key function and limit value for SAVE-03

## Deferred Ideas

None — discussion stayed within phase scope. No scope-creep topics came up.
