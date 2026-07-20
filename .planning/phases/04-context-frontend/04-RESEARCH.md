# Phase 4: Context and Frontend - Research

**Researched:** 2026-02-19
**Domain:** React/TanStack Router wizard UI, DSI/SP registration flow, questionnaire config explanatory content
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Wizard Navigation Model
- **Strictly linear**: Users must complete each category before advancing to the next. Forward is blocked until current category is done. Back is always available.
- **Within each category: sub-pages per topic**: Categories have 3 topics each. Users advance through topic 1 → topic 2 → topic 3 before advancing to the next category (not all questions at once).
- **Progress indicator: Step pills** — numbered circles at top (1 → 2 → 3 → 4), active category highlighted, completed categories marked with a checkmark.
- **Back behavior**: Going back auto-saves the current topic/category answers and preserves them. No answers are lost when navigating backwards.
- **End of last category**: Returns to the dashboard. User generates the compliance report manually from the dashboard (no auto-generate or review page).

#### Follow-up Question UX
- **Trigger**: Follow-up section appears when user selects YES or NOT THERE YET. Disappears (and selections are silently cleared) when user switches to NOT APPLICABLE.
- **Appearance**: Inline expand below the question card — slides down within the same question block, no navigation required.
- **Answer option style**: Horizontal button group (three styled buttons side by side: Yes / Not there yet / Not applicable), selected button highlighted.
- **Follow-up structure**: Every follow-up ALWAYS shows BOTH:
  1. Multi-select checkboxes (from the `followup.options` list in config)
  2. A free-text "Other" field
  Both are always present together whenever a follow-up appears. There is no config variation — multi-select + Other is the universal follow-up pattern.
- **Clear on answer change**: Switching from YES/NOT_THERE_YET to NOT_APPLICABLE silently clears `followup_selections` and `followup_other` (not preserved in state).

#### Explanatory Context (Category/Topic Level)
- **NOT user input**: Text notes and images in this phase are admin-provided explanatory content shown TO the user to help them understand what they're being asked — not content the user creates.
- **Level**: Optional — can be attached at category level, topic level, or both.
- **Storage**: Defined in the questionnaire JSON config files alongside category/topic definitions. Lightweight and adjustable; no database or admin UI needed now.
- **Report**: Explanatory content does NOT appear in the compliance report — in-questionnaire help only.
- **Design team handoff**: Content fields are open/adjustable so that when the design team delivers, explanatory text and images can be updated without code changes.

#### DSI/SP Selection
- **At registration**: The user selects DSI or SP during signup, not on a separate initiative form. This becomes their account-level type.
- **After login**: The app reflects their type — the correct questionnaire config (DSI or SP) is loaded based on this selection.
- **Initiative creation**: The participant_type on the initiative is set from the user's chosen type at registration (not re-asked during initiative creation).

#### Production Frontend (04-02)
- **Skipped for Phase 4**: Design team will not deliver within the next week. 04-02 is deferred.
- **RJSF**: Completely replaced by the new wizard. RJSF and its dependencies are removed.
- **Dashboard**: Claude's discretion on whether to update dashboard layout. Likely kept as-is; focus is on the questionnaire wizard.

### Claude's Discretion
- Dashboard layout changes (if any) — keep minimal, focus on wizard.
- RJSF removal approach (clean uninstall vs. co-existence).
- Exact styling of wizard cards, topic nav arrows, and button group states within the existing coe-dsc.nl branding.
- Whether to store explanatory content as embedded JSON objects in config or as separate Markdown strings — whichever is easier to update later.

### Deferred Ideas (OUT OF SCOPE)
- **04-02: Production frontend (design team)** — Design team components and styling deferred until assets are delivered.
- **Admin panel for managing explanatory content** — Currently config-file based. A Phase 5/6 admin panel could allow admins to edit explanatory text/images in-app without a code deploy.
</user_constraints>

---

## Summary

Phase 4 has two plans: 04-01 (questionnaire wizard + DSI/SP at registration) and 04-03 (question context — text notes + image upload). The codebase is already in strong shape: TanStack Router 1.160.0, React Query v5, Axios with the `{ api }` pattern, custom CSS variables (no Tailwind, no component library for core UI), and questionnaire config already follows the `categories → topics → questions` v2 structure. RJSF is currently used in `QuestionnaireForm.tsx` only and can be cleanly removed.

