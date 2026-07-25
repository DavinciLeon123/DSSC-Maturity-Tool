# Phase 15: Questionnaire Submission API, Wizard UI & Save Reliability - Pattern Map

**Mapped:** 2026-07-25
**Files analyzed:** 15
**Analogs found:** 14 / 15 (all files have at least a role-match; most are direct rebuild-in-place analogs of themselves)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/lib/questionnaire.ts` | utility (API client/types) | request-response | itself (pre-rewrite version) + `frontend/src/lib/api.ts` (axios instance) | exact (same file, schema rewrite) |
| `frontend/src/lib/assessments.ts` (new) | utility (API client/types) | request-response | `frontend/src/lib/questionnaire.ts` (`saveAnswer`/`fetchAnswers` shape) | role-match |
| `frontend/src/hooks/useDebouncedSave.ts` (new) | hook | event-driven | none in codebase (greenfield) — closest conceptual precedent is `WizardPage.tsx`'s `useMutation` + `useRef` unmount-save pattern (lines 136-173, 230-254) | no analog (new pattern class) |
| `frontend/src/components/questionnaire/WizardPage.tsx` | component (controller-ish, orchestrates save/nav/submit) | request-response + event-driven | itself (pre-rebuild version) | exact (same file, full rebuild) |
| `frontend/src/components/questionnaire/QuestionCard.tsx` | component | request-response (props-driven) | itself (pre-rebuild version) | exact |
| `frontend/src/components/questionnaire/AnswerButtonGroup.tsx` → RadioScale | component | request-response (props-driven) | itself (pre-rebuild version) | exact |
| `frontend/src/components/questionnaire/StepPills.tsx` | component | request-response (props-driven) | itself (extend, not rebuild) | exact |
| `frontend/src/routes/_app/questionnaire.tsx` | route | request-response | itself (minor edit) | exact |
| `frontend/src/routes/_app/assessments.tsx` (new, history page) | route/component | request-response | `frontend/src/routes/_app/admin.index.tsx` (Table + Card + loading/error pattern) | role-match |
| `frontend/src/routes/_app/dashboard.tsx` | route/component | request-response | itself (extend with Modal.confirm + link) | exact |
| `backend/app/api/v1/questionnaire.py` (`_get_or_create_draft_assessment`, `upsert_answer`, rate limiter) | controller/route | CRUD | itself (modify in place) | exact |
| `backend/app/api/v1/initiatives.py` (`GET /initiatives/{id}/assessments`, new) | controller/route | CRUD (read/aggregate) | `submit_initiative` in the same file (lines 79-115) — ownership check + Assessment query pattern | exact (sibling route, same file) |
| `backend/app/schemas/assessment.py` (new) | model (Pydantic schema) | transform | `backend/app/schemas/initiative.py` (`InitiativeRead`) style; `backend/app/schemas/questionnaire.py` (`AnswerRead`) | role-match |
| `backend/app/services/dimension_scoring.py` (new helper for submitted assessments) | service | CRUD/transform | `get_current_assessment` in the same file (lines 43-59) | exact (sibling function, same file) |
| `backend/alembic` migration (new: `(initiative_id, version)` unique constraint + `last_viewed_category_id` column) | migration | batch/schema | `i9d7e6f5a4b3` (Phase 13's hand-written migration adding `uq_assessment_one_draft_per_initiative`) | exact (same file family, hand-written convention) |

## Pattern Assignments

### `backend/app/api/v1/questionnaire.py` (controller, CRUD) — MODIFY

**Analog:** itself, `_get_or_create_draft_assessment` (lines 41-87) and `upsert_answer` (lines 90-181)

**Imports pattern** (lines 1-16):
```python
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.deps import get_current_user, get_dssc_questionnaire_config
from app.db.session import get_session
from app.models.assessment import Assessment, AssessmentStatus
from app.models.initiative import Initiative, InitiativeStatus
from app.models.questionnaire import QuestionnaireAnswer
from app.models.user import User
from app.schemas.questionnaire import AnswerCreate, AnswerRead
```
Add `from app.core.security import decode_access_token` for the new per-user key function (D-15/SAVE-03).

**Race-safe create-with-IntegrityError-retry pattern to copy verbatim, extended with version increment** (lines 41-87):
```python
def _get_or_create_draft_assessment(session: Session, initiative_id: int) -> Assessment:
    assessment = session.exec(
        select(Assessment)
        .where(
            Assessment.initiative_id == initiative_id,
            Assessment.status == AssessmentStatus.draft,
        )
        .order_by(Assessment.created_at.desc())
    ).first()
    if assessment:
        return assessment

    assessment = Assessment(initiative_id=initiative_id)  # ADD: version=next_version (D-15)
    session.add(assessment)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        assessment = session.exec(
            select(Assessment)
            .where(
                Assessment.initiative_id == initiative_id,
                Assessment.status == AssessmentStatus.draft,
            )
            .order_by(Assessment.created_at.desc())
        ).first()
        if assessment is None:
            raise
        return assessment
    session.refresh(assessment)
    return assessment
