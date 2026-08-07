# Phase 15: Questionnaire Submission API, Wizard UI & Save Reliability - Research

**Researched:** 2026-07-24
**Domain:** Frontend save-reliability UX (debounce/retry/beforeunload), FastAPI per-user rate limiting, versioned-assessment data modeling, greenfield history/comparison endpoints
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Wizard flow & navigation**
- D-01: Keep the current one-category-per-page pagination model (6 pages, 8-9 questions each) — matches the existing `WizardPage.tsx` structure, no need to redesign the page-level shape.
- D-02: Within a category page, questions can be answered in any order. Next is enabled only once every question on that page has an answer (not before). Still relies on the backend's existing all-answered completion gate (`assert_assessment_complete`, SCOR-04) as the final authority at submit time.
- D-03: Back navigation is fully free — the user can jump back to any earlier category and change an already-saved answer at any point before final submission.
- D-04: Progress indicator shows both a category-level stepper (e.g. "Category 3 of 6") and an overall answered-count (e.g. "27 of 52 answered").

**Autosave timing & tab-close safety (SAVE-01/04)**
- D-05: Autosave triggers per-answer (not per-topic/batch), debounced ~1-2s after each selection. Matches the backend's existing `PUT /questionnaire/initiatives/{id}/answers/{question_id}` shape — no batching endpoint needed.
- D-06: Clicking Next or Back always flushes any pending debounced save immediately first — a synchronous safety net on top of the debounce.
- D-07: A `beforeunload` handler forces any still-pending debounced save through before the tab closes/refreshes (conceptually `navigator.sendBeacon`-style "fire on unload" — exact mechanism, e.g. `sendBeacon` vs. `fetch(..., {keepalive: true})`, is Claude's/researcher's call given the PUT endpoint requires auth headers and sendBeacon cannot set custom headers).
- D-08: On returning after tab close/hard-refresh, user lands back at the last category they were viewing, with all previously-saved answers pre-filled. Exact storage location for "last viewed category" is Claude's discretion.

**Save failure & retry UX (SAVE-02)**
- D-09: On save failure: automatic retry with backoff first; if exhausted, surface a manual "Retry" button. Extend the existing `AutosaveBadge` (`idle/saving/saved/failed/rate-limited`) rather than replacing it.
- D-10: A persistently-failing save blocks the Next button (and Submit, per D-12) until it succeeds.
- D-11: No dismiss/override path — Retry is the only way past a failed save.
- D-12: The same block-until-saved rule applies to the final Submit action, on top of (not instead of) the backend's existing 422 completion gate.

**Retake flow & versioning (HIST-01)**
- D-13: Starting a retake is an explicit user action — a "Start new assessment" button with a confirmation dialog.
- D-14: A new retake draft starts fully blank — no answers copied forward.
- D-15: `Assessment.version` must actually be computed and incremented on creation — `max(existing versions for this initiative) + 1` — rather than always defaulting to 1 as `_get_or_create_draft_assessment` does today.