The wizard (04-01) is a pure frontend concern: in-component state drives category/topic navigation using `useState` for `(categoryIndex, topicIndex)`, not new routes. The `/questionnaire` route stays flat; sub-pages within it are rendered conditionally. DSI/SP selection requires a backend column addition on `User` (`participant_type`) plus updates to the register form, the `/auth/register` endpoint, and the initiative-creation flow. The explanatory context fields (`context_text`, `context_image`) are added to the JSON config files with null defaults — no backend changes required.

For 04-03 (question context), the Phase 4 original description references "user can add text notes and images per question" — but the CONTEXT.md decisions explicitly clarify that this phase's "context" is admin-provided explanatory content in config, NOT user-created content. The original success criteria items 3, 4, 5 (user context notes, image upload, report inclusion) were redefined in CONTEXT.md. Plan 04-03 scoped by CONTEXT.md = admin explanatory content in config files only (no database, no upload endpoint).

**Primary recommendation:** Build 04-01 first (wizard + DSI/SP at registration) as it touches backend and frontend. Then 04-03 (config explanatory content) is a pure config + display frontend task with no backend changes.

---

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @tanstack/react-router | 1.160.0 | File-based routing | Already in use, TanStack Router Vite plugin configured |
| @tanstack/react-query | 5.90.21 | Server state, caching | Already in use, established pattern |
| axios | 1.13.5 | HTTP client with interceptors | Named `{ api }` import pattern established |
| react | 19.2.0 | UI | Project baseline |
| antd | 6.3.0 | Installed but NOT used for wizard | Installed; planner should NOT use it for new wizard components |

### To Remove
| Library | Reason |
|---------|--------|
| @rjsf/core ^6.3.1 | Replaced by wizard — CONTEXT.md: "completely removed" |
| @rjsf/utils ^6.3.1 | RJSF dependency — remove with core |
| @rjsf/validator-ajv8 ^6.3.1 | RJSF dependency — remove with core |

### No New Libraries Needed
The wizard is custom UI using plain React + inline styles consistent with the existing codebase pattern (see Sidebar, register page — all use CSS variables, no UI library). No animation library needed (CONTEXT.md does not require CSS transitions, though a simple inline expand can use CSS `max-height` transition if desired).

**Removal:**
```bash
npm uninstall @rjsf/core @rjsf/utils @rjsf/validator-ajv8
```

---

## Architecture Patterns

### Current Project Structure (relevant to Phase 4)
```
frontend/src/
├── routes/
│   ├── __root.tsx              # Root outlet (no layout)
│   ├── _app.tsx                # Auth guard + sidebar layout
│   ├── _app/
│   │   ├── questionnaire.tsx   # REPLACE ENTIRELY with wizard
│   │   ├── dashboard.tsx       # Keep as-is (minimal touch)
│   │   └── initiative.tsx      # Keep as-is (participant_type read from user)
│   ├── _auth.tsx
│   └── _auth/
│       └── register.tsx        # ADD DSI/SP radio selection
├── components/
│   ├── questionnaire/
│   │   ├── QuestionnaireForm.tsx  # DELETE (RJSF-based)
│   │   ├── NotApplicableWidget.tsx # DELETE
│   │   ├── ComplyExplainWidget.tsx # DELETE
│   │   ├── EvidenceInput.tsx       # KEEP (Phase 3.1, still used)
│   │   ├── FindingsPanel.tsx       # KEEP (score display)
│   │   └── Sidebar.tsx             # Wrong folder but keep
│   └── layout/
│       └── Sidebar.tsx
├── lib/
│   ├── api.ts                  # { api } pattern — unchanged
│   ├── auth.ts                 # authStore — unchanged
│   └── questionnaire.ts        # UPDATE: new types for wizard
├── styles/
│   └── globals.css             # CSS variables — unchanged
└── routeTree.gen.ts            # Auto-generated — DO NOT EDIT manually
```

```
backend/app/
├── models/
│   ├── user.py                 # ADD participant_type field
│   └── questionnaire.py        # No changes (already has followup fields)
├── schemas/
│   ├── auth.py                 # UPDATE UserCreate + UserRead to include participant_type
│   └── initiative.py           # UPDATE InitiativeCreate to auto-use user's participant_type
├── api/v1/
│   ├── auth.py                 # UPDATE register endpoint to accept participant_type
│   └── initiatives.py          # UPDATE create_initiative to pull participant_type from user
└── ...

config/
├── dsi-questionnaire-v2.json   # ADD context_text/context_image to category/topic objects
└── sp-questionnaire-v2.json    # ADD context_text/context_image to category/topic objects
```