```
RESEARCH.md's "D-15: Version Increment Logic" section has the exact modified version (adds `func.max(Assessment.version)` query before the insert) — copy that, not a fresh design.

**Ownership-check + config-validation pattern to copy for the new key function's fallback and for any new route** (lines 111-149): the `session.get(Initiative, initiative_id)` → 404 → `initiative.user_id != current_user.id` → 403 → status-lock 403 sequence is the house style for every mutating endpoint touching an initiative. Reuse verbatim in the new history endpoint (read-only variant, no status-lock check needed there).

**slowapi Limiter + decorator convention** (lines 18-19, 93):
```python
limiter = Limiter(key_func=get_remote_address)   # → replace key_func with get_user_or_ip_key
...
@limiter.limit("60/minute")                       # → raise to "120/minute" per RESEARCH A1
```
New key function (copy from RESEARCH.md Pitfall 1, reusing `decode_access_token` per Don't-Hand-Roll):
```python
def get_user_or_ip_key(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        sub = decode_access_token(auth_header[len("Bearer "):])
        if sub:
            return f"user:{sub}"
    return get_remote_address(request)
```

**Postgres upsert pattern** (lines 153-171) — unchanged, no modification needed; this is the exact shape SAVE-01's debounced-per-answer save calls into with zero backend change.

---

### `backend/app/api/v1/initiatives.py` (controller, CRUD) — NEW ROUTE alongside `submit_initiative`

**Analog:** `submit_initiative` (lines 79-115) in the same file — ownership check + Assessment query + response shape conventions.

**Imports to add:**
```python
from app.core.deps import get_dssc_questionnaire_config
from app.schemas.assessment import AssessmentSummary
from app.services.dimension_scoring import compute_dimension_scores  # existing, assessment_id-agnostic
```

**Ownership + query pattern to copy** (lines 92-108):
```python
initiative = session.get(Initiative, initiative_id)
if not initiative:
    raise HTTPException(status_code=404, detail="Initiative not found")
if initiative.user_id != current_user.id:
    raise HTTPException(status_code=403, detail="Not your initiative")

assessment = session.exec(
    select(Assessment)
    .where(
        Assessment.initiative_id == initiative_id,
        Assessment.status == AssessmentStatus.draft,
    )
    .order_by(Assessment.created_at.desc())
).first()
```
For the new `GET /{initiative_id}/assessments` route, swap `AssessmentStatus.draft` → `AssessmentStatus.submitted` and `.first()` → `.all()`, ordered by `Assessment.version`. Full route body is in RESEARCH.md's "Greenfield History Endpoint" section — copy that shape directly rather than re-deriving it (already reviewed/cross-checked against ownership/security conventions above).

**`_to_read`-style response-shaping helper convention** (lines 118-136): follow the same "private `_to_...` function below the routes, converts a DB model to its Pydantic Read schema" idiom for any `AssessmentSummary`-building helper, rather than inlining the shape construction in the route body.

---

### `backend/app/schemas/assessment.py` (new schema file)

**Analog:** `backend/app/schemas/questionnaire.py` (`AnswerRead`) — check this file's exact field-naming/typing convention (not re-read this session; reuse whatever base-model/orm-mode convention `AnswerRead`/`InitiativeRead` already use, e.g. `model_config = ConfigDict(from_attributes=True)` if present) before hand-writing `AssessmentSummary`/`AssessmentHistoryResponse`. RESEARCH.md's Greenfield History Endpoint section has the target shape:
```python
class AssessmentSummary(BaseModel):
    id: int
    version: int
    submitted_at: str
    overall_average: float
    dimension_scores: list[dict]
```

---

### `backend/app/services/dimension_scoring.py` (service, CRUD/transform) — MODIFY (add helper)

**Analog:** `get_current_assessment` (lines 43-59) in the same file — same file, sibling function, same docstring-explains-scope convention.

**Pattern to copy, adapted per Pitfall 5 (do NOT generalize `get_current_assessment` — write a separate query):**
```python
def get_current_assessment(session: Session, initiative_id: int) -> Assessment | None:
    """... most-recent draft ..."""
    return session.exec(
        select(Assessment)
        .where(
            Assessment.initiative_id == initiative_id,
            Assessment.status == AssessmentStatus.draft,
        )
        .order_by(Assessment.created_at.desc())
    ).first()
```
New helper (e.g. `list_submitted_assessments`) should mirror this exactly but filter `AssessmentStatus.submitted` and return `.all()` ordered by `version`. `compute_dimension_scores(session, assessment_id, config)` itself (referenced, not shown — already assessment_id-agnostic per RESEARCH Don't-Hand-Roll) needs no changes; call it once per row returned by the new helper.

**Config-derived structure idiom to keep following** (lines 22-38): `_full_question_ids`/`_category_question_counts`/`_category_names` all derive from the `config` dict param, never hardcoded — the new history endpoint's dimension-name column (for the comparison table) should reuse `_category_names(config)`, not a new hardcoded list.

---

### `frontend/src/components/questionnaire/WizardPage.tsx` (component, request-response + event-driven) — FULL REBUILD

**Analog:** itself (pre-rebuild) — the `AutosaveBadge` component (lines 19-82), the `useMutation` save wiring (lines 136-173), and the nav-button disabled/style convention (lines 606-643) are all direct carry-overs; only their wiring changes.

**AutosaveBadge state-machine shell to extend, not replace** (lines 19-82): keep the `SaveBadgeState = "idle"|"saving"|"saved"|"failed"|"rate-limited"` type and the same per-state `<span>` styling convention; per UI-SPEC, `failed` now needs two visual sub-states (transient-retrying amber vs. terminal red) — extend the component's props/logic rather than introducing a 6th top-level state name, per D-09's "extend `AutosaveBadge` rather than replacing it."

**`useMutation` + `onError` 429-branching pattern to copy for the new save call site** (lines 136-173):
```typescript
const saveMutation = useMutation({
  mutationFn: async ({ questionId, ... }) => {
    setBadgeState("saving");
    return saveAnswer(initiativeId, questionId, { ... });
  },
  onSuccess: () => {
    setBadgeState("saved");
    setTimeout(() => setBadgeState("idle"), 2000);
  },
  onError: (error: unknown) => {
    const status = (error as { response?: { status?: number } }).response?.status;
    if (status === 429) {
      setBadgeState("rate-limited");
      setTimeout(() => setBadgeState("idle"), 3000);
    } else {
      setBadgeState("failed");   // → wire into RESEARCH Pattern 3's retry-with-backoff instead of a dead end
    }
  },
});
```
This 429-vs-other branch is exactly right and should be kept; only the `else` branch's terminal handling needs the new retry-ladder wiring from RESEARCH.md Pattern 3.

**`useRef`-based unmount fire-and-forget save to replace with `useDebouncedSave`'s `flushAll()`** (lines 230-254) — this exact pattern is what SAVE-04/D-07 supersedes; RESEARCH.md's `flushOnUnload`/`beforeunload` listener (D-07 section) is the direct replacement, called from a `useEffect` with `window.addEventListener("beforeunload", ...)` instead of the current cleanup-function-on-unmount approach.

**Next/Back button disabled-style convention to copy for the new failed-save blocking (D-10)** (lines 606-643): the `isNextDisabled`/style ternary (`border`, `background`, `color`, `cursor` all keyed off one boolean) is the exact pattern to extend — add `badgeState === "failed"` (terminal only, not `retrying`/`rate-limited`) into the existing `isNextDisabled` boolean rather than introducing a parallel disabled-check.

**Submitted-confirmation page markup** (lines 347-421) — mostly unchanged; copy string is now `Submit assessment →` per UI-SPEC Copywriting Contract instead of `Finish →` (line 641).

---

### `frontend/src/components/questionnaire/AnswerButtonGroup.tsx` → RadioScale (component) — FULL REBUILD

**Analog:** itself (pre-rebuild) for the selected/unselected visual language (filled circle + border-color swap per UI-SPEC Component Inventory) — read this file directly during planning/implementation for the exact selected-state CSS if not already in context; RESEARCH.md Pattern 1 has the target new shape (horizontal `flex` row, `question.options ?? config.default_options`, 44px hit-target per UI-SPEC Spacing Scale exception).

---

### `frontend/src/lib/questionnaire.ts` (utility) — FULL REWRITE

**Analog:** itself (pre-rewrite) for the exported-function-shape convention (`saveAnswer`/`fetchAnswers`/`fetchQuestionnaireConfig` as thin wrappers around the shared `api` axios instance from `frontend/src/lib/api.ts`) — keep that wrapper-function convention, just retype the payload/response shapes per RESEARCH.md's `AnswerOption`/`Question`/`QuestionnaireConfig` interfaces and the live backend `AnswerCreate`/`AnswerRead` (`question_id`/`category_id`/`score: 1-5`).

---

### `frontend/src/lib/assessments.ts` (new)

**Analog:** `frontend/src/lib/questionnaire.ts`'s `saveAnswer`/`fetchAnswers` wrapper-function convention (thin `api.get(...)`/`api.put(...)` calls returning typed data). New `fetchAssessmentHistory(initiativeId)` should follow the identical thin-wrapper shape, hitting `GET /initiatives/{id}/assessments`.

---

### `frontend/src/routes/_app/assessments.tsx` (new history page)

**Analog:** `frontend/src/routes/_app/admin.index.tsx` — `message.useMessage()` toast pattern (line 38), antd `Table` column-definitions convention (lines ~130-276), and the `Card`/`Tabs`/`Alert` composition for a list+detail page layout.

```typescript
import { Card, Table, Button, Popconfirm, Tag, Modal, Tabs, message, Alert } from "antd";
...
const [messageApi, contextHolder] = message.useMessage();
```
Reuse this exact toast-setup convention for the history page's load-error retry flow (UI-SPEC: "same failed→retry pattern as autosave"), and the `Table` `dataSource`+`columns` shape for both the version-list table and the per-dimension comparison table (D-16a/b).

---

### `frontend/src/routes/_app/dashboard.tsx` — EXTEND (D-13 confirm dialog + D-17 history link)

**Analog:** `admin.index.tsx`'s `Modal.confirm({...})` usage (line 119) for the "Start new assessment" confirmation dialog — copy that call shape (title/content/onOk) rather than hand-rolling a new `Modal` component instance. Dashboard's existing inline `Alert` error pattern (referenced in CONTEXT.md, ~lines 281-320) stays the convention for any new error states on this page.

---

### `backend/alembic` migration (new: unique constraint + `last_viewed_category_id` column)

**Analog:** `i9d7e6f5a4b3` (Phase 13's hand-written migration, referenced at CONTEXT.md line 43 and RESEARCH.md's `_get_or_create_draft_assessment` docstring) which added `uq_assessment_one_draft_per_initiative` as a partial unique index on the `assessment` table. Follow the same hand-written-not-autogenerate convention (per RESEARCH.md's explicit migration note) for both the new `(initiative_id, version)` unique constraint (Pitfall 4) and the new nullable `last_viewed_category_id` column (D-08) — bundle both into one migration since both touch the same `assessment` table, per RESEARCH.md's explicit recommendation.

## Shared Patterns

### Ownership re-derivation (Access Control, V4)
**Source:** `backend/app/api/v1/questionnaire.py` lines 111-116, `backend/app/api/v1/initiatives.py` lines 92-96/59-63
**Apply to:** Every new/modified backend route this phase (new history endpoint, modified `upsert_answer`)
```python
initiative = session.get(Initiative, initiative_id)
if not initiative:
    raise HTTPException(status_code=404, detail="Initiative not found")
if initiative.user_id != current_user.id:
    raise HTTPException(status_code=403, detail="Not your initiative")
```

### IntegrityError-catch-and-requery race safety
**Source:** `backend/app/api/v1/questionnaire.py` lines 66-85 (`_get_or_create_draft_assessment`)
**Apply to:** D-15's version-increment logic (Pitfall 4) — same shape, requery on the new `(initiative_id, version)` constraint instead of the draft-uniqueness one.

### slowapi per-file `Limiter` + `@limiter.limit(...)` decorator
**Source:** `backend/app/api/v1/questionnaire.py` line 19/93, `backend/app/api/v1/auth.py` line 25/60 (`@limiter.limit("10/minute")`)
**Apply to:** The modified `upsert_answer` rate limit (key_func swap + `120/minute`, SAVE-03) — no other route in this phase adds new rate limiting.

### AutosaveBadge state-machine + amber/red two-tier error convention
**Source:** `frontend/src/components/questionnaire/WizardPage.tsx` lines 19-82
**Apply to:** `WizardPage.tsx`'s rebuild (SAVE-02/D-09) and, per UI-SPEC, the history page's load-error banner ("same failed→retry pattern as autosave, for consistency") — one shared visual/copy convention across both surfaces.

### antd Table + `message.useMessage()` list-page convention
**Source:** `frontend/src/routes/_app/admin.index.tsx` lines 3, 38, 130-276
**Apply to:** New `assessments.tsx` history page (both the version-list table and comparison table).

### Config-derived structure, never hardcoded
**Source:** `backend/app/services/dimension_scoring.py` lines 22-38 (`_full_question_ids`/`_category_question_counts`/`_category_names`), `backend/app/api/v1/questionnaire.py` lines 138-142 (`valid_categories_by_question`)
**Apply to:** RadioScale's option list (`question.options ?? config.default_options`), the new history endpoint's dimension names (reuse `_category_names(config)`), any per-category counts in `StepPills.tsx`'s new "N of 52 answered" counter.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `frontend/src/hooks/useDebouncedSave.ts` | hook | event-driven | No existing per-key debounce-timer hook exists in this codebase; this is a genuinely new pattern class. RESEARCH.md's Pattern 2 code example is the concrete starting point to use instead of a codebase analog. |

## Metadata

**Analog search scope:** `frontend/src/components/questionnaire/`, `frontend/src/routes/_app/`, `frontend/src/lib/`, `backend/app/api/v1/`, `backend/app/services/`, `backend/app/models/`, `backend/alembic/versions/`
**Files scanned:** ~15 (all read directly this session or in RESEARCH.md's prior session, per its Sources section)
**Pattern extraction date:** 2026-07-25