**History view (HIST-02)**
- D-16: The history view shows both (a) a list/table of past assessment versions (date, version #, overall average score, link out) and (b) a per-dimension score comparison table across versions (plain table, not chart).
- D-17: The history view lives on a new dedicated page/route (e.g. `/assessments` or `/history`), linked from the dashboard.

### Claude's Discretion
- Exact debounce interval within the ~1-2s range (D-05).
- Exact mechanism for the beforeunload forced-flush — `sendBeacon` vs. `fetch(keepalive: true)` vs. another approach (D-07).
- Exact retry backoff schedule/attempt count before falling back to the manual button (D-09).
- Exact storage location for "last viewed category" (D-08).
- Exact new endpoint shape for listing an initiative's past assessments and its response schema (D-16/D-17).
- Exact route path/naming for the new history page (D-17).
- Fate of legacy frontend files that no longer match the backend shape (`frontend/src/lib/questionnaire.ts`, `AnswerButtonGroup.tsx`, `QuestionCard.tsx`) — full rebuild assumed.
- Exact new key function for SAVE-03's per-user rate limiting and appropriate limit value.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope (wizard rebuild, save reliability, retake/history). No scope-creep topics came up.

**Also explicitly out of scope per the phase boundary (not a CONTEXT.md "deferred idea," but binding on this research):** scoring math (Phase 14, done), radar-chart/priority-list report rendering and the frozen report data contract (Phase 16), admin aggregation (Phase 16), automated test coverage for the rebuilt subsystems beyond keeping CI green (Phase 17), and auth/security hardening beyond SAVE-03's rate-limit key function (Phase 18).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QSTN-02 | Each question presents 5 answer options via a horizontal line with radio circles, each mapped to a 1-5 maturity score | See Architecture Patterns (Pattern 1: Radio-Scale Component) and Component Inventory in 15-UI-SPEC.md — config-driven from `default_options`/`options` in `config/dssc-questionnaire.json` |
| SAVE-01 | Answers auto-saved as the user answers each question (debounced) | See Pattern 2 (Per-Answer Debounced Save Hook) — no backend change needed, existing PUT endpoint is already per-question |
| SAVE-02 | Save failures surfaced with clear retry path, no silent fire-and-forget | See Pattern 3 (Retry-with-Backoff State Machine) and Common Pitfalls 1/2 |
| SAVE-03 | Rate limiting keyed per authenticated user, not per client IP | See "SAVE-03: Per-User Rate Limiting" section — critical slowapi ordering pitfall documented |
| SAVE-04 | Closing tab / hard-refresh mid-questionnaire does not silently lose answers | See "D-07: beforeunload Flush Mechanism" section — fetch+keepalive recommended over sendBeacon |
| HIST-01 | Retaking creates a new, dated, permanently preserved assessment version | See "D-15: Version Increment Logic" section — race-condition-safe pattern mirroring existing `_get_or_create_draft_assessment` |
| HIST-02 | User can view history of past assessments and compare scores across versions | See "Greenfield History Endpoint" section — proposed `GET /initiatives/{id}/assessments` shape |
</phase_requirements>

## Summary

This phase has two very different halves. The **backend half** is low-risk, additive work on a schema that already anticipates it: `Assessment.version`/`status`/`submitted_at` already exist (Phase 13), the per-question upsert endpoint already matches the new debounced-per-answer save pattern with zero endpoint-shape changes needed, and `dimension_scoring.py`'s `compute_dimension_scores` already takes an arbitrary `assessment_id` — it just needs to be pointed at *submitted* assessments instead of only the current draft. The one real gap is `_get_or_create_draft_assessment` always creating `version=1`; this needs a `max(version)+1` computation with the same race-condition-safe pattern (DB unique index + IntegrityError catch-and-requery) already used for the one-draft-per-initiative constraint.

The **frontend half** is a full rebuild of `WizardPage.tsx`/`QuestionCard.tsx`/`AnswerButtonGroup.tsx`/`frontend/src/lib/questionnaire.ts` because they're still typed for the pre-Phase-13 3-way YES/NOT_THERE_YET/NOT_APPLICABLE + `mami_code`/followup shape, which doesn't exist anywhere in the live backend anymore. Three research questions were explicitly flagged as unsettled in CONTEXT.md and are resolved below: (1) the beforeunload flush mechanism — **`fetch(..., {keepalive: true})`, not `sendBeacon`**, because `sendBeacon` cannot carry an `Authorization` header or use a PUT verb, both hard requirements of the existing answer-save endpoint, and a single answer payload (~60 bytes) is nowhere near the 64 KiB keepalive/beacon size ceiling either approach would hit; (2) the SAVE-03 per-user rate-limit key function, which has a real, easy-to-miss gotcha — slowapi's `key_func` receives only the raw `Request`, not any of the route's `Depends()`-injected values, so `current_user` is not available inside it and the JWT must be decoded directly from the `Authorization` header inside the key function itself; (3) retry backoff — a capped exponential backoff (3 automatic attempts, ~1s/2s/4s, then hand off to the manual `Retry save` button) is the industry-standard shape and pairs cleanly with the UI-SPEC's already-locked two-tier amber-then-red badge states.

**Primary recommendation:** Rebuild the wizard's answer plumbing (`questionnaire.ts` → new types, `AnswerButtonGroup.tsx` → horizontal radio-scale, `WizardPage.tsx` → per-answer debounced save + retry state machine + `fetch(keepalive:true)` beforeunload flush) as one cohesive unit since they share the same type contract; keep the backend changes small and additive (version-increment fix, new per-user key function, new read-only history endpoint) since the schema was already built in Phase 13 to support exactly this.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Radio-scale answer capture (QSTN-02) | Browser / Client | — | Pure UI state; no server round-trip until debounced save fires |
| Debounced autosave scheduling (SAVE-01) | Browser / Client | API / Backend | Client owns the timer; backend owns the idempotent upsert it eventually calls |
| Save failure detection + retry (SAVE-02) | Browser / Client | — | Retry-with-backoff is a client-side concern; server just returns normal HTTP errors (422/429/5xx) |
| Per-user rate limiting (SAVE-03) | API / Backend | — | Must be enforced server-side (client-side throttling is not a security control) |
| Beforeunload forced flush (SAVE-04) | Browser / Client | API / Backend | Client detects unload and fires the request; backend's existing upsert handles it identically to any other save |
| Assessment version increment (HIST-01) | API / Backend | Database / Storage | Versioning is a data-integrity invariant — must be computed and enforced at write time in the same transaction, not derived client-side |
| History list + comparison table (HIST-02) | API / Backend | Browser / Client | Backend aggregates scores per submitted assessment (reusing `compute_dimension_scores`); client only renders a plain table |
| "Last viewed category" resume state (D-08) | API / Backend | Database / Storage | Must survive a hard refresh/new tab, so it cannot live in client memory or sessionStorage alone — needs server-side persistence |

## Standard Stack

### Core

No new libraries are required for this phase. Every capability is achievable with what's already installed:

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React (built-in hooks: `useState`/`useRef`/`useEffect`) | 19.2.0 (already installed) | Debounce timer, retry state machine, `beforeunload` listener | This repo has no debounce library (`lodash` is not a dependency) and debounce-via-`setTimeout`+`useRef` is ~15 lines — not a "don't hand-roll" case, it's a textbook custom hook |
| `fetch` (Browser built-in, not `axios`) | N/A | The single `beforeunload`-triggered save request | `axios`'s underlying XHR transport does not support the `keepalive` flag the way native `fetch` does; this one call site should bypass the shared `api` axios instance and call native `fetch` directly (see Pitfall 3) |
| antd `Table`/`Card`/`Button`/`Modal`/`Tag` | ^6.3.0 (already installed) | History list, comparison table, confirmation dialog | Already the established convention (`admin.index.tsx` uses `Table` for exactly this shape: dataSource + columns) |
| slowapi | >=0.1.9 (already installed) | Per-user rate limiting on the answer-save endpoint | Already in use app-wide; only the `key_func` changes, not the library |
| PyJWT | >=2.8.0 (already installed) | Decoding the JWT inside the new rate-limit key function | Already used by `app/core/security.py`'s `decode_access_token` — reuse that function directly, don't reimplement JWT decoding |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| TanStack Query (`useMutation`) | ^5.90.21 (already installed) | The debounced save call *except* the beforeunload one | Keep using it for the normal in-app save path (retry/error state integrates cleanly with `onError`); only the beforeunload flush needs to escape it (mutations are torn down on unmount/navigation, which the unload event itself may trigger) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom `useDebouncedSave` hook | `lodash.debounce` or `use-debounce` (npm package) | Would be a new dependency for ~15 lines of logic this repo doesn't otherwise need lodash for; not worth the addition |
| `fetch(keepalive:true)` for beforeunload flush | `navigator.sendBeacon()` | Rejected — cannot set `Authorization` header or use `PUT`, both required by the existing answer-save endpoint (see dedicated section below) |
| Decode JWT inside slowapi `key_func` | Add a first-class Starlette middleware that decodes the JWT once and stashes `request.state.user_email` before routing | Middleware approach is architecturally cleaner (avoids repeating decode logic if more per-user-keyed endpoints appear later) but is a larger structural change than this phase's scope; the in-key_func decode is a 3-line addition matching the existing per-file `limiter = Limiter(...)` pattern already duplicated in `auth.py`/`questionnaire.py`. Flag as a candidate for Phase 18 (SECU) if per-user rate limiting spreads to more endpoints. |
| New dedicated `assessment_history` DB column for "last viewed category" | Derive last-viewed category from the most-recently-`updated_at` answer row, mapped back to its `category_id` via config | Both are viable; the derived approach requires zero migration but needs a join through `QuestionnaireAnswer.category_id` sorted by `updated_at` at read time. See "D-08" section for the recommendation and rationale. |

**Installation:** None — no new packages required this phase.

## Package Legitimacy Audit

**Not applicable this phase.** No new external packages are introduced. All capabilities (debounce, retry/backoff, beforeunload flush, per-user rate limiting, history table) are implemented with libraries already present in `backend/pyproject.toml` and `frontend/package.json` (verified above). If the planner later decides a debounce/retry helper library is warranted after all, run the Package Legitimacy Gate at that time — do not skip it retroactively.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────── Browser / Client ───────────────────────────┐
│                                                                          │
│  QuestionCard (radio-scale, QSTN-02)                                    │
│        │ onAnswerChange(question_id, score)                             │
│        ▼                                                                │
│  WizardPage local state (localAnswers) ──────► StepPills (D-04 counter) │
│        │                                                                │
│        │ per-question debounce timer (~1.5s, D-05)                      │
│        ▼                                                                │
│  useDebouncedSave hook ──── flush() ◄── Next/Back click (D-06)          │
│        │                    flush() ◄── beforeunload event (D-07)       │
│        │ (normal path: TanStack useMutation)                            │
│        │ (unload path: raw fetch(..., {keepalive:true}))                │
│        ▼                                                                │
│  Retry-with-backoff state machine (D-09) ──► AutosaveBadge              │
│        │  (3 auto attempts: 1s/2s/4s, then                              │
│        │   terminal "failed" blocks Next/Submit, D-10/D-11/D-12)        │
│        ▼                                                                │
└────────┼─────────────────────────────────────────────────────────────--┘
         │  PUT /questionnaire/initiatives/{id}/answers/{question_id}
         │  Authorization: Bearer <jwt>
         ▼
┌─────────────────────────── API / Backend ──────────────────────────────┐
│                                                                          │
│  slowapi rate limiter                                                   │
│   key_func: decode JWT from Authorization header → email (SAVE-03)     │
│   fallback: get_remote_address (unauthenticated / malformed token)      │
│        │                                                                │
│        ▼                                                                │
│  upsert_answer()                                                        │
│   ├─ ownership check (Initiative.user_id == current_user.id)            │
│   ├─ config validation (question_id/category_id)                       │
│   ├─ _get_or_create_draft_assessment() ── version = max(existing)+1     │
│   │    (D-15, only on CREATE, race-safe via unique index + retry)       │
│   └─ pg_insert ... ON CONFLICT DO UPDATE (existing, unchanged)          │
│        │                                                                │
│        ▼                                                                │
│  Postgres: assessment (version, status draft/submitted)                 │
│            questionnaire_answer (assessment_id, question_id, score)     │
│                                                                          │
│  ── separate read path, HIST-02 ──                                      │
│  GET /initiatives/{id}/assessments                                      │
│   └─ list submitted Assessments + compute_dimension_scores(each)        │
│        │                                                                │
└────────┼─────────────────────────────────────────────────────────────--┘
         ▼
   History page (/assessments or /history, D-17)
   ├─ table: date, version, overall avg, link → /report?assessment_id=N   │
   └─ comparison table: rows=6 dimensions, cols=versions (D-16)           │
```

### Recommended Project Structure

```
frontend/src/
├── lib/
│   └── questionnaire.ts          # REBUILD: new types (question_id/category_id/score 1-5),
│                                  #   fetchQuestionnaireConfig/fetchAnswers/saveAnswer (unchanged shape,
│                                  #   new payload), + a new flushAnswerBeacon() using raw fetch+keepalive
│   └── assessments.ts            # NEW: fetchAssessmentHistory(initiativeId) for HIST-02
├── hooks/
│   └── useDebouncedSave.ts       # NEW: encapsulates timer + flush() + retry/backoff state machine
├── components/questionnaire/
│   ├── WizardPage.tsx            # REBUILD: wires useDebouncedSave, beforeunload listener, D-08 resume
│   ├── QuestionCard.tsx          # REBUILD: drop followup branch entirely
│   ├── AnswerButtonGroup.tsx     # REBUILD → RadioScale: horizontal 5-circle row, config-driven labels
│   └── StepPills.tsx             # EXTEND: add "N of 52 answered" counter (D-04)
├── routes/_app/
│   ├── questionnaire.tsx         # MINOR: pass last-viewed-category into WizardPage (D-08)
│   ├── assessments.tsx           # NEW (or history.tsx — planner's call, D-17): history page
│   └── dashboard.tsx             # EXTEND: "Start new assessment" confirm dialog (D-13) + history link (D-17)

backend/app/
├── api/v1/
│   ├── questionnaire.py          # MODIFY: _get_or_create_draft_assessment version-increment (D-15),
│   │                              #   new per-user key_func, last-viewed-category write (D-08)
│   └── initiatives.py            # NEW ROUTE: GET /initiatives/{id}/assessments (HIST-02)
├── schemas/
│   └── assessment.py             # NEW: AssessmentSummary, AssessmentHistoryResponse schemas
└── services/
    └── dimension_scoring.py      # MINOR: new get_assessment_by_id-style helper for submitted assessments
                                    #   (compute_dimension_scores already takes an arbitrary assessment_id)
```

### Pattern 1: Config-Driven Horizontal Radio-Scale

**What:** Replace the vertical 3-button stack in `AnswerButtonGroup.tsx` with a horizontal row of 5 circles, each bound to a `{label, score}` pair pulled from `question.options ?? config.default_options`.
**When to use:** Every question card (QSTN-02).
**Example:**
```typescript
// New shape, driven by config/dssc-questionnaire.json
interface AnswerOption { label: string; score: number }
interface Question {
  id: string;
  category_id: string;
  text: string;
  options?: AnswerOption[]; // overrides default_options for this question only
}
interface QuestionnaireConfig {
  version: string;
  default_options: AnswerOption[];
  categories: { id: string; name: string; questions: Question[] }[];
}

function RadioScale({ question, config, value, onChange }: {
  question: Question; config: QuestionnaireConfig;
  value: number | null; onChange: (score: number) => void;
}) {
  const options = question.options ?? config.default_options;
  return (
    <div style={{ display: "flex", gap: "0.75rem" }}>
      {options.map((opt) => (
        <label key={opt.score} style={{ display: "flex", flexDirection: "column", alignItems: "center", minHeight: 44 }}>
          <button
            type="button"
            role="radio"
            aria-checked={value === opt.score}
            onClick={() => onChange(opt.score)}
            style={{ width: 44, height: 44, /* visible circle padded to 44px hit target per UI-SPEC */ }}
          />
          <span>{opt.label}</span>
        </label>
      ))}
    </div>
  );
}
```

### Pattern 2: Per-Answer Debounced Save Hook

**What:** One debounce timer per question, not a single shared timer — otherwise answering question 2 resets question 1's pending save timer if they share state.
**When to use:** SAVE-01, wired from `QuestionCard`'s `onAnswerChange`.
**Example:**
```typescript
// Source: standard debounce-per-key pattern (no official doc — training-knowledge idiom, [ASSUMED])
function useDebouncedSave(delayMs: number, save: (questionId: string, score: number) => Promise<void>) {
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const pending = useRef<Record<string, number>>({}); // latest un-flushed value per question

  function schedule(questionId: string, score: number) {
    pending.current[questionId] = score;
    clearTimeout(timers.current[questionId]);
    timers.current[questionId] = setTimeout(() => flush(questionId), delayMs);
  }

  async function flush(questionId: string) {
    const score = pending.current[questionId];
    if (score === undefined) return;
    clearTimeout(timers.current[questionId]);
    delete pending.current[questionId];
    await save(questionId, score);
  }

  function flushAll() {
    return Promise.all(Object.keys(pending.current).map(flush));
  }

  return { schedule, flush, flushAll };
}
```
D-06 (Next/Back) calls `flushAll()` before navigating. D-07 (beforeunload) cannot `await` an async flush reliably (see Pitfall 3) — it must synchronously fire the keepalive request for whatever is still in `pending.current` at that instant.

### Pattern 3: Retry-with-Backoff State Machine (D-09)

**What:** On save failure, auto-retry up to 3 times with increasing delay (1s, 2s, 4s — a capped exponential backoff), then transition to a terminal `failed` state requiring the manual `Retry save` button. This is the industry-standard shape for client-side retry logic (capped attempt count + capped delay), matching the UI-SPEC's already-locked two-tier badge design (amber "retrying" → red "failed").
**When to use:** Every autosave call (SAVE-02), and re-armed identically on manual retry button click.
**Example:**
```typescript
// Source: general industry pattern (exponential backoff with capped attempts) — [CITED: multiple
// engineering blogs converge on 3-5 attempts, 1-2s base delay, hard cap on max delay; see Sources]
const RETRY_DELAYS_MS = [1000, 2000, 4000]; // 3 automatic attempts

async function saveWithRetry(
  attemptFn: () => Promise<void>,
  onStateChange: (state: "saving" | "retrying" | "failed" | "saved" | "rate-limited") => void,
) {
  for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt++) {
    try {
      onStateChange(attempt === 0 ? "saving" : "retrying");
      await attemptFn();
      onStateChange("saved");
      return;
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } }).response?.status;
      if (status === 429) {
        onStateChange("rate-limited"); // transient, self-healing — not the terminal path (D-09)
        return;
      }
      if (attempt === RETRY_DELAYS_MS.length) {
        onStateChange("failed"); // terminal — blocks Next/Submit (D-10/D-11/D-12), needs manual Retry
        return;
      }
      await new Promise((r) => setTimeout(r, RETRY_DELAYS_MS[attempt]));
    }
  }
}
```
Note: a 429 response is a **distinct, non-escalating** outcome from the automatic-retry ladder above — it should not consume one of the 3 auto-retry attempts, since retrying immediately into a rate limit would make the problem worse. Route 429s straight to the `rate-limited` transient state (already modeled in `AutosaveBadge`), which self-clears rather than escalating toward the terminal `failed` state.

### Anti-Patterns to Avoid
- **Sharing one global debounce timer across all questions:** answering question 2 would cancel/reset question 1's pending save. Each question needs its own timer key (Pattern 2).
- **Awaiting the debounced-save promise inside a `beforeunload` handler:** browsers do not guarantee async work started in `beforeunload` completes before the page actually unloads — this is exactly why `keepalive: true` exists (see Pitfall 3 and the D-07 section below).
- **Retrying a 429 (rate-limited) response with the same backoff ladder as a 5xx/network failure:** it will not succeed sooner and adds load to an endpoint that already signaled "slow down." Treat 429 as its own transient state (already modeled by `AutosaveBadge`'s `rate-limited` state).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT decoding inside the new rate-limit key function | A second, ad-hoc JWT decode/parsing routine in `questionnaire.py` | `app.core.security.decode_access_token` (already exists, already handles `InvalidTokenError`) | Two independent JWT-parsing implementations is exactly the kind of drift that causes auth bugs; reuse the one function |
| Version-increment race safety | A `SELECT MAX(version)` followed by a separate `INSERT` with no protection against a second concurrent request doing the same | The same IntegrityError-catch-and-requery pattern already used for `uq_assessment_one_draft_per_initiative` in `_get_or_create_draft_assessment` (CR-02 precedent) | Two concurrent "first PUT of a new retake" requests can race between the SELECT and the INSERT exactly like the existing lazy-draft-creation race; the fix is the same shape, not a new invention |
| Dimension score aggregation for past assessments | A second scoring function specific to "historical" assessments | `dimension_scoring.compute_dimension_scores(session, assessment_id, config)` (already assessment_id-agnostic) | It already accepts any `assessment_id`, draft or submitted — no new aggregation logic needed, just call it once per submitted Assessment row in the new history endpoint |

**Key insight:** This phase's backend surface area is almost entirely "point existing, already-correct primitives at a slightly wider set of rows" (submitted assessments, not just the current draft) rather than new algorithms. Resist the temptation to write parallel logic for the "history" case — reuse the same completion/scoring functions Phase 14 already built.

## Common Pitfalls

### Pitfall 1: slowapi's `key_func` cannot see `Depends()`-injected values
**What goes wrong:** A key function like `def get_rate_limit_key(request: Request, current_user: User = Depends(get_current_user)) -> str` looks reasonable but slowapi does not resolve FastAPI dependencies when calling `key_func` — it calls `key_func(request)` directly, with only the raw ASGI `Request` object, before the route's own dependencies (including `get_current_user`) have run.
**Why it happens:** slowapi's rate-limit decorator wraps the route at a layer that predates FastAPI's dependency injection for that specific call; it was designed around `get_remote_address(request)`-style functions that need nothing but the request.
**How to avoid:** Extract and decode the JWT manually inside the key function, reusing `decode_access_token`:
```python
# backend/app/api/v1/questionnaire.py
from app.core.security import decode_access_token
from slowapi.util import get_remote_address