### Pattern 1: Wizard State with useState (no new routes)
**What:** Category and topic index tracked as local state inside the `/questionnaire` route component. No URL params for wizard steps.
**When to use:** The questionnaire is a single `/questionnaire` route. Sub-pages (topics) are rendered conditionally inside the component, not as separate URL segments.
**Why not search params:** The wizard's internal step is transient navigation state, not bookmarkable. Using useState keeps the pattern simple and consistent with how existing tab navigation works in the codebase.

```typescript
// Source: established codebase pattern (questionnaire.tsx uses activeCategory state)
const [categoryIndex, setCategoryIndex] = useState(0);
const [topicIndex, setTopicIndex] = useState(0);

// Derived values
const currentCategory = config.categories[categoryIndex];
const currentTopic = currentCategory.topics[topicIndex];

// Navigation
function goNext() {
  if (topicIndex < currentCategory.topics.length - 1) {
    // save current topic answers first, then advance topic
    setTopicIndex(t => t + 1);
  } else if (categoryIndex < config.categories.length - 1) {
    // save, then advance category (reset topic to 0)
    setCategoryIndex(c => c + 1);
    setTopicIndex(0);
  } else {
    // Last category last topic — return to dashboard
    navigate({ to: '/dashboard' });
  }
}

function goBack() {
  if (topicIndex > 0) {
    setTopicIndex(t => t - 1);
  } else if (categoryIndex > 0) {
    setCategoryIndex(c => c - 1);
    // topicIndex = last topic of previous category
    const prevCat = config.categories[categoryIndex - 1];
    setTopicIndex(prevCat.topics.length - 1);
  }
}
```

### Pattern 2: DSI/SP on User Model (backend)
**What:** Add `participant_type: ParticipantType` to the `User` SQLModel. The register endpoint accepts this field. Initiative creation reads `participant_type` from the authenticated user instead of accepting it as input.
**Migration needed:** Yes — a new Alembic migration adding `participant_type` column to `user` table with default `"DSI"`.

```python
# Source: backend/app/models/user.py — current pattern to follow
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    role: str = Field(default="USER")
    participant_type: str = Field(default="DSI")  # "DSI" or "SP"
    failed_login_attempts: int = Field(default=0)
    lockout_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

```python
# Updated UserCreate schema — add participant_type
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    participant_type: Literal["DSI", "SP"] = "DSI"

    @field_validator("password")
    # ... existing validator unchanged
```

```python
# Updated register endpoint — stores participant_type on user
user = User(
    email=user_in.email,
    hashed_password=hash_password(user_in.password),
    participant_type=user_in.participant_type,
)
```

```python
# Updated create_initiative — reads participant_type from user, not request body
initiative = Initiative(
    user_id=current_user.id,
    participant_type=current_user.participant_type,
    **initiative_in.model_dump(exclude={"participant_type"})
)
```

### Pattern 3: Answer Auto-Save on Navigate
**What:** Before advancing to the next topic/category, trigger `saveMutation.mutateAsync()` for all pending (dirty) answers on the current topic. Use `useMutation` with `mutateAsync` so navigation only proceeds after save completes.
**Critical detail:** The API already handles upsert (PUT endpoint with conflict resolution). No need to diff — just resave all answers for the current topic on navigation.

```typescript
// Source: established pattern from questionnaire.tsx saveMutation
async function saveCurrentTopicAndAdvance(direction: 'next' | 'back') {
  // Save all answered questions in current topic
  const questionsToSave = currentTopic.questions.filter(q => localAnswers[q.id]);
  await Promise.all(
    questionsToSave.map(q =>
      saveMutation.mutateAsync({
        questionId: q.id,
        mamiCode: q.mami_code,
        answerValue: localAnswers[q.id].answer_value,
        followupSelections: localAnswers[q.id].followup_selections,
        followupOther: localAnswers[q.id].followup_other,
      })
    )
  );
  if (direction === 'next') goNext();
  else goBack();
}
```

### Pattern 4: Button Group for Answer Selection
**What:** Three horizontal styled buttons (Yes / Not there yet / Not applicable). No radio inputs — custom button elements with visual selection state.
**Styling:** Use existing CSS variable pattern (`var(--color-green)`, `var(--color-navy)`) with border + background toggle.

```typescript
// Source: design decision from CONTEXT.md, pattern matches existing button style in codebase
const ANSWER_OPTIONS: { value: AnswerValue; label: string }[] = [
  { value: "YES", label: "Yes" },
  { value: "NOT_THERE_YET", label: "Not there yet" },
  { value: "NOT_APPLICABLE", label: "Not applicable" },
];

