# Phase 2: Questionnaire and Scoring - Research

**Researched:** 2026-02-15
**Domain:** Config-driven questionnaire storage + ZEN Engine scoring + RJSF form rendering
**Confidence:** MEDIUM-HIGH (ZEN Engine Python API verified via official docs + GitHub; RJSF verified via npm/GitHub; answer storage pattern is standard SQL; JDM format verified via source JSON)

---

## Summary

Phase 2 delivers the domain core of the MAMI Compliance Checker: a config-driven questionnaire where answers are stored per-question with version stamping, and a scoring engine that produces CRITICAL/NON_CRITICAL findings. The phase splits cleanly into three plans matching the roadmap: (1) MAMI framework config loader, (2) questionnaire engine with answer storage, and (3) GoRules ZEN Engine scoring.

The GoRules ZEN Engine Python SDK (`zen-engine` v0.51.0, released January 2026) is well-documented and straightforward to integrate. The key API surface is small: `ZenEngine()` singleton, `create_decision(json_str)` for direct loading, `engine.evaluate(key, input)` with a custom loader, and `async_evaluate` for non-blocking calls. The Python SDK is released under Rust bindings; it is production-ready but the project explicitly states "we can't accept code contributions" — meaning it is a maintained external dependency, not community-extendable.

RJSF v6.3.1 (released February 12, 2026) requires `react >= 18` and is confirmed compatible with React 19.2.0 (the project's current version). `@gorules/jdm-editor` v1.51.2 (February 2026) also requires `react >= 18` and introduces Ant Design v5 as a dependency — this must be installed in the frontend. The questionnaire answer storage uses a row-per-question pattern that supports partial saves and version stamping without requiring the full form to be complete before saving.

**Primary recommendation:** Build the MAMI config as a Python dict loaded from a JSON file at startup; store answers as one DB row per question per initiative (not a single JSONB blob); integrate ZEN Engine via the FastAPI lifespan pattern as a singleton initialized once; use RJSF (without jdm-editor in Phase 2 — the visual editor is an admin feature for later) to render the questionnaire form in React.

---

## Standard Stack

### Core (Backend additions for Phase 2)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| zen-engine | 0.51.0 | GoRules ZEN Engine — evaluates JDM decision files | Only open-source Python rule engine with matching visual editor; sub-millisecond Rust evaluation; JDM files stored as JSON |
| pyyaml | >=6.0 | YAML config loader (for questionnaire config file) | Standard Python YAML parser; needed if questionnaire config is YAML |

**Note:** `zen-engine` must be added to `pyproject.toml`. All other backend dependencies (FastAPI, SQLModel, Alembic) are already installed from Phase 1.

### Core (Frontend additions for Phase 2)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @rjsf/core | 6.3.1 | JSON Schema form renderer — renders the MAMI questionnaire from config | Config-driven; renders from JSON Schema; handles NOT_APPLICABLE via custom widgets |
| @rjsf/utils | 6.3.1 | Required RJSF companion utilities | Peer dependency of @rjsf/core |
| @rjsf/validator-ajv8 | 6.3.1 | JSON Schema validation (ajv8 current; ajv6 deprecated) | Required for form validation |
| antd | ^5.0.0 | Ant Design UI library | Required transitive peer of @gorules/jdm-editor; do NOT skip even if jdm-editor is Phase 3+ |

**Note on Ant Design:** `@gorules/jdm-editor` v1.51.2 bundles Ant Design v5 as a dependency. Even if jdm-editor is used only in admin pages, antd ships with the bundle and affects styling. Plan for CSS isolation — RJSF's default theme may conflict with antd globals. Use RJSF without an antd theme (`@rjsf/core` headless) and style it manually using existing CSS variables.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| RJSF (@rjsf/core) | Plain react-hook-form | react-hook-form has no config-driven JSON Schema rendering; RJSF is correct for QUES-06 |
| RJSF (@rjsf/core) | SurveyJS Form Library | SurveyJS Creator (the admin editor) requires paid license; RJSF is fully Apache 2.0 |
| zen-engine | Hand-rolled MoSCoW if/else | Hand-rolled breaks SCOR-02 (per-recommendation override in config); ZEN handles it declaratively |
| Row-per-question answer storage | JSONB blob per initiative | JSONB blob cannot record per-question questionnaire_version; row-per-question supports partial save/resume natively |

### Backend Installation
```bash
cd backend
uv add "zen-engine==0.51.0" "pyyaml>=6.0"
```

### Frontend Installation
```bash
cd frontend
npm install @rjsf/core @rjsf/utils @rjsf/validator-ajv8
# antd is pulled in by @gorules/jdm-editor (used in Phase 3+)
# Install now to avoid version conflicts later:
npm install antd
```

---

## Architecture Patterns

### Recommended Project Structure (Phase 2 additions)
```
backend/
├── app/
│   ├── models/
│   │   ├── questionnaire.py       # QuestionnaireAnswer table model
│   │   └── (user.py, initiative.py already exist)
│   ├── schemas/
│   │   └── questionnaire.py       # AnswerCreate, AnswerRead, FindingRead schemas
│   ├── api/v1/
│   │   ├── questionnaire.py       # GET /questionnaire, POST/PATCH /answers endpoints
│   │   └── scoring.py             # POST /initiatives/{id}/score endpoint
│   ├── services/
│   │   ├── mami_config.py         # MAMI framework config loader (singleton)
│   │   └── scoring_engine.py      # ZEN Engine wrapper (singleton via app.state)
│   └── core/
│       └── lifespan.py            # FastAPI lifespan startup: load config + ZEN engine
│
config/
├── mami-framework.json            # MAMI codes: id, category, dimension, moscow_level
├── questionnaire-v1.json          # Questionnaire structure: questions mapped to MAMI codes
└── scoring/
    └── mami-scoring.json          # JDM decision file for MoSCoW scoring rules

frontend/
├── src/
│   ├── routes/_app/
│   │   └── questionnaire.tsx      # Questionnaire page (RJSF form, category/dimension tabs)
│   ├── components/questionnaire/
│   │   ├── QuestionnaireForm.tsx  # RJSF wrapper with custom widgets
│   │   ├── NotApplicableWidget.tsx # Custom widget for NOT_APPLICABLE toggle
│   │   └── ComplyExplainWidget.tsx # Custom widget for comply-or-explain + rationale
│   └── lib/
│       └── questionnaire.ts       # API calls: load answers, save answer, trigger scoring
```

### Pattern 1: MAMI Framework Config File Structure (JSON)

**What:** Single JSON file defines all MAMI codes, their category, dimension, and MoSCoW level. Loaded once at startup and cached in `app.state`. No MAMI code is hardcoded in Python logic.

**When to use:** This is the source of truth for all MAMI code references.

```json
// config/mami-framework.json
{
  "version": "1.0",
  "high_level": [
    {"id": "H-HRA-0", "category": "cross-cutting", "dimension": "human_readable", "moscow_level": "MUST", "description": "..."},
    {"id": "H-MRA-0", "category": "cross-cutting", "dimension": "machine_readable", "moscow_level": "MUST", "description": "..."},
    {"id": "H-TA-0",  "category": "cross-cutting", "dimension": "trust_anchors",   "moscow_level": "MUST", "description": "..."}
  ],
  "codes": [
    {"id": "S-HRA-1.1",  "category": "scheme",        "dimension": "human_readable",   "moscow_level": "MUST",   "critical_override": null, "description": "..."},
    {"id": "S-HRA-1.2",  "category": "scheme",        "dimension": "human_readable",   "moscow_level": "SHOULD", "critical_override": null, "description": "..."},
    {"id": "S-MRA-1.1",  "category": "scheme",        "dimension": "machine_readable", "moscow_level": "MUST",   "critical_override": null, "description": "..."},
    {"id": "PP-HRA-2.1", "category": "participants",   "dimension": "human_readable",   "moscow_level": "MUST",   "critical_override": null, "description": "..."},
    {"id": "D-HRA-3.1",  "category": "data",          "dimension": "human_readable",   "moscow_level": "MUST",   "critical_override": null, "description": "..."},
    {"id": "SER-HRA-4.1","category": "services",      "dimension": "human_readable",   "moscow_level": "MUST",   "critical_override": true, "description": "..."}
  ]
}
```

**Key field:** `critical_override` — `null` means "use default" (MUST = CRITICAL, others = NON_CRITICAL); `true` forces CRITICAL; `false` forces NON_CRITICAL. This satisfies SCOR-02.

### Pattern 2: Questionnaire Config File Structure (JSON)

**What:** Separate JSON file from the MAMI framework config. Defines questions, groups them by category/dimension, and maps each question to its MAMI code. This is the versioned questionnaire schema.

```json
// config/questionnaire-v1.json
{
  "version": "1.0",
  "$schema": "https://json-schema.org/draft/2020-12",
  "categories": [
    {
      "id": "scheme",
      "label": "Scheme Management",
      "dimensions": [
        {
          "id": "human_readable",
          "label": "Human Readable/Actionable",
          "questions": [
            {
              "id": "q_S-HRA-1.1",
              "mami_code": "S-HRA-1.1",
              "text": "Does your initiative have a publicly available governance document?",
              "answer_type": "yes_no_explain",
              "required": true
            },
            {
              "id": "q_S-HRA-1.2",
              "mami_code": "S-HRA-1.2",
              "text": "Is the governance document kept up to date (reviewed at least annually)?",
              "answer_type": "yes_no_explain",
              "required": false
            }
          ]
        }
      ]
    }
  ]
}
```

**Answer types:**
- `yes_no_explain` — Yes / No / Comply-or-explain (with rationale text field)
- `yes_no` — Simple Yes / No (no rationale)
- `not_applicable_allowed` — All of the above + NOT_APPLICABLE option

### Pattern 3: Row-Per-Question Answer Storage

**What:** One database row per (initiative, question_id). This enables partial saves and save/resume across sessions (QUES-02). Each row carries the questionnaire version it was answered against (QUES-07).

**Why not a single JSONB blob per initiative:** A JSONB blob cannot easily record per-question questionnaire versions when questions change. Row-per-question allows the scoring engine to compare answer versions and flag stale answers.

```python
# Source: Standard survey answer storage pattern
# backend/app/models/questionnaire.py

from enum import Enum
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class AnswerValue(str, Enum):
    yes = "YES"
    no = "NO"
    comply_explain = "COMPLY_EXPLAIN"
    not_applicable = "NOT_APPLICABLE"

class QuestionnaireAnswer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    initiative_id: int = Field(foreign_key="initiative.id", index=True)
    question_id: str = Field(index=True)          # e.g. "q_S-HRA-1.1"
    mami_code: str = Field(index=True)             # e.g. "S-HRA-1.1" (denormalized for query speed)
    questionnaire_version: str                     # e.g. "1.0" — QUES-07
    answer_value: AnswerValue
    rationale: Optional[str] = None               # Required when answer_value = COMPLY_EXPLAIN
    answered_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        # DB unique constraint: one answer per (initiative_id, question_id)
        # Use a UniqueConstraint in the migration, not sa_column here
        pass
```

**DB unique constraint:** Add `UniqueConstraint("initiative_id", "question_id")` in the Alembic migration to enforce one-answer-per-question-per-initiative at the DB level.

### Pattern 4: GoRules ZEN Engine — FastAPI Lifespan Singleton

**What:** The ZEN Engine is expensive to initialize (Rust native). Initialize once at application startup using FastAPI's lifespan pattern. Store in `app.state`. Access via a FastAPI dependency.

```python
# Source: FastAPI official docs + GoRules Python README
# backend/app/services/scoring_engine.py

import json
import zen
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config" / "scoring"

def create_scoring_engine() -> zen.ZenEngine:
    """Create ZEN engine with a file-system loader from config/scoring/"""
    def loader(key: str) -> str:
        path = CONFIG_DIR / key
        return path.read_text()

    return zen.ZenEngine({"loader": loader})

async def score_initiative(
    engine: zen.ZenEngine,
    answers: list[dict],
    mami_config: dict,
) -> list[dict]:
    """
    Input structure for JDM:
    {
      "answers": [
        {"mami_code": "S-HRA-1.1", "moscow_level": "MUST", "answer_value": "YES",
         "critical_override": null},
        ...
      ]
    }
    Returns: {"findings": [{"mami_code": "S-HRA-1.1", "severity": "CRITICAL", ...}, ...]}
    """
    try:
        result = engine.evaluate("mami-scoring.json", {"answers": answers})
        return result["result"]["findings"]
    except Exception as e:
        raise ValueError(f"Scoring evaluation failed: {e}") from e
```

```python
# Source: FastAPI official docs https://fastapi.tiangolo.com/advanced/events/
# backend/app/main.py — lifespan startup

from contextlib import asynccontextmanager
import json
from pathlib import Path
import zen
from fastapi import FastAPI
from app.services.scoring_engine import create_scoring_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load MAMI config at startup
    config_path = Path("config/mami-framework.json")
    app.state.mami_config = json.loads(config_path.read_text())

    # Load questionnaire config at startup
    q_path = Path("config/questionnaire-v1.json")
    app.state.questionnaire_config = json.loads(q_path.read_text())

    # Initialize ZEN Engine singleton
    app.state.zen_engine = create_scoring_engine()

    yield  # app runs here

    # Shutdown cleanup (nothing needed for ZEN)

app = FastAPI(lifespan=lifespan, ...)
```

```python
# backend/app/core/deps.py — ZEN engine dependency
from fastapi import Depends, Request
import zen

def get_zen_engine(request: Request) -> zen.ZenEngine:
    return request.app.state.zen_engine

def get_mami_config(request: Request) -> dict:
    return request.app.state.mami_config

def get_questionnaire_config(request: Request) -> dict:
    return request.app.state.questionnaire_config
```

### Pattern 5: JDM Decision File for MoSCoW Scoring

**What:** A JSON Decision Model file stored in `config/scoring/mami-scoring.json`. The engine receives all answers as an input array and outputs a findings array. Each row in the decision table maps (moscow_level, answer_value, critical_override) to a (severity, status) output.

**JDM format verified from official GoRules test data:**

```json
// config/scoring/mami-scoring.json
// Simplified example — full version will have one row per (moscow_level, answer_value) combination
{
  "nodes": [
    {
      "id": "input-node",
      "type": "inputNode",
      "position": {"x": 50, "y": 200},
      "name": "Answers"
    },
    {
      "id": "scoring-table",
      "type": "decisionTableNode",
      "position": {"x": 350, "y": 200},
      "name": "MoSCoW Scoring",
      "content": {
        "hitPolicy": "collect",
        "inputs": [
          {"field": "answers[].moscow_level",  "id": "col_moscow",   "name": "MoSCoW Level",    "type": "expression"},
          {"field": "answers[].answer_value",  "id": "col_answer",   "name": "Answer",           "type": "expression"},
          {"field": "answers[].critical_override", "id": "col_crit", "name": "Critical Override","type": "expression"}
        ],
        "outputs": [
          {"field": "findings[].mami_code",  "id": "out_code",     "name": "MAMI Code",   "type": "expression"},
          {"field": "findings[].severity",   "id": "out_severity", "name": "Severity",    "type": "expression"},
          {"field": "findings[].status",     "id": "out_status",   "name": "Status",      "type": "expression"}
        ],
        "rules": [
          {"_id": "r1", "col_moscow": "\"MUST\"",   "col_answer": "\"NO\"",            "col_crit": "",      "out_code": "answers[].mami_code", "out_severity": "\"CRITICAL\"",     "out_status": "\"FINDING\""},
          {"_id": "r2", "col_moscow": "\"MUST\"",   "col_answer": "\"COMPLY_EXPLAIN\"","col_crit": "",      "out_code": "answers[].mami_code", "out_severity": "\"CRITICAL\"",     "out_status": "\"FINDING\""},
          {"_id": "r3", "col_moscow": "\"MUST\"",   "col_answer": "\"NO\"",            "col_crit": "false", "out_code": "answers[].mami_code", "out_severity": "\"NON_CRITICAL\"", "out_status": "\"FINDING\""},
          {"_id": "r4", "col_moscow": "\"SHOULD\"", "col_answer": "\"NO\"",            "col_crit": "",      "out_code": "answers[].mami_code", "out_severity": "\"NON_CRITICAL\"", "out_status": "\"FINDING\""},
          {"_id": "r5", "col_moscow": "",           "col_answer": "\"YES\"",           "col_crit": "",      "out_code": "",                    "out_severity": "",                 "out_status": "\"COMPLIANT\""},
          {"_id": "r6", "col_moscow": "",           "col_answer": "\"NOT_APPLICABLE\"","col_crit": "",      "out_code": "",                    "out_severity": "",                 "out_status": "\"NOT_APPLICABLE\""}
        ]
      }
    },
    {
      "id": "output-node",
      "type": "outputNode",
      "position": {"x": 650, "y": 200},
      "name": "Findings"
    }
  ],
  "edges": [
    {"id": "e1", "type": "edge", "sourceId": "input-node",     "targetId": "scoring-table"},
    {"id": "e2", "type": "edge", "sourceId": "scoring-table",  "targetId": "output-node"}
  ]
}
```

**IMPORTANT — ZEN array handling:** ZEN Engine does not natively iterate over arrays in decision table inputs. The recommended approach is to pre-process answers in Python before passing to ZEN, evaluating each answer individually and collecting results, OR use ZEN's function nodes with JavaScript to iterate. For Phase 2, **pre-process in Python: loop over answers, call `engine.evaluate` per answer or batch using `asyncio.gather` with `async_evaluate`.** This is simpler than relying on ZEN's array syntax, which is not well-documented for the Python SDK.

### Pattern 6: RJSF Form Rendering with Custom Widgets

**What:** RJSF v6 renders the questionnaire from a JSON Schema. Custom widgets handle NOT_APPLICABLE toggle and comply-or-explain with rationale. The form's `onChange` handler auto-saves each answer to the backend.

```typescript
// Source: RJSF docs https://rjsf-team.github.io/react-jsonschema-form/docs/
// frontend/src/components/questionnaire/QuestionnaireForm.tsx

import Form from "@rjsf/core";
import validator from "@rjsf/validator-ajv8";
import { RJSFSchema, UiSchema } from "@rjsf/utils";
import { NotApplicableWidget } from "./NotApplicableWidget";
import { ComplyExplainWidget } from "./ComplyExplainWidget";

const customWidgets = {
  notApplicableWidget: NotApplicableWidget,
  complyExplainWidget: ComplyExplainWidget,
};

interface Props {
  schema: RJSFSchema;
  formData: Record<string, unknown>;
  onAnswerChange: (questionId: string, value: unknown) => void;
}

export function QuestionnaireForm({ schema, formData, onAnswerChange }: Props) {
  const uiSchema: UiSchema = {
    // Per-question widget overrides come from server-side schema uiSchema hints
  };

  const handleChange = ({ formData: newData }: { formData: Record<string, unknown> }) => {
    // Detect which field changed and auto-save
    Object.entries(newData).forEach(([questionId, value]) => {
      if (value !== formData[questionId]) {
        onAnswerChange(questionId, value);
      }
    });
  };

  return (
    <Form
      schema={schema}
      uiSchema={uiSchema}
      formData={formData}
      validator={validator}
      widgets={customWidgets}
      onChange={handleChange}
      onSubmit={() => {}} // Submission is separate from auto-save
    >
      {/* Suppress default submit button — save is auto */}
      <div />
    </Form>
  );
}
```

### Anti-Patterns to Avoid

- **Scoring logic in Python if/else:** All MoSCoW → severity mapping MUST be in the JDM file. Python code only calls `engine.evaluate()` and maps results. This is the hard requirement that makes scoring config-driven (SCOR-02).
- **Storing all answers as a single JSONB blob:** Prevents per-question version tracking and makes partial saves complex. Use row-per-question.
- **Initializing ZEN Engine per request:** ZEN Engine is a Rust native library — constructing it is expensive. Always use the lifespan singleton pattern.
- **Using `@app.on_event("startup")` decorator:** This pattern is deprecated in FastAPI. Use `lifespan` context manager instead (verified from FastAPI docs 2025).
- **Rendering questionnaire structure from DB tables:** The questionnaire structure (categories, dimensions, questions) comes from the config JSON file loaded at startup. Only answers are stored in the DB. Do not mirror the questionnaire structure to DB tables.
- **Versioning the questionnaire as a new DB table per version:** Store the version as a string field on each answer row. When the questionnaire config changes, bump the `version` field in the JSON file. Old answers retain their version string. New questions start fresh.
- **RJSF with @rjsf/antd theme:** Ant Design v5 has global CSS resets that conflict with the project's custom CSS variables. Use `@rjsf/core` headless and apply brand styles manually via `className` props or uiSchema `classNames`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MoSCoW scoring logic | Python if/else with hardcoded rules | zen-engine + JDM file | Config change requires code deploy; ZEN makes rules editable without code |
| JSON Schema form rendering | Custom React form components per question | @rjsf/core + custom widgets | RJSF handles validation, error display, conditional rendering from schema |
| Per-answer validation | Custom validator in API endpoint | Pydantic schema (AnswerValue enum) + RJSF client-side | Double validation: RJSF client-side + Pydantic server-side |
| MAMI code catalog | Hardcoded dict in Python | config/mami-framework.json loaded at startup | Framework changes = JSON edit, not code change |
| Business rule evaluation | Custom expression evaluator | zen-engine with ZEN Expression Language | ZEN handles `> 10`, `in ["a", "b"]`, boolean logic — don't reimplement |
| Form auto-save | Custom debounce + diff | RJSF `onChange` + TanStack Query mutation | `onChange` fires on every field change; backend PATCH uses the UniqueConstraint upsert pattern |

**Key insight:** The combination of RJSF (form rendering from schema) + zen-engine (scoring from JDM config) + JSON config files creates a fully config-driven system where neither adding a new question nor changing a scoring rule requires a code change or redeploy.

---

## Common Pitfalls

### Pitfall 1: ZEN Engine Array Iteration Complexity
**What goes wrong:** Developer tries to pass all answers as an array to a single ZEN decision table evaluation, expecting ZEN to iterate. ZEN's array expression syntax in decision tables is not well-documented for the Python SDK and may not work as expected with `answers[].field` syntax in the Python binding.
**Why it happens:** The JDM format supports array indexing in expression language, but iterating arrays across multiple decision table rows requires careful setup.
**How to avoid:** Pre-process in Python. Loop over each answer, call `engine.evaluate("mami-scoring.json", {"answer": single_answer})` per answer, collect results. This is simpler, predictable, and avoids undocumented array syntax. Alternatively, use a ZEN function node with JavaScript to handle the iteration — but this adds a JavaScript execution dependency.
**Warning signs:** ZEN evaluation returns empty findings when answers is a non-empty array.

### Pitfall 2: RJSF and React 19 Strict Mode
**What goes wrong:** RJSF v6 may emit React warnings about legacy string refs or deprecated lifecycle methods under React 19 strict mode.
**Why it happens:** RJSF's peer dependency is `react >= 18`, which includes React 19, but internal components may use patterns being deprecated in React 19.
**How to avoid:** Disable React StrictMode in `main.tsx` if RJSF produces console errors. This is a documented workaround for third-party libraries not yet fully React 19 compliant. Re-enable when RJSF releases a 19-specific update.
**Warning signs:** Console errors about `findDOMNode` or string refs during form rendering.

### Pitfall 3: Alembic Missing QuestionnaireAnswer Model Import
**What goes wrong:** `alembic revision --autogenerate` produces an empty migration — the `questionnaire_answers` table is not created.
**Why it happens:** The new model is not imported in `backend/app/db/base.py` before `target_metadata = SQLModel.metadata` is set.
**How to avoid:** Add `from app.models.questionnaire import QuestionnaireAnswer  # noqa: F401` to `backend/app/db/base.py`. This is the same pattern as Phase 1 for the Initiative model.
**Warning signs:** Migration file contains only `pass` in `upgrade()`.

### Pitfall 4: UniqueConstraint on (initiative_id, question_id) — SQLModel Syntax
**What goes wrong:** Duplicate answer rows are created for the same question when the user edits an answer, because the upsert logic has a bug.
**Why it happens:** SQLModel's `table=True` model does not directly support `UniqueConstraint` via Field — it requires SQLAlchemy's `__table_args__`.
**How to avoid:** Add the constraint in the model class:
```python
from sqlalchemy import UniqueConstraint
class QuestionnaireAnswer(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("initiative_id", "question_id", name="uq_answer_per_question"),)
    ...
```
Then in the API endpoint, use a PostgreSQL-native upsert:
```python
from sqlalchemy.dialects.postgresql import insert as pg_insert
stmt = pg_insert(QuestionnaireAnswer).values(...)
stmt = stmt.on_conflict_do_update(
    constraint="uq_answer_per_question",
    set_={"answer_value": ..., "rationale": ..., "updated_at": ...}
)
session.exec(stmt)
```
**Warning signs:** Multiple rows with the same (initiative_id, question_id) in the DB.

### Pitfall 5: Config File Path Resolution in Docker
**What goes wrong:** `Path("config/mami-framework.json")` resolves relative to the working directory, which differs between local dev and Docker.
**Why it happens:** In Docker, the working directory is `/app` (or wherever CMD is run from). The `config/` directory must be inside the Docker image.
**How to avoid:** Use `Path(__file__).parent.parent / "config" / "mami-framework.json"` for a path relative to the Python source tree, OR copy the `config/` directory in the Dockerfile, OR make the config path an env var (`MAMI_CONFIG_DIR`).
**Warning signs:** `FileNotFoundError` on startup in Docker but not locally.

### Pitfall 6: RJSF Validator Missing from Installation
**What goes wrong:** RJSF form renders but shows no validation errors, or throws `validator is required` error.
**Why it happens:** `@rjsf/validator-ajv8` is a separate package and must be explicitly imported and passed to `<Form validator={validator}>`.
**How to avoid:** Always install `@rjsf/validator-ajv8` alongside `@rjsf/core`. Import `import validator from "@rjsf/validator-ajv8"` and pass it as the `validator` prop.
**Warning signs:** Form submits without validating required fields; or runtime error "ReferenceError: validator is not defined".

### Pitfall 7: rationale Required Only When COMPLY_EXPLAIN
**What goes wrong:** API accepts `answer_value: "COMPLY_EXPLAIN"` with `rationale: null`, violating the comply-or-explain requirement.
**Why it happens:** Pydantic model has `rationale: Optional[str] = None` without a cross-field validator.
**How to avoid:** Add a Pydantic `@model_validator(mode="after")`:
```python
from pydantic import model_validator

@model_validator(mode="after")
def rationale_required_for_comply_explain(self):
    if self.answer_value == AnswerValue.comply_explain and not self.rationale:
        raise ValueError("rationale is required when answer_value is COMPLY_EXPLAIN")
    return self
```
**Warning signs:** DB contains rows where `answer_value = 'COMPLY_EXPLAIN'` and `rationale IS NULL`.

---

## Code Examples

### ZEN Engine Complete Python Integration

```python
# Source: GoRules Python docs https://docs.gorules.io/developers/sdks/python
# + GoRules GitHub https://github.com/gorules/zen/blob/master/bindings/python/README.md

import zen
from pathlib import Path

# --- Initialization (once at startup) ---
SCORING_DIR = Path("config/scoring")

def loader(key: str) -> str:
    return (SCORING_DIR / key).read_text()

engine = zen.ZenEngine({"loader": loader})

# --- Single-answer evaluation pattern ---
def evaluate_single_answer(
    engine: zen.ZenEngine,
    mami_code: str,
    moscow_level: str,
    answer_value: str,
    critical_override: bool | None,
) -> dict:
    result = engine.evaluate("mami-scoring.json", {
        "answer": {
            "mami_code": mami_code,
            "moscow_level": moscow_level,
            "answer_value": answer_value,
            "critical_override": critical_override,
        }
    })
    return result["result"]  # {"severity": "CRITICAL", "status": "FINDING"}

# --- Batch evaluation with async ---
import asyncio

async def score_all_answers(
    engine: zen.ZenEngine,
    answers: list[dict],
) -> list[dict]:
    tasks = [
        engine.async_evaluate("mami-scoring.json", {"answer": a})
        for a in answers
    ]
    results = await asyncio.gather(*tasks)
    findings = []
    for answer, result in zip(answers, results):
        finding = result["result"]
        finding["mami_code"] = answer["mami_code"]
        if finding.get("status") == "FINDING":
            findings.append(finding)
    return findings
```

### RJSF Not-Applicable Custom Widget

```typescript
// Source: RJSF docs https://rjsf-team.github.io/react-jsonschema-form/docs/
// frontend/src/components/questionnaire/NotApplicableWidget.tsx

import { WidgetProps } from "@rjsf/utils";

export function NotApplicableWidget({ value, onChange, label }: WidgetProps) {
  const isNA = value === "NOT_APPLICABLE";

  return (
    <div className="question-widget">
      <label>{label}</label>
      <div className="answer-options">
        {["YES", "NO", "COMPLY_EXPLAIN", "NOT_APPLICABLE"].map((opt) => (
          <label key={opt} className="radio-option">
            <input
              type="radio"
              name={label}
              value={opt}
              checked={value === opt}
              onChange={() => onChange(opt)}
            />
            {opt === "COMPLY_EXPLAIN" ? "Comply or Explain" : opt.replace("_", " ")}
          </label>
        ))}
      </div>
      {value === "COMPLY_EXPLAIN" && (
        <textarea
          placeholder="Explain how you comply or why you cannot..."
          onChange={(e) => onChange({ value: "COMPLY_EXPLAIN", rationale: e.target.value })}
        />
      )}
    </div>
  );
}
```

### SQLAlchemy PostgreSQL Upsert for Answer Save

```python
# Source: SQLAlchemy docs https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#insert-on-conflict
# backend/app/api/v1/questionnaire.py

from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime

def upsert_answer(session, initiative_id: int, answer_in: AnswerCreate) -> QuestionnaireAnswer:
    stmt = pg_insert(QuestionnaireAnswer).values(
        initiative_id=initiative_id,
        question_id=answer_in.question_id,
        mami_code=answer_in.mami_code,
        questionnaire_version=answer_in.questionnaire_version,
        answer_value=answer_in.answer_value,
        rationale=answer_in.rationale,
        answered_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_answer_per_question",
        set_={
            "answer_value": stmt.excluded.answer_value,
            "rationale": stmt.excluded.rationale,
            "questionnaire_version": stmt.excluded.questionnaire_version,
            "updated_at": stmt.excluded.updated_at,
        }
    )
    session.exec(stmt)
    session.commit()
    # Fetch the upserted row to return
    return session.exec(
        select(QuestionnaireAnswer).where(
            QuestionnaireAnswer.initiative_id == initiative_id,
            QuestionnaireAnswer.question_id == answer_in.question_id
        )
    ).one()
```

### FastAPI Lifespan Pattern (verified from official docs)

```python
# Source: https://fastapi.tiangolo.com/advanced/events/
from contextlib import asynccontextmanager
from fastapi import FastAPI
import json
import zen
from pathlib import Path

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.mami_config = json.loads(
        Path("config/mami-framework.json").read_text()
    )
    app.state.questionnaire_config = json.loads(
        Path("config/questionnaire-v1.json").read_text()
    )

    def loader(key: str) -> str:
        return Path(f"config/scoring/{key}").read_text()

    app.state.zen_engine = zen.ZenEngine({"loader": loader})

    yield  # Application runs

    # Shutdown (ZEN engine has no explicit close)

app = FastAPI(lifespan=lifespan)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.95 (2023) | `on_event` deprecated; use lifespan for all startup/shutdown |
| SurveyJS Creator (commercial) | @rjsf/core + custom admin | Ongoing | SurveyJS Creator requires paid license for WYSIWYG builder — RJSF is Apache 2.0 |
| passlib for passwords | bcrypt direct (already Phase 1) | 2024 | Not relevant to Phase 2 but noted |
| Manual scoring if/else | GoRules ZEN Engine JDM files | 2024 | JDM visual editor allows non-technical admin to update rules |
| ajv6 validator for RJSF | ajv8 validator (@rjsf/validator-ajv8) | RJSF v5 | ajv6 deprecated; v8 is current |

**Deprecated/outdated for Phase 2:**
- `@app.on_event("startup")`: Deprecated in FastAPI. Do NOT use for ZEN Engine initialization.
- `@rjsf/validator-ajv6`: Deprecated. Use `@rjsf/validator-ajv8`.
- React `StrictMode` with RJSF v6: May produce warnings; document workaround.

---

## Open Questions

1. **ZEN Engine array iteration for batch scoring**
   - What we know: ZEN Engine evaluates a single input object; its array iteration syntax in decision tables is not clearly documented for the Python SDK
   - What's unclear: Whether ZEN can natively iterate over an answers array in one `evaluate()` call using the `answers[]` accessor syntax
   - Recommendation: Plan 02-03 should implement Python-side iteration (call `evaluate` once per answer) as the safe default. Optionally spike ZEN function node with JavaScript iteration as an optimization if performance requires it. LOW confidence — validate in 02-03 spike.

2. **RJSF comply-or-explain interaction model**
   - What we know: RJSF supports custom widgets; the rationale text field should appear only when "Comply or Explain" is selected
   - What's unclear: Whether to store the choice (YES/NO/COMPLY_EXPLAIN) and rationale as a single composite field or two separate fields
   - Recommendation: Store as two separate columns (`answer_value` and `rationale`) in the DB. The RJSF widget handles the UX of showing/hiding the rationale textarea. The API receives both fields. Pydantic validates that rationale is non-null when answer_value is COMPLY_EXPLAIN.

3. **Questionnaire config file format: JSON vs YAML**
   - What we know: The requirement says "JSON/YAML config file" (QUES-06); both are valid
   - What's unclear: Which to use for Phase 2
   - Recommendation: Use JSON for the MAMI framework config (machine-readable, simpler tooling) and JSON for the questionnaire config. YAML adds value only if humans frequently edit the file directly and prefer its comment support. For Phase 2 MVP, JSON is simpler and avoids a YAML parser dependency.

4. **Questionnaire UI navigation: single form vs category tabs**
   - What we know: The MAMI questionnaire has 4 categories × 3 dimensions = 12 cells, with multiple questions per cell
   - What's unclear: Whether to show all questions on one page or paginate by category
   - Recommendation: Category-level tabs (4 tabs for Scheme / Participants / Data / Services) with all dimensions visible per tab. This maps to the MAMI 4×3 structure and enables the user to see progress per category. RJSF does not have built-in wizard/multi-step; implement tabs at the React router level, not inside RJSF.

5. **Scoring endpoint timing: on-demand vs on-save**
   - What we know: Scoring is relatively fast (sub-millisecond per answer with ZEN Engine); there are ~15-20 MAMI questions total
   - What's unclear: Whether to score on every answer save (expensive but always fresh) or on explicit request
   - Recommendation: Score on explicit request via `POST /initiatives/{id}/score`. Store the result in a `scoring_result` JSON column on the initiative row (or a separate table). This separates QUES-02 (auto-save answers) from SCOR-01 (scoring). Scoring happens when user clicks "See Score" or "Generate Report".

---

## Sources

### Primary (HIGH confidence)
- https://github.com/gorules/zen/blob/master/bindings/python/README.md — Python API, loader pattern, sync/async usage
- https://pypi.org/project/zen-engine/ — Current version 0.51.0 (January 19, 2026 release)
- https://github.com/gorules/zen/blob/master/test-data/table.json — JDM JSON format verified from source
- https://github.com/gorules/zen/blob/master/test-data/credit-analysis.json — Multi-node JDM format verified
- https://github.com/rjsf-team/react-jsonschema-form/blob/main/packages/core/package.json — peerDependencies: `react >= 18`
- https://github.com/gorules/jdm-editor/blob/master/package.json — peerDependencies: `react >= 18`, version 1.51.2
- https://fastapi.tiangolo.com/advanced/events/ — Lifespan pattern for startup singletons (confirmed 2025)

### Secondary (MEDIUM confidence)
- https://docs.gorules.io/developers/sdks/python — async_evaluate API, tracing, expression utilities
- https://github.com/rjsf-team/react-jsonschema-form — v6.3.1 released February 12, 2026; 10 UI themes
- https://github.com/fastapi/sqlmodel/discussions/1105 — JSONB column in SQLModel using `sa_column=Column(JSONB)`
- https://docs.gorules.io/reference/json-decision-model-jdm — JDM structure: nodes, edges, metadata (sections verified)
- Red Gate survey DB design — row-per-answer pattern for questionnaire systems

### Tertiary (LOW confidence — needs validation)
- ZEN array iteration behavior in Python SDK — no official documentation found; LOW confidence on behavior
- RJSF React 19 compatibility beyond peer dep declaration — `>=18` covers 19 per semver, but no explicit test confirmation found

---

## Metadata

**Confidence breakdown:**
- zen-engine Python API (ZenEngine class, evaluate, loader): HIGH — verified from official GitHub README and PyPI
- JDM JSON format structure: HIGH — verified from source test-data files in gorules/zen repo
- RJSF v6.3.1 peer deps (react >= 18): HIGH — verified from GitHub package.json
- @gorules/jdm-editor v1.51.2 peer deps (react >= 18, antd v5): HIGH — verified from GitHub package.json
- Row-per-question answer storage pattern: HIGH — standard database design, multiple sources
- FastAPI lifespan singleton pattern: HIGH — verified from official FastAPI docs
- PostgreSQL upsert via sqlalchemy pg_insert: MEDIUM — verified from SQLAlchemy docs; SQLModel wrapper compatibility needs testing
- ZEN array iteration in Python: LOW — no official documentation; Python spike recommended before 02-03 plan

**Research date:** 2026-02-15
**Valid until:** 2026-03-15 (30 days — zen-engine and RJSF are stable; GoRules has been releasing frequently so check version on implementation day)