def get_user_or_ip_key(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        sub = decode_access_token(auth_header[len("Bearer "):])
        if sub:
            return f"user:{sub}"  # sub is the user's email (unique), see create_access_token
    return get_remote_address(request)  # unauthenticated/malformed token falls back to IP-keying

limiter = Limiter(key_func=get_user_or_ip_key)
```
**Warning signs:** If a "per-user" key function is written with a `Depends(get_current_user)` parameter, it will either raise at decoration time (slowapi passes only `request`, so calling the wrapped key_func with just `request` will TypeError on a missing argument) or, if written defensively with a default, will silently fall through to some fallback for every request — either way, unit-test this key function directly (not just via HTTP) to catch the mismatch early.

### Pitfall 2: `beforeunload`'s async save will not complete before the tab closes
**What goes wrong:** A `beforeunload` handler that calls `await api.put(...)` (the shared axios instance) frequently loses the race — the browser does not wait for in-flight promises inside `beforeunload`, especially for a hard refresh or immediate tab close, so the request is aborted mid-flight and the user loses their last answer silently (exactly what SAVE-04 forbids).
**Why it happens:** `beforeunload` (and the page unload sequence generally) does not pause navigation for arbitrary async work; only a small number of browser-native mechanisms are specifically designed to survive it.
**How to avoid:** Use `fetch(url, { method: "PUT", headers: {...}, body: JSON.stringify(...), keepalive: true })` for this one call site specifically — the `keepalive` flag tells the browser to let the request outlive the page context. `sendBeacon` was ruled out (see below) because it cannot carry the `Authorization` header this endpoint requires, and cannot use `PUT`.
**Warning signs:** Manually test by filling in an answer, waiting less than the debounce interval, then closing the tab immediately — if the answer is missing on next login, the flush isn't actually surviving unload.

### Pitfall 3: `keepalive` fetch requests share a small combined payload budget across the whole page
**What goes wrong:** Browsers (per the Fetch spec, implemented by Chromium/Firefox/WebKit) enforce roughly a 64 KiB *combined* limit across all in-flight `keepalive: true` requests from a page at once — exceeding it causes the request to fail with a network error rather than queuing.
**Why it happens:** This mirrors the same historical 64 KiB single-request limit `navigator.sendBeacon()` has always had; `fetch`'s `keepalive` flag inherited a similar (if not identical) budget so a page can't use it to smuggle large uploads past unload.
**How to avoid:** Not a practical concern for this phase — a single answer payload (`{question_id, category_id, score}`) is on the order of 60-100 bytes, and only one such request should ever be in flight at unload time if D-06's flush-on-navigate is working correctly (there should be at most one pending debounce per question, not 52 simultaneous ones, by the time a user actually closes the tab). Document this constraint anyway so the planner doesn't accidentally batch multiple answers into one giant beforeunload payload later.
**Warning signs:** A "network error" specifically on the beforeunload-triggered request, with normal debounced saves working fine — check whether something is trying to flush more than one answer's worth of data in a single keepalive request.

### Pitfall 4: Version-increment race on retake creation
**What goes wrong:** If two tabs (or a double-click on "Start new assessment") both fire the first answer-save PUT for the same initiative at nearly the same instant, both could read the same `max(version)` before either commits, both compute the same next version number, and one write fails or — worse — both succeed and two Assessment rows share a version number.
**Why it happens:** This is the exact same class of race the existing `uq_assessment_one_draft_per_initiative` partial unique index already defends against for "does a draft already exist" — but the *version number itself* is not currently covered by any constraint.
**How to avoid:** Add a DB-level uniqueness guarantee on `(initiative_id, version)` (a new unique constraint/index, migration required) in addition to computing `version = max(existing versions for this initiative, default 0) + 1` in application code; catch the resulting `IntegrityError` on the rare double-insert race and re-query/retry once, mirroring `_get_or_create_draft_assessment`'s existing CR-02 handling.
**Warning signs:** Two "version 3" assessments for the same initiative in the DB, or an unhandled `IntegrityError` surfacing as a 500 on the answer-save endpoint right after a retake starts.

### Pitfall 5: `assert_assessment_complete`/`get_current_assessment` currently hardcode "current == most recent draft"
**What goes wrong:** These two functions in `dimension_scoring.py` explicitly only ever look at the most-recent **draft** assessment (their own docstrings flag this as a known Phase-15 gap). The new history endpoint must NOT reuse `get_current_assessment` to find past assessments — it needs a new, separate query for `status == submitted` assessments, ordered by version or `submitted_at`.
**Why it happens:** Phase 14 built exactly what SCOR-04 needed at the time (gate on the current in-progress draft) and explicitly deferred the "submitted-assessment history" case to this phase, per its own comment.
**How to avoid:** Write a new, separate query/helper for "all submitted assessments for this initiative" rather than trying to generalize `get_current_assessment`'s draft-only semantics — they answer genuinely different questions ("what am I filling in right now" vs. "what have I finished in the past") and conflating them risks the history endpoint accidentally surfacing an in-progress draft as if it were a completed version.
**Warning signs:** A retake-in-progress (unsubmitted draft) showing up in the history list/comparison table before the user has actually submitted it.

## Runtime State Inventory

> This phase is not a rename/refactor/migration phase — it is a feature rebuild (new wizard behavior + new versioning logic) that also touches the DB schema for D-15/Pitfall 4 (a new unique constraint) and D-08 (last-viewed-category storage). Included for completeness since a schema change is involved, even though this isn't a rename.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Existing `assessment` rows all have `version=1` (the current, unconditional default) — no existing initiative has more than one submitted assessment today, since HIST-01's increment logic has never run | None required — a fresh `version=1` for every existing row is already correct; the new increment logic only affects assessments created after this phase ships. No backfill needed. |
| Live service config | None — no external service (n8n, Datadog, etc.) references assessment versions | None |
| OS-registered state | None | None |
| Secrets/env vars | None — no new secrets/env vars introduced | None |
| Build artifacts | None — no renamed packages/modules | None |

**Nothing found requiring migration of existing data** — confirmed by inspecting `backend/app/models/assessment.py` (all rows currently default to `version=1`) and the absence of any other `Assessment.version` writer in the codebase (`_get_or_create_draft_assessment` is the only place `Assessment(...)` is constructed for this table, per `grep -rn "Assessment(" backend/app`).

## SAVE-03: Per-User Rate Limiting — Detailed Recommendation

**Current state:** `backend/app/api/v1/questionnaire.py` line 19-20 creates its own `Limiter(key_func=get_remote_address)` instance (a second, separate instance from `main.py`'s `app.state.limiter` — both exist today, which is itself a minor pre-existing duplication, not something this phase needs to fix). `@limiter.limit("60/minute")` on `upsert_answer` is IP-keyed.

**Recommendation:**
1. Replace `get_remote_address` with a new `get_user_or_ip_key` function (shown in Pitfall 1) that decodes the `Authorization` header's JWT directly via the existing `decode_access_token`, keying on the token's `sub` (email) — falling back to IP-address keying only when no valid Bearer token is present (keeps the endpoint's existing behavior for genuinely unauthenticated/malformed requests, which today would 401 anyway at the `get_current_user` dependency, but the rate limiter itself runs before that dependency resolves).
2. Raise the limit from `60/minute` to a more generous **`120/minute` per user** [ASSUMED — no external authority specifies this number]. Rationale: the old `60/minute` was sized for the old per-topic batched save (up to ~8-9 concurrent PUTs per Next/Back click, i.e. bursty but infrequent). The new per-answer debounce fires one small request per answered question (~1-2s after each), plus up to 3 automatic retries per failed save (Pattern 3) — a user who answers a whole 8-9-question category page in well under a minute, combined with a transient network blip triggering a couple of retries, could plausibly reach ~15-20 requests/minute in the worst realistic case, well under both the old and new ceiling; `120/minute` leaves comfortable headroom without meaningfully weakening abuse protection (a legitimate human cannot answer more than 52 questions total in any single session, so sustained abuse-shaped traffic still stands out clearly against this ceiling).
3. This is explicitly the one SAVE/SECU-adjacent item CONTEXT.md scopes into this phase ("SAVE-03's per-user rate-limit key function is the one exception explicitly required here") — do not expand into broader auth/security hardening (httpOnly cookies, CSRF, etc.), which is Phase 18's job.

## D-07: beforeunload Flush Mechanism — Detailed Recommendation

**Decision: `fetch(url, { keepalive: true })`, not `navigator.sendBeacon()`.**

| Requirement | `sendBeacon()` | `fetch(..., {keepalive:true})` |
|---|---|---|
| Survives page unload | Yes (designed for this) | Yes (this is exactly what the flag is for) |
| Custom `Authorization` header | **No** — `sendBeacon` does not support custom headers at all [CITED: MDN/community consensus, see Sources] | Yes — full control over headers |
| HTTP method | POST only | Any method, including the existing endpoint's `PUT` |
| Body shape | `Blob`/`FormData`/`string` — no arbitrary JSON content-type control in older engines | Ordinary `JSON.stringify(...)` body with `Content-Type: application/json`, matching the existing endpoint's expectation |
| Payload size ceiling | 64 KiB (spec-defined) | Roughly the same ceiling applies to combined in-flight keepalive bytes, but irrelevant here (single answer payload is ~100 bytes) |

Given the existing `PUT /questionnaire/initiatives/{id}/answers/{question_id}` endpoint requires both a Bearer token and the `PUT` verb, `sendBeacon` is **not viable without changing the endpoint contract** (e.g., adding a token-in-query-string variant, which would be a security regression — tokens should never appear in URLs/query strings, logs, or browser history). `fetch(..., {keepalive:true})` requires no backend change at all.

```typescript
// Recommended beforeunload handler — bypasses the shared axios `api` instance
// deliberately, since axios/XHR does not expose the keepalive flag.
function flushOnUnload(initiativeId: number, questionId: string, categoryId: string, score: number) {
  const token = authStore.getToken();
  const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";
  fetch(`${baseUrl}/questionnaire/initiatives/${initiativeId}/answers/${questionId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question_id: questionId, category_id: categoryId, score }),
    keepalive: true,
  }).catch(() => {
    // Nothing to surface — the tab is closing. This is a best-effort last resort,
    // not the primary save path (D-06's flush-on-navigate + the ~1.5s debounce already
    // cover the overwhelming majority of cases; beforeunload is the final safety net).
  });
}

useEffect(() => {
  function handler() {
    // Only fires for whatever answer(s) still have a pending debounce timer.
    Object.entries(pendingAnswersRef.current).forEach(([questionId, { categoryId, score }]) => {
      flushOnUnload(initiativeId, questionId, categoryId, score);
    });
  }
  window.addEventListener("beforeunload", handler);
  return () => window.removeEventListener("beforeunload", handler);
}, [initiativeId]);
```

**Note on `beforeunload` reliability more broadly [ASSUMED, flagged for awareness — not a required change]:** Browser engineering guidance (Chrome DevRel, MDN) has moved toward preferring `pagehide`/`visibilitychange` over `beforeunload` for unload-time work in general, because `beforeunload` listeners disable the back/forward cache (bfcache) for the page and `beforeunload` does not fire reliably for backgrounded mobile tabs killed by the OS. **D-07 in CONTEXT.md explicitly locks in "a `beforeunload` handler"** as the decision already made by the user, so this research does not recommend replacing it. If the planner wants defense-in-depth, adding a `visibilitychange`/`pagehide` listener that performs the *same* keepalive flush as a supplementary trigger (not a replacement) is a reasonable, low-risk addition — but this goes beyond D-07's literal text and should be called out to the user as an enhancement, not silently added as if it were part of the locked decision.

## D-15: Version Increment Logic — Detailed Recommendation

```python
# backend/app/api/v1/questionnaire.py — _get_or_create_draft_assessment, modified
from sqlalchemy import func

def _get_or_create_draft_assessment(session: Session, initiative_id: int) -> Assessment:
    assessment = session.exec(
        select(Assessment).where(
            Assessment.initiative_id == initiative_id,
            Assessment.status == AssessmentStatus.draft,
        ).order_by(Assessment.created_at.desc())
    ).first()
    if assessment:
        return assessment

    # D-15: compute the next version from ALL assessments (draft or submitted) for
    # this initiative, not just submitted ones — this is the "first PUT of a new
    # retake" moment, and no draft exists yet at this point in the function.
    max_version = session.exec(
        select(func.max(Assessment.version)).where(Assessment.initiative_id == initiative_id)
    ).one()
    next_version = (max_version or 0) + 1

    assessment = Assessment(initiative_id=initiative_id, version=next_version)
    session.add(assessment)
    try:
        session.commit()
    except IntegrityError:
        # Pitfall 4: two concurrent "first answer of a new retake" requests raced.
        # Requires a new unique constraint on (initiative_id, version) — see migration note below.
        session.rollback()
        assessment = session.exec(
            select(Assessment).where(
                Assessment.initiative_id == initiative_id,
                Assessment.status == AssessmentStatus.draft,
            ).order_by(Assessment.created_at.desc())
        ).first()
        if assessment is None:
            raise
        return assessment
    session.refresh(assessment)
    return assessment
```

**Migration note:** add a new Alembic migration for a unique constraint on `(initiative_id, version)` in the `assessment` table, following the existing hand-written-migration precedent (`i9d7e6f5a4b3` in Phase 13) rather than autogenerate, since this repo's migrations for this table have consistently been hand-authored.

## Greenfield History Endpoint (HIST-01/HIST-02)

**Recommended shape** (exact path/naming is Claude's discretion per CONTEXT.md — `GET /initiatives/{id}/assessments` matches the existing `/initiatives/{id}/submit` sibling-route convention already in `initiatives.py`):

```python
# backend/app/api/v1/initiatives.py — new route, alongside submit_initiative
class AssessmentSummary(BaseModel):
    id: int
    version: int
    submitted_at: str
    overall_average: float
    dimension_scores: list[dict]  # reuses DimensionScore shape from scoring.py

@router.get("/{initiative_id}/assessments", response_model=list[AssessmentSummary])
def list_assessment_history(
    initiative_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    config: dict = Depends(get_dssc_questionnaire_config),
):
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    if initiative.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your initiative")

    submitted = session.exec(
        select(Assessment).where(
            Assessment.initiative_id == initiative_id,
            Assessment.status == AssessmentStatus.submitted,
        ).order_by(Assessment.version)
    ).all()

    return [
        AssessmentSummary(
            id=a.id,
            version=a.version,
            submitted_at=a.submitted_at.isoformat() if a.submitted_at else "",
            overall_average=round(
                sum(d["score"] for d in (scores := compute_dimension_scores(session, a.id, config)))
                / len(scores), 2,
            ),
            dimension_scores=scores,
        )
        for a in submitted
    ]
```

This reuses `compute_dimension_scores` unchanged (Don't Hand-Roll table) and matches the existing ownership-check pattern duplicated across every route in this file. The frontend comparison table (D-16b) pivots this same response client-side: rows = the 6 `dimension_scores` category names (identical across all versions from config), columns = each `AssessmentSummary` in the list.

## D-08: "Last Viewed Category" Storage — Detailed Recommendation

**Recommendation: a new nullable `Assessment.last_viewed_category_id: str | None` column, written on each successful answer save** (piggy-backing on the existing upsert — set it to `answer_in.category_id` on every `upsert_answer` call), rather than the "derive from most-recently-updated answer" alternative.

**Rationale:** deriving it from `QuestionnaireAnswer` ordered by `updated_at` works, but conflates two different signals — "the last question I *answered*" is not the same as "the last *page* I was viewing" (a user could navigate to category 4, look around, answer nothing there yet, and refresh — the derived approach would incorrectly resume them at whatever category they last saved an answer in, e.g. category 3, not category 4 where they actually were). A dedicated column, updated whenever the wizard's category index changes (not only on answer save), correctly captures "where was I looking," independent of "what did I last save." This requires the frontend to make a small, cheap write (e.g. a lightweight `PATCH` or piggybacked field on the next debounced save) whenever the category index changes, even if no answer changed on that page yet — flag this as an additional small endpoint/field the planner needs to account for beyond the answer-save endpoint itself.

**Migration:** add `last_viewed_category_id` as part of the same Alembic migration as Pitfall 4's `(initiative_id, version)` unique constraint, since both touch the `assessment` table.

## Code Examples

Verified patterns from official/existing-code sources — see individual Pattern/Pitfall sections above, all of which are annotated with their source (existing codebase file+line, or `[CITED]`/`[ASSUMED]` tags for external claims).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-topic batched save on Next/Back only, `useRef`-based fire-and-forget unmount save (no error handling) | Per-answer debounced save with a real retry/backoff state machine and a `beforeunload`-safe flush | This phase (Phase 15) | Answers are saved continuously during use, not just at navigation boundaries; failures are visible and blocking rather than silent |
| IP-keyed rate limiting (`get_remote_address`) on the answer-save endpoint | JWT-derived per-user keying, falling back to IP only for unauthenticated/malformed requests | This phase (SAVE-03) | A shared office/NAT no longer causes one user's activity to throttle another's; a single user's own burst of legitimate saves is what's now bounded |
| `Assessment.version` always `1` | `version = max(existing) + 1`, computed at draft-creation time | This phase (D-15/HIST-01) | Retaking the questionnaire actually produces a distinguishable, permanently preserved new version rather than silently reusing version 1 forever |

**Deprecated/outdated:**
- `frontend/src/lib/questionnaire.ts`'s `AnswerValue = "YES"|"NOT_THERE_YET"|"NOT_APPLICABLE"` and `mami_code`/`Followup`/`Topic` types: fully superseded by Phase 13's backend schema (`question_id`/`category_id`/`score: 1-5`) and have no live backend counterpart at all — this phase must rewrite them, not adapt them incrementally.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Recommended per-user rate limit of `120/minute` (up from `60/minute`) | SAVE-03 detailed recommendation | If too low: legitimate fast-answering users occasionally get spuriously rate-limited mid-questionnaire, surfacing the (correctly-implemented) `rate-limited` badge state more than intended. If too high: reduces the effectiveness of the rate limit as an abuse control. Low blast radius either way — value is trivially adjustable, not a structural decision. |
| A2 | 3 automatic retry attempts with 1s/2s/4s backoff before falling back to the manual `Retry save` button | Pattern 3 | If too aggressive (more/longer retries): terminal-failure UX is delayed, user waits longer before getting an actionable Retry button. If too lean: users see the manual-retry state for transient blips that would have resolved on their own. Purely a UX-tuning parameter, easy to adjust post-launch. |
| A3 | New `Assessment.last_viewed_category_id` column (rather than deriving resume position from answer `updated_at`) is the right storage choice for D-08 | D-08 section | If the derived-from-answers approach is actually preferred (e.g. to avoid an extra write on category-navigation with no answer change), the planner would need a different, smaller migration — low risk, this is a genuinely open discretion call already flagged as such in CONTEXT.md, not a hidden assumption. |
| A4 | Decoding the JWT's `sub` (email) as the per-user rate-limit key satisfies "current_user.id-based" per SAVE-03's intent, without an extra DB lookup for the literal integer ID | SAVE-03 / Pitfall 1 | If a reviewer insists on the literal integer `user.id` (e.g., for log correlation with other systems), the key function would need its own DB session and a `User` lookup by email — functionally equivalent for rate-limiting purposes (email is unique, indexed) but a slightly heavier implementation. |

**If this table is empty:** N/A — see entries above. All are low-blast-radius tuning/discretion parameters explicitly delegated to "Claude's discretion" in CONTEXT.md, not load-bearing facts a wrong call would be costly to reverse.

## Open Questions (RESOLVED)

1. **Should the "last viewed category" write happen on every category-index change, or only piggyback on the next answer save?**
   - What we know: D-08 requires resuming at the last-*viewed* category, which can differ from the last-*answered* category (a user can navigate without answering).
   - What's unclear: Whether a dedicated lightweight write (e.g., a small `PATCH /questionnaire/initiatives/{id}/last-viewed-category`) is worth a new endpoint, versus piggybacking the field onto the existing answer-save payload (which would only update it when an answer is actually saved on that page — an approximation, not exact).
   - Recommendation: Add the small dedicated endpoint/field — it is a trivial write (single-column UPDATE) and gives an exact rather than approximate resume position, matching the strictness-over-convenience theme CONTEXT.md's "Specific Ideas" section identifies as the throughline of every decision in this phase.
   - RESOLVED: Adopted the dedicated-endpoint recommendation. Backend adds `PATCH /questionnaire/initiatives/{initiative_id}/last-viewed-category` (unconditional single-column write) in plan 15-01 Task 2; the frontend calls it via a `saveLastViewedCategory` wrapper on every categoryIndex change in plan 15-04 Task 2. The answer-save piggyback approach was explicitly rejected (no last-viewed write remains in `upsert_answer`) so the resume position is exact, not an approximation.

2. **Exact debounce interval within 1-2s (D-05's explicitly open range).**
   - What we know: CONTEXT.md locks the range but not the exact value.
   - What's unclear: No user testing data exists to pick 1.0s vs. 1.5s vs. 2.0s definitively.
   - Recommendation: 1.5s — splits the range, gives enough time to avoid saving on every intermediate click if a user changes their mind quickly, without feeling laggy relative to the "Saved ✓" confirmation appearing.
   - RESOLVED: 1.5s adopted, implemented in plan 15-03 (useDebouncedSave).

## Environment Availability

Skipped — this phase has no new external tool/service/runtime dependencies beyond what's already installed and verified working in this repo (Postgres via testcontainers, existing slowapi/PyJWT/antd/TanStack Query versions all confirmed present in `pyproject.toml`/`package.json` above). No new CLI tools, databases, or services are introduced.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest 9.1.1 + pytest-xdist, real-Postgres via `testcontainers[postgres]` fixtures (`backend/tests/conftest.py`) |
| Frontend framework | Vitest 4.1.10 + Testing Library (installed Phase 12; currently only `TopNav.test.tsx` exists — no wizard/questionnaire component tests yet) |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]`), `frontend/vite.config.ts`/`vitest` config (not read this session — assume standard Vitest setup per existing `TopNav.test.tsx`) |
| Quick run command | `cd backend && uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` |
| Full suite command | `cd backend && uv run pytest tests/ -n auto -m "not perf" -q` (per CLAUDE.md's `staging.yml` job) |

**Important scoping note per CONTEXT.md's explicit phase boundary:** "automated test coverage for the rebuilt subsystems" is Phase 17's job (TEST-01/02/03), not this phase's. This phase must still keep the existing CI quality gate green (ruff/mypy/pytest/docs-freshness, per CLAUDE.md), which means the two existing backend test files touching this endpoint — `backend/tests/api/test_questionnaire_answers.py` and `backend/tests/schemas/test_questionnaire_schemas.py` — will need updating wherever they assert `version == 1` unconditionally or exercise the old `get_remote_address`-keyed limiter, but writing comprehensive new Vitest coverage for the rebuilt wizard is explicitly out of scope here.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QSTN-02 | Radio-scale renders 5 config-driven options mapped to scores 1-5 | manual-only (UAT) | N/A — visual/interaction, no Vitest component tests exist yet for this subtree | ❌ Phase 17 |
| SAVE-01 | Per-answer save fires ~1.5s after selection without Next/Back | manual-only (UAT) | N/A | ❌ Phase 17 |
| SAVE-02 | Failed save shows retry, blocks Next/Submit until resolved | manual-only (UAT) | N/A | ❌ Phase 17 |
| SAVE-03 | Rate-limit key function returns per-user key, not per-IP | unit | `pytest tests/api/test_questionnaire_answers.py -k rate_limit -x` | ❌ Wave 0 — new test needed this phase to avoid shipping an untested key function change |
| SAVE-04 | beforeunload flush survives tab close | manual-only (UAT) | N/A — cannot be automated in jsdom/pytest; requires real-browser E2E (Phase 17/Playwright) | ❌ Phase 17 |
| HIST-01 | New retake creates `version = max+1`, never overwrites | unit | `pytest tests/api/test_questionnaire_answers.py -k version_increment -x` | ❌ Wave 0 — new test needed this phase, this is the core mechanism being added |
| HIST-02 | `GET /initiatives/{id}/assessments` returns submitted versions with scores | unit | `pytest tests/api/test_initiatives.py -k assessment_history -x` | ❌ Wave 0 — greenfield endpoint, new test file/cases needed |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/ -n auto -m "not perf and not benchmark" -q` (matches CLAUDE.md's local quality gate)
- **Per wave merge:** full suite including `benchmark`-marked tests, per `staging.yml`
- **Phase gate:** Full suite green before `/gsd-verify-work`, plus the manual-only UAT items above walked through conversationally per Phase 15's own success criteria (no automated E2E harness exists yet — that's Phase 17/TEST-03's Playwright suite)

### Wave 0 Gaps
- [ ] `backend/tests/api/test_questionnaire_answers.py` — add version-increment test cases (creates a submitted assessment, then a second draft, asserts `version == 2`) and a direct unit test of the new `get_user_or_ip_key` function (not just an HTTP-level test) per Pitfall 1's warning
- [ ] `backend/tests/api/test_initiatives.py` (or a new `test_assessment_history.py`) — covers the new `GET /initiatives/{id}/assessments` endpoint: empty list for no submissions, correct ordering, ownership check (404/403), scores match `compute_dimension_scores` output
- [ ] No new frontend test infrastructure required this phase — existing Vitest setup is untouched; new component tests for the rebuilt wizard are explicitly deferred to Phase 17 (TEST-02) per CONTEXT.md's phase boundary

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No (unchanged this phase) | JWT bearer token, existing `get_current_user`/`decode_access_token` — reused, not modified |
| V3 Session Management | No (unchanged this phase) | localStorage JWT storage is an existing, separately-tracked concern (SECU-01, Phase 18) — out of scope here |
| V4 Access Control | Yes | Every new/modified endpoint re-derives ownership through `Initiative.user_id == current_user.id` (already the established pattern in `upsert_answer`/`get_answers`) — the new history endpoint must follow this identically, never trusting a client-supplied `initiative_id` alone |
| V5 Input Validation | Yes | `AnswerCreate.score: int = Field(ge=1, le=5)` already enforces range at the schema layer; the existing config cross-validation (`valid_categories_by_question`) already guards against unknown `question_id`/mismatched `category_id` — no new validation gaps introduced by the debounce/retry changes since the endpoint contract itself doesn't change |
| V6 Cryptography | Yes (reuse, not new) | The new rate-limit key function decodes the *existing* JWT via the *existing* `decode_access_token`/`PyJWT` — do not add a second, parallel JWT verification path; this is exactly the "Don't Hand-Roll" item flagged above |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Rate-limit bypass via key function relying on a spoofable header | Denial of Service | `get_user_or_ip_key` derives its key from a cryptographically-verified JWT signature (via `decode_access_token`, which validates the signature before returning `sub`), not a client-supplied header value that could be forged to always produce a fresh key and dodge the limit |
| Authorization token leakage via URL/query string (if `sendBeacon` had been chosen and required a token-in-URL workaround) | Information Disclosure | Avoided entirely by choosing `fetch(keepalive:true)` (D-07 recommendation above) — the token stays in a header, never appears in the URL, browser history, or server access logs |
| Retake/version race producing duplicate or skipped version numbers under concurrent requests | Tampering (data integrity) | New `(initiative_id, version)` unique DB constraint + IntegrityError-catch-and-requery pattern (Pitfall 4), mirroring the existing `uq_assessment_one_draft_per_initiative` precedent |
| History endpoint leaking another user's assessment scores via ID guessing (initiative_id or assessment id) | Information Disclosure | Ownership re-derivation (`Initiative.user_id == current_user.id`) before returning any assessment data — identical pattern already used by every other route in `initiatives.py`/`questionnaire.py`; note IDs here are still sequential integers (SECU-02's enumerability concern is explicitly Phase 18's job, not fixed here — the ownership check is the actual control preventing unauthorized *access*, sequential IDs alone are not a vulnerability without an ownership bypass) |

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `backend/app/api/v1/questionnaire.py`, `backend/app/api/v1/initiatives.py`, `backend/app/models/assessment.py`, `backend/app/services/dimension_scoring.py`, `backend/app/core/deps.py`, `backend/app/core/security.py`, `backend/app/api/v1/auth.py`, `backend/app/main.py`, `backend/pyproject.toml` — all read directly this session, confirms exact current implementation, existing rate-limiter pattern, and available dependency versions
- Codebase inspection: `frontend/src/components/questionnaire/WizardPage.tsx`, `AnswerButtonGroup.tsx`, `QuestionCard.tsx`, `StepPills.tsx`, `frontend/src/lib/questionnaire.ts`, `frontend/src/lib/api.ts`, `frontend/src/lib/auth.ts`, `frontend/src/routes/_app/dashboard.tsx`, `frontend/src/routes/_app/questionnaire.tsx`, `frontend/src/routes/_app/admin.index.tsx`, `frontend/package.json` — confirms exact current wizard implementation, existing antd Table convention, and localStorage-based synchronous token access (feasibility check for D-07)
- `config/dssc-questionnaire.json` — confirms the `default_options`/`options` config shape QSTN-02's radio-scale must consume
- `.planning/phases/15-questionnaire-submission-api-wizard-ui-save-reliability/15-UI-SPEC.md` — approved visual/interaction contract, treated as binding input alongside CONTEXT.md

### Secondary (MEDIUM confidence — WebSearch, cross-referenced across multiple independent sources)
- [fix: replace sendBeacon with fetch keepalive for autosave on page close (langgenius/dify PR #32088)](https://github.com/langgenius/dify/pull/32088) — real-world precedent for exactly this migration (sendBeacon → fetch keepalive for an authenticated autosave-on-unload use case)
- [Making Reliable API Calls When a User Closes a Browser Tab (Medium)](https://medium.com/@abdul_mufeed/making-reliable-api-calls-when-a-user-closes-a-browser-tab-0b988aa0cbf9)
- [navigator.sendBeacon VS fetch + keepalive (blog.zackhu.com)](https://blog.zackhu.com/navigatorsendbeacon-vs-fetch-keepalive)
- [The 64KiB Limitation of navigator.sendBeacon and its implementation (Huli's blog)](https://blog.huli.tw/2025/01/06/en/navigator-sendbeacon-64kib-and-source-code/)
- [Enforce limit on inflight keepalive bytes (whatwg/fetch PR #419)](https://github.com/whatwg/fetch/pull/419) — spec-level confirmation of the combined keepalive-bytes budget
- [SlowAPI: Secure Your FastAPI App with Rate Limiting (bytescrum)](https://blog.bytescrum.com/slowapi-secure-your-fastapi-app-with-rate-limiting)
- [fastapi-user-limiter (PyPI/GitHub, epflgraph)](https://pypi.org/project/fastapi-user-limiter/) — confirms the general community pattern of extracting the rate-limit key from the Authorization header rather than via FastAPI DI
- [How to Implement Retry Logic with Exponential Backoff in React (oneuptime.com)](https://oneuptime.com/blog/post/2026-01-15-retry-logic-exponential-backoff-react/view)
- [Exponential Backoff with Jitter for the Fetch API (haikel-fazzani.eu.org)](https://www.haikel-fazzani.eu.org/javascript/fetch-api-exponential-backoff-jitter)
- [Retrying and Exponential Backoff: Smart Strategies for Robust Software (HackerOne)](https://www.hackerone.com/blog/retrying-and-exponential-backoff-smart-strategies-robust-software)
- [Window: pagehide event (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Window/pagehide_event)
- [Deprecating the unload event (Chrome for Developers)](https://developer.chrome.com/docs/web-platform/deprecating-unload)

### Tertiary (LOW confidence — flagged in Assumptions Log)
- Exact per-user rate limit value (`120/minute`) and exact retry schedule (`1s/2s/4s`, 3 attempts) — both [ASSUMED], reasoned from general industry convergence, not a specific authoritative source for this app's traffic patterns. See Assumptions Log A1/A2.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all recommendations reuse already-installed, already-in-use packages confirmed by direct file inspection
- Architecture: HIGH — backend patterns (version increment, history endpoint) directly extend existing, well-documented precedents in the same files (`_get_or_create_draft_assessment`'s CR-02 race handling, `compute_dimension_scores`'s assessment-agnostic design); frontend patterns are standard, well-established React idioms
- Pitfalls: HIGH for slowapi key_func (a well-documented, easily-verified library behavior) and keepalive/beforeunload mechanics (cross-referenced across a real migration PR + spec discussions); MEDIUM for the exact rate-limit/retry numeric values (reasoned estimates, not measured against this app's real traffic)

**Research date:** 2026-07-24
**Valid until:** 2026-08-23 (30 days — this is a stable-technology domain: slowapi/PyJWT/fetch-keepalive semantics do not change quickly; re-verify sooner only if the frontend or backend framework versions are upgraded in the interim)