function AnswerButtonGroup({ value, onChange }: { value: AnswerValue | null; onChange: (v: AnswerValue) => void }) {
  return (
    <div style={{ display: "flex", gap: "0.5rem" }}>
      {ANSWER_OPTIONS.map(opt => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          style={{
            padding: "0.5rem 1rem",
            border: `2px solid ${value === opt.value ? "var(--color-green)" : "#D1D5DB"}`,
            background: value === opt.value ? "var(--color-green)" : "white",
            color: value === opt.value ? "white" : "var(--color-text-gray)",
            borderRadius: "var(--border-radius-sm)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
```

### Pattern 5: Step Pills Progress Indicator
**What:** A row of numbered pills at the top of the questionnaire page. Each pill shows its category number; the active one uses `var(--color-navy)` background with white text; completed ones show a checkmark icon.
**Completion logic:** A category is "complete" when ALL required questions in all its topics have a saved answer.

```typescript
// Source: design decision from CONTEXT.md, styled using existing globals.css variables
function StepPills({ categories, currentCategoryIndex, completedCategories }: Props) {
  return (
    <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "2rem" }}>
      {categories.map((cat, i) => {
        const isActive = i === currentCategoryIndex;
        const isComplete = completedCategories.has(cat.id);
        return (
          <div key={cat.id} style={{
            width: "2rem", height: "2rem",
            borderRadius: "50%",
            background: isActive ? "var(--color-navy)" : isComplete ? "var(--color-green)" : "#E5E7EB",
            color: isActive || isComplete ? "white" : "var(--color-text-gray)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontWeight: 700, fontSize: "0.875rem",
          }}>
            {isComplete && !isActive ? "✓" : i + 1}
          </div>
        );
      })}
    </div>
  );
}
```

### Pattern 6: Explanatory Content in Config
**What:** Optional `context_text` (string | null) and `context_image` (string | null) fields on category and topic objects in the JSON config.
**Recommendation:** Store as embedded strings in JSON (not separate markdown files). This is simplest to update and passes through the existing `/questionnaire/config` API without any backend changes.

```json
// Source: config/dsi-questionnaire-v2.json — extend existing structure
{
  "id": "scheme",
  "label": "Scheme Management",
  "context_text": null,
  "context_image": null,
  "topics": [
    {
      "id": "human_readable",
      "label": "Human Readable/Actionable",
      "context_text": "This topic asks about ...",
      "context_image": null,
      "questions": [ ... ]
    }
  ]
}
```

Display logic: if `context_text` or `context_image` is non-null, render a callout box above the questions on that topic/category page.

### Pattern 7: TanStack Router routeTree.gen.ts
**What:** The file `routeTree.gen.ts` is auto-generated by the TanStack Router Vite plugin. It must NOT be manually edited.
**How it works:** The Vite plugin (`TanStackRouterVite`) scans `src/routes/` on every `vite dev` start. Adding a new file creates a new route automatically. The commit instructions say this file IS committed to the repo.
**For Phase 4:** No new route files are needed. The wizard lives entirely inside the existing `_app/questionnaire.tsx`. Only file deletions (RJSF widget files) and modifications to existing route files.

### Anti-Patterns to Avoid
- **Using RJSF for anything in Phase 4:** RJSF is being fully removed. Do not leave any import of `@rjsf/*`.
- **Storing wizard step in URL search params:** Would add complexity without benefit; the wizard step is not bookmarkable or shareable. Use useState.
- **Putting participant_type on Initiative creation form frontend:** The initiative form (`initiative.tsx`) must NOT ask for participant_type. It comes from the user model (set at registration).
- **Using antd components for the wizard:** antd is installed but the existing wizard pattern is plain styled HTML to match the existing codebase consistency. Using antd for some components but not others creates visual inconsistency.
- **Forgetting Alembic migration for user.participant_type:** Adding the field to the SQLModel without a migration will cause a startup error in production.
- **Saving answers one-at-a-time on every keystroke for followup_other:** Debounce the free-text "Other" field (300-500ms) to avoid hammering the API while the user types.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Answer persistence with conflict handling | Custom insert-or-update logic | Existing PUT `/questionnaire/initiatives/{id}/answers/{question_id}` endpoint (PostgreSQL upsert already implemented) | The ON CONFLICT DO UPDATE is already in `questionnaire.py` |
| Server-state caching + invalidation | Custom cache | TanStack Query `useQuery` + `invalidateQueries` | Already used in questionnaire.tsx; established pattern |
| HTTP with auth headers | Custom fetch wrapper | `{ api }` from `lib/api.ts` | Interceptors handle auth token injection and 401 redirect |
| Category completion tracking | Custom DB query | Compute from `savedAnswers` array already fetched by `fetchAnswers()` | All answers are already loaded client-side |

**Key insight:** The heavy lifting (answer upsert, auth, config loading) is already done. Phase 4 is primarily a frontend rendering concern — replace RJSF with controlled React components.

---

## Common Pitfalls

### Pitfall 1: routeTree.gen.ts Conflicts
**What goes wrong:** Developer manually edits `routeTree.gen.ts` or the Vite plugin regenerates it unexpectedly, causing merge conflicts.
**Why it happens:** Two developers modifying route files simultaneously, or a vite restart after adding/removing a file.
**How to avoid:** Never manually edit `routeTree.gen.ts`. Only add/remove files in `src/routes/`. After any route file change, run `vite dev` once to regenerate, then commit the updated `routeTree.gen.ts`.
**Warning signs:** TypeScript errors in `routeTree.gen.ts` referencing files that don't exist.

### Pitfall 2: participant_type Migration Missing
**What goes wrong:** `User.participant_type` column is added to SQLModel but no Alembic migration is created. The backend starts but the column does not exist in the DB, causing `column does not exist` errors on register.
**Why it happens:** SQLModel does not auto-create columns; Alembic `--autogenerate` must be run to detect the schema diff.
**How to avoid:** Always create a migration after changing a `SQLModel(table=True)` class. Use `alembic revision --autogenerate -m "add user participant_type"`.
**Warning signs:** `psycopg2.errors.UndefinedColumn` in the backend logs.

### Pitfall 3: RJSF Residual Imports
**What goes wrong:** After uninstalling `@rjsf/*`, TypeScript compilation fails because other files still import from removed packages.
**Why it happens:** The files `QuestionnaireForm.tsx`, `NotApplicableWidget.tsx`, `ComplyExplainWidget.tsx` all import from `@rjsf/*`. The route `questionnaire.tsx` imports `QuestionnaireForm`.
**How to avoid:** Delete the three RJSF component files first, update `questionnaire.tsx` to remove their imports, then run `npm uninstall`. Build (`tsc -b && vite build`) to verify clean.
**Warning signs:** `Cannot find module '@rjsf/core'` errors after uninstall.

### Pitfall 4: Follow-up Clear Not Propagating to API
**What goes wrong:** When user switches from YES to NOT_APPLICABLE, the local state clears `followup_selections` and `followup_other`, but the save to the API happens before the state update resolves, so the old follow-up data persists in the DB.
**Why it happens:** React state updates are async; saving immediately after `setState` reads stale state.
**How to avoid:** Use the new value directly in the save call rather than reading from state:
```typescript
function handleAnswerChange(questionId: string, newValue: AnswerValue) {
  const followupSelections = newValue === "NOT_APPLICABLE" ? null : localAnswers[questionId]?.followup_selections;
  const followupOther = newValue === "NOT_APPLICABLE" ? null : localAnswers[questionId]?.followup_other;
  // save with explicit new values, not state
  saveAnswer({ answerValue: newValue, followupSelections, followupOther });
  setLocalAnswers(prev => ({
    ...prev,
    [questionId]: { answer_value: newValue, followup_selections: followupSelections, followup_other: followupOther }
  }));
}
```
**Warning signs:** Follow-up data visible in DB after user selected NOT_APPLICABLE.

### Pitfall 5: Initiative Creation Breaks When participant_type Removed from Body
**What goes wrong:** The frontend `initiative.tsx` currently has a form that doesn't include `participant_type` in the POST body. After the backend change, `InitiativeCreate` no longer accepts `participant_type` from the request (it reads from user). This is correct — but any existing code that sends `participant_type` in the initiative create body must be updated.
**How to avoid:** Remove `participant_type` from `InitiativeCreate` schema on the backend, and ensure `InitiativeCreate` does not include it. Update initiative creation to always use `current_user.participant_type`.
**Warning signs:** `422 Unprocessable Entity` on initiative creation if old schema expected `participant_type` in body.

### Pitfall 6: "Forward blocked until complete" — What Does Complete Mean?
**What goes wrong:** Planner interprets "category complete" loosely. If "complete" means "at least one answer per required question", the completion check must only count questions where `required: true`.
**How to avoid:** A category is considered complete when every question with `required: true` across all its topics has a saved `answer_value` (any of YES/NOT_THERE_YET/NOT_APPLICABLE). Optional questions do not block progress.
**Warning signs:** Users can't advance despite having answered everything visible.

### Pitfall 7: antd 6.x Installed but Unused
**What goes wrong:** antd is in package.json but not imported anywhere in the current codebase. If Phase 4 adds antd imports for convenience, it bloats the bundle and creates a styling clash with the existing pure CSS approach.
**How to avoid:** Do not use antd components in Phase 4. The wizard uses the existing plain-styled button/div approach matching the rest of the app.
**Warning signs:** Unexplained CSS conflicts or `antd` in bundle analysis.

---

## Code Examples

### Complete TypeScript Types for Wizard (update lib/questionnaire.ts)
```typescript
// Source: derived from config/dsi-questionnaire-v2.json structure (verified by reading file)

export type AnswerValue = "YES" | "NOT_THERE_YET" | "NOT_APPLICABLE";

export interface Followup {
  trigger: AnswerValue[];
  prompt: string;
  options: string[];
  allow_other: boolean;
}

export interface Question {
  id: string;
  mami_code: string;
  text: string;
  answer_type: "yes_notyet_na";
  required: boolean;
  has_evidence: boolean;
  followup?: Followup;
}

export interface Topic {
  id: string;
  label: string;
  mami_dimension: string;
  context_text?: string | null;     // NEW: admin explanatory content
  context_image?: string | null;    // NEW: admin explanatory image URL/path
  questions: Question[];
}

export interface Category {
  id: string;
  label: string;
  context_text?: string | null;     // NEW: admin explanatory content
  context_image?: string | null;    // NEW: admin explanatory image URL/path
  topics: Topic[];
}

export interface QuestionnaireConfig {
  version: string;
  participant_type: "DSI" | "SP";
  categories: Category[];
}

// Local answer state for wizard (before save)
export interface LocalAnswer {
  answer_value: AnswerValue;
  followup_selections: string[] | null;
  followup_other: string | null;
}

// Updated API payload (replaces old AnswerPayload)
export interface AnswerPayload {
  question_id: string;
  mami_code: string;
  questionnaire_version: string;
  answer_value: AnswerValue;
  followup_selections?: string[] | null;
  followup_other?: string | null;
}
```

### DSI/SP Radio in Register Form
```typescript
// Source: design decision + existing register.tsx pattern
// Add to RegisterPage state and form:

const [participantType, setParticipantType] = useState<"DSI" | "SP">("DSI");

// In form body before submit button:
<div style={{ marginBottom: "1rem" }}>
  <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.375rem", color: "var(--color-navy)" }}>
    I am a:
  </label>
  <div style={{ display: "flex", gap: "0.75rem" }}>
    {(["DSI", "SP"] as const).map(type => (
      <button
        key={type}
        type="button"
        onClick={() => setParticipantType(type)}
        style={{
          flex: 1,
          padding: "0.75rem",
          border: `2px solid ${participantType === type ? "var(--color-green)" : "#D1D5DB"}`,
          background: participantType === type ? "var(--color-green)" : "white",
          color: participantType === type ? "white" : "var(--color-text-gray)",
          borderRadius: "var(--border-radius-sm)",
          fontWeight: 600,
          cursor: "pointer",
        }}
      >
        {type === "DSI" ? "DSI — Data Space Initiator" : "SP — Service Provider"}
      </button>
    ))}
  </div>
</div>

// Updated fetch body:
body: JSON.stringify({ email, password, participant_type: participantType }),
```

### Category Completion Check
```typescript
// Source: derived from config structure and CONTEXT.md definition of "complete"
function isCategoryComplete(
  category: Category,
  savedAnswers: Map<string, AnswerValue>
): boolean {
  const requiredIds = category.topics
    .flatMap(t => t.questions)
    .filter(q => q.required)
    .map(q => q.id);
  return requiredIds.every(id => savedAnswers.has(id));
}

// Build Map from API answers for efficient lookup:
const savedAnswerMap = useMemo(() => {
  const map = new Map<string, AnswerValue>();
  savedAnswers.forEach(a => map.set(a.question_id, a.answer_value as AnswerValue));
  return map;
}, [savedAnswers]);
```

### Inline Follow-up Expand
```typescript
// Source: CONTEXT.md design decision — inline expand, no navigation
// The follow-up section is conditionally rendered within the question card
function QuestionCard({ question, answer, onAnswerChange }: Props) {
  const showFollowup = answer?.answer_value === "YES" || answer?.answer_value === "NOT_THERE_YET";

  return (
    <div style={{ background: "white", borderRadius: "var(--border-radius-sm)", padding: "1.5rem", boxShadow: "0 1px 3px rgba(0,0,0,0.08)", marginBottom: "1rem" }}>
      <p style={{ fontWeight: 600, color: "var(--color-navy)", marginBottom: "1rem" }}>{question.text}</p>
      <AnswerButtonGroup value={answer?.answer_value ?? null} onChange={v => onAnswerChange(question.id, v)} />

      {showFollowup && question.followup && (
        <div style={{ marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid #E5E7EB" }}>
          <p style={{ fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.75rem", color: "var(--color-navy)" }}>
            {question.followup.prompt}
          </p>
          {/* Multi-select checkboxes — always shown */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "0.75rem" }}>
            {question.followup.options.map(opt => (
              <label key={opt} style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={answer?.followup_selections?.includes(opt) ?? false}
                  onChange={e => onFollowupSelectionChange(question.id, opt, e.target.checked)}
                />
                <span style={{ fontSize: "0.875rem" }}>{opt}</span>
              </label>
            ))}
          </div>
          {/* Free-text "Other" — always shown */}
          <input
            type="text"
            placeholder="Other (describe)..."
            value={answer?.followup_other ?? ""}
            onChange={e => onFollowupOtherChange(question.id, e.target.value)}
            style={{ width: "100%", padding: "0.5rem 0.75rem", border: "1px solid #D1D5DB", borderRadius: "var(--border-radius-sm)", fontSize: "0.875rem" }}
          />
        </div>
      )}
    </div>
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| RJSF schema-driven form | Custom React button group wizard | Direct control over UX; no JSON Schema overhead |
| `answer_type: "yes_no" / "yes_no_explain" / "not_applicable_allowed"` in Question type | `answer_type: "yes_notyet_na"` (v2 config) | Frontend types must be updated to match v2 config |
| Old answer values: `YES / NO / COMPLY_EXPLAIN / NOT_APPLICABLE` | New: `YES / NOT_THERE_YET / NOT_APPLICABLE` | Backend AnswerValue enum already updated in Phase 3.1 |
| All dimensions shown at once per category (tab UI) | One topic per page per category (wizard) | Better UX; requires rewrite of questionnaire route |
| No follow-up UX | Inline expand with multi-select + Other | Phase 3.1 added DB columns; Phase 4 adds the UI |
| participant_type on Initiative (set at creation) | participant_type on User (set at registration) | Initiative creation simplifies; register form grows |

**Deprecated/outdated from this codebase:**
- `QuestionnaireForm.tsx` (RJSF-based): Deleted in Phase 4
- `NotApplicableWidget.tsx`: Deleted in Phase 4
- `ComplyExplainWidget.tsx`: Deleted in Phase 4
- `questionnaire.ts` fields `answer_type: "yes_no" | "yes_no_explain" | "not_applicable_allowed"` and `AnswerPayload.answer_value: "YES" | "NO" | "COMPLY_EXPLAIN"`: Updated to v2 values

---

## Key Implementation Details

### What the config structure actually looks like (verified from file)
The v2 config uses `topics` (not `dimensions` as in the old TypeScript type). The `questionnaire.ts` lib currently has `dimensions: Dimension[]` — this is the OLD type that predates the v2 config. The v2 JSON uses `topics`. The TypeScript types must be updated to match.

Current lib type (WRONG for v2):
```typescript
export interface Category { id: string; label: string; dimensions: Dimension[]; }
```

Correct v2 type:
```typescript
export interface Category { id: string; label: string; topics: Topic[]; }
```

This mismatch is an important finding: the current `questionnaire.tsx` route iterates `cat.dimensions` which doesn't exist in the v2 config. The wizard rewrite will fix this naturally.

### Number of categories/topics in DSI config
- Category 1: "Scheme Management" — 3 topics (human_readable, machine_readable, trust_anchors)
- Category 2: "Participants" — 3 topics
- Category 3: "Data" — 3 topics
- Category 4: (not read fully but assumed 3 topics per CONTEXT.md "1 → 2 → 3 → 4" pills)

The step pills are `1 → 2 → 3 → 4` per CONTEXT.md — confirming 4 categories.

### Backend: initiative.tsx currently does NOT include participant_type in the create body
Looking at `initiative.tsx` lines 87-97: the create body only sends `name, description, sector, sector_other, contact_name, contact_email, organization`. But `InitiativeCreate` schema requires `participant_type`. This means the current initiative creation is actually broken (returns 422) unless participant_type has a default. The model has `default=ParticipantType.dsi` — so it works because the Pydantic schema also needs to have a default or it's optional. Checking `schemas/initiative.py` line 15: `participant_type: ParticipantType` — no default. This means initiative creation currently requires `participant_type` in the body, but the frontend doesn't send it. This is a pre-existing bug that Phase 4 resolves by moving participant_type to the user model.

**Implication for Phase 4:** The initiative creation endpoint must be updated to NOT require `participant_type` in the body; instead it reads from `current_user.participant_type`. The `InitiativeCreate` schema should remove `participant_type` or make it optional with backend override.

---

## Open Questions

1. **How many categories does the SP config have?**
   - What we know: DSI has 4 categories (inferred from step pill count "1 → 2 → 3 → 4" in CONTEXT.md). The SP config exists (`sp-questionnaire-v2.json`) but was not read.
   - What's unclear: Whether SP also has 4 categories with the same or different topics.
   - Recommendation: Planner should treat the wizard as config-driven (N categories, N topics each) — hardcoding 4 is wrong. The step pills should render `config.categories.length` pills dynamically.

2. **Debounce for followup_other auto-save**
   - What we know: The current answer save is triggered immediately on change. For free-text fields, this would fire on every keystroke.
   - What's unclear: Should followup_other save on blur (when user leaves the field) or on debounce (300ms after last keystroke)?
   - Recommendation: Save on navigation (Next/Back button click) rather than on every change. Local state holds the value; save happens on topic transition. This avoids debounce complexity and is consistent with the "save on navigate" pattern.

3. **Image display for context_image in config**
   - What we know: `context_image` is a string field in the config. The CONTEXT.md says "text + images" for explanatory content.
   - What's unclear: Is `context_image` a URL (to a remote image), a relative path (served from the backend), or a base64 data URI?
   - Recommendation: Use a relative URL (e.g., `/static/context/category-scheme.png`) served by the backend's static files or a CDN. The planner should define where static images are served from. For Phase 4, if no actual images exist yet, `context_image: null` everywhere is fine — the display component just renders nothing when null.

---

## Sources

### Primary (HIGH confidence)
- Direct code reading: `frontend/src/routes/_app/questionnaire.tsx` — current questionnaire page structure
- Direct code reading: `frontend/src/components/questionnaire/QuestionnaireForm.tsx` — RJSF usage to remove
- Direct code reading: `backend/app/models/user.py` — User model (no participant_type yet)
- Direct code reading: `backend/app/models/initiative.py` — ParticipantType enum, Initiative model
- Direct code reading: `backend/app/models/questionnaire.py` — AnswerValue enum, QuestionnaireAnswer model with followup fields
- Direct code reading: `backend/app/api/v1/auth.py` — register endpoint structure
- Direct code reading: `backend/app/api/v1/questionnaire.py` — upsert answer endpoint
- Direct code reading: `backend/app/api/v1/initiatives.py` — create initiative endpoint
- Direct code reading: `backend/app/schemas/auth.py` — UserCreate (email + password only, no participant_type)
- Direct code reading: `backend/app/schemas/initiative.py` — InitiativeCreate requires participant_type in body
- Direct code reading: `config/dsi-questionnaire-v2.json` — v2 config structure (categories → topics → questions)
- Direct code reading: `frontend/package.json` — installed versions confirmed
- Direct code reading: `frontend/src/routeTree.gen.ts` — route tree structure
- Direct code reading: `frontend/src/styles/globals.css` — CSS variables (--color-navy, --color-green, etc.)
- Direct code reading: `frontend/vite.config.ts` — TanStack Router Vite plugin configuration
- Direct code reading: `frontend/src/lib/questionnaire.ts` — CURRENT TypeScript types (uses `dimensions`, needs update to `topics`)

### Secondary (MEDIUM confidence)
- TanStack Router 1.160.0 file-based routing: behavior verified from installed package version and existing routeTree.gen.ts output
- SQLModel + Alembic migration pattern: inferred from Phase 3.1 prior work (migration added followup columns)

### Tertiary (LOW confidence)
- antd 6.3.0 behavior: installed but not used; advice to avoid it is based on visual consistency reasoning, not antd docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions confirmed from package.json and node_modules
- Current codebase state: HIGH — all files read directly
- Architecture patterns: HIGH — derived from actual code, not assumptions
- Wizard state machine: HIGH — derived from CONTEXT.md decisions + existing code patterns
- Pitfalls: HIGH — identified from actual code inconsistencies (e.g., dimensions vs topics mismatch, participant_type bug)
- Explanatory content storage: HIGH — CONTEXT.md explicitly chose JSON config fields

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable project — 30 days)
