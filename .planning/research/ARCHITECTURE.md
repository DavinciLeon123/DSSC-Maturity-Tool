# Architecture Research

**Domain:** Config-driven compliance assessment tool (MAMI Checker)
**Researched:** 2026-02-14
**Confidence:** MEDIUM-HIGH

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  User UI     │  │  Admin UI    │  │  Dashboard/Reports   │  │
│  │ (SPA / SSR)  │  │ (SPA / SSR)  │  │ (embedded widget)    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼────────────────────-┼──────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  REST API (Express/FastAPI)  ·  OpenAPI spec             │   │
│  │  Auth middleware (JWT)  ·  RBAC middleware               │   │
│  │  Rate limiter  ·  Request validation  ·  Audit logger    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Domain Service Layer                        │
│  ┌───────────┐  ┌───────────┐  ┌────────────┐  ┌────────────┐  │
│  │ Auth /    │  │  Quest-   │  │  Rule      │  │  Report    │  │
│  │ User Svc  │  │  ionnaire │  │  Engine    │  │  Generator │  │
│  │           │  │  Engine   │  │  Svc       │  │  Svc       │  │
│  └───────────┘  └─────┬─────┘  └─────┬──────┘  └─────┬──────┘  │
│  ┌───────────┐        │               │               │         │
│  │ MAMI      │        │               │               │         │
│  │ Framework │◄───────┴───────────────┴───────────────┘         │
│  │ Svc       │                                                   │
│  └───────────┘                                                   │
│  ┌───────────┐  ┌───────────┐                                   │
│  │ URL Check │  │  Admin    │                                    │
│  │ Worker    │  │  Svc      │                                    │
│  └───────────┘  └───────────┘                                   │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Relational  │  │  Config      │  │  Job Queue           │  │
│  │  DB          │  │  Files       │  │  (in-memory / Redis) │  │
│  │  (Postgres)  │  │  (JSON/YAML) │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| MAMI Framework Service | Owns the MAMI 4x3 matrix: codes, categories, dimensions, MoSCoW levels. Single source of truth for the standard. | JSON config file loaded at startup; read-only API endpoints |
| Questionnaire Engine | Renders and persists questionnaires. Maps user answers to MAMI codes. Handles versioning, NOT_APPLICABLE, comply-or-explain. | JSON schema per version; SurveyJS as visual builder; answers stored in DB |
| Rule Engine Service | Evaluates scoring logic against answered questionnaire. Produces CRITICAL/NON_CRITICAL findings. Runs cross-checks. | GoRules ZEN engine embedded; JDM config files; visual editor in admin UI |
| URL Check Subsystem | Consent-gated HTTP probe jobs. Checks status, keywords, snapshots hash+timestamp. Queue-backed, rate-limited. | Async job queue (Bull/pg-boss); separate worker process |
| Report Generator | Assembles findings from rule engine + URL checks into HTML report. Per-code rationale, evidence, next steps, matrix overview. | Template engine (Handlebars/Jinja2); renders stored report snapshot |
| Dashboard Module | Admin heatmaps, initiative analytics, aggregations. User compliance overview. | Embedded open-source viz (Apache ECharts or Metabase) |
| Auth / User Service | Registration, login, JWT issuance, session management. RBAC enforcement (USER/ADMIN roles). | bcrypt passwords; JWT access tokens; role stored on user record |
| Admin Service | User management, initiative listing, soft deletes, analytics aggregations. | Protected admin-only routes; queries across all initiatives |
| Audit Logger | Immutable record of URL checks and report generation events. | Write-only audit_log table; no soft-delete |

---

## Recommended Project Structure

```
mami-checker/
├── apps/
│   ├── api/                    # Express/FastAPI REST server
│   │   ├── routes/             # Route handlers per domain
│   │   │   ├── auth.routes.ts
│   │   │   ├── questionnaire.routes.ts
│   │   │   ├── report.routes.ts
│   │   │   ├── urlcheck.routes.ts
│   │   │   └── admin.routes.ts
│   │   ├── middleware/         # Auth, RBAC, rate-limit, validation
│   │   ├── openapi.yaml        # OpenAPI 3.x spec (source of truth)
│   │   └── server.ts
│   ├── worker/                 # URL check job worker (separate process)
│   │   ├── jobs/
│   │   │   └── url-probe.job.ts
│   │   └── worker.ts
│   └── web/                    # Basic frontend (optional for MVP)
├── packages/
│   ├── mami-framework/         # MAMI standard definition
│   │   ├── config/
│   │   │   └── mami-codes.json # Code, category, dimension, MoSCoW
│   │   └── index.ts            # Typed loader + validation
│   ├── questionnaire-engine/   # Core questionnaire logic
│   │   ├── schemas/            # Versioned JSON schemas (SurveyJS format)
│   │   │   └── v1/
│   │   │       └── questionnaire.json
│   │   ├── evaluator.ts        # Maps answers -> MAMI codes
│   │   └── versioning.ts
│   ├── rule-engine/            # GoRules ZEN wrapper
│   │   ├── decisions/          # JDM JSON decision files
│   │   │   └── mami-scoring.json
│   │   └── evaluator.ts        # Runs ZEN against answers
│   ├── url-checker/            # HTTP probe logic
│   │   ├── probe.ts            # HTTP status + keyword check
│   │   ├── snapshot.ts         # Hash + timestamp storage
│   │   └── consent.ts          # Consent record management
│   └── report-generator/       # Report assembly + template
│       ├── templates/
│       │   └── report.html.hbs # Handlebars template
│       └── generator.ts        # Compiles findings -> HTML
├── db/
│   ├── migrations/             # SQL migration files
│   └── seed.ts                 # Dev seed data
├── docker-compose.yml
└── openapi.yaml               # Root OpenAPI spec
```

### Structure Rationale

- **packages/mami-framework/:** Framework definition as a standalone package. Questionnaire engine and rule engine import it — never the reverse. Swappable without touching application logic.
- **packages/questionnaire-engine/:** Stores versioned schemas as JSON files. Engine code references schema by version. Answers stored in DB keyed by version.
- **packages/rule-engine/:** Wraps GoRules ZEN. Decision logic lives in JDM JSON files editable via the visual admin UI, not in code.
- **packages/url-checker/:** Pure probe logic. No knowledge of initiatives or reports. The worker and the API service both use this package, but job orchestration stays in the worker.
- **apps/worker/:** Separate Node.js process for URL jobs. Isolates blocking I/O from the request path. Shares DB connection but otherwise independent.
- **db/migrations/:** Single source of schema truth. No ORM auto-migration in production.

---

## Architectural Patterns

### Pattern 1: Config-Driven Domain Definition

**What:** The MAMI framework (codes, categories, MoSCoW levels) and the questionnaire schema are stored as JSON config files, loaded at startup, and exposed as read-only. Business logic references config IDs, not hardcoded strings.

**When to use:** Always — this is a hard requirement. It means adding a new MAMI code or changing a scoring rule requires editing a JSON file and restarting (or hot-reloading), not modifying application code.

**Trade-offs:** Pros: extensible, auditable diff via git. Cons: requires schema validation on load to catch config errors early.

**Example:**
```typescript
// packages/mami-framework/index.ts
import codes from './config/mami-codes.json';

export interface MamiCode {
  id: string;           // e.g. "S-HRA-1.1"
  category: string;     // e.g. "scheme"
  dimension: string;    // e.g. "human_readable"
  moscowLevel: 'MUST' | 'SHOULD' | 'COULD' | 'WONT';
  defaultSeverity: 'CRITICAL' | 'NON_CRITICAL';
  description: string;
}

export function getAllCodes(): MamiCode[] {
  return codes as MamiCode[];
}

export function getCode(id: string): MamiCode | undefined {
  return (codes as MamiCode[]).find(c => c.id === id);
}
```

---

### Pattern 2: Questionnaire Engine as JSON Schema Evaluator

**What:** The questionnaire is a SurveyJS-compatible JSON schema (versioned). The engine's job is to (a) serve the schema to the frontend, (b) validate incoming answers against it, and (c) map each answer to its MAMI code using the schema metadata.

**When to use:** For all question/answer interactions. The visual builder (SurveyJS Creator) edits the schema; the form library renders it; the backend stores both schema (by version) and answers (by initiative + version).

**Trade-offs:** Pros: admin can rearrange questions without code changes, branching logic via SurveyJS expressions. Cons: SurveyJS expression syntax must be understood by whoever manages the schema.

**Example:**
```typescript
// packages/questionnaire-engine/evaluator.ts
interface AnswerSet {
  questionnaireVersion: string;
  answers: Record<string, unknown>; // question ID -> answer value
}

interface MamiAnswerMapping {
  mamiCodeId: string;
  questionId: string;
  answerValue: unknown;
  isNotApplicable: boolean;
  explanation?: string; // comply-or-explain text
}

export function mapAnswersToMamiCodes(
  answerSet: AnswerSet,
  schema: SurveyJsSchema
): MamiAnswerMapping[] {
  // Each question in the schema has a custom property: mamiCodeId
  // This function produces the flattened mapping used by the rule engine
}
```

---

### Pattern 3: Rule Engine as Embedded Decision Evaluator

**What:** GoRules ZEN engine is embedded in the API process (not a separate service). It loads JDM decision files from disk at startup. The rule engine service receives the MamiAnswerMapping array and produces a findings array — one entry per MAMI code with score, severity, and rationale.

**When to use:** For all scoring and cross-check logic. The visual admin editor (JDM Editor React component) writes back to the JDM JSON files.

**Trade-offs:** Pros: sub-millisecond evaluation, no network hop, no extra service to operate. Cons: JDM files must be reloaded on change (restart or file watcher).

**Example:**
```typescript
// packages/rule-engine/evaluator.ts
import { ZenEngine } from '@gorules/zen-engine';

const engine = new ZenEngine();
engine.addLoader(async (key) => {
  // Load JDM file from ./decisions/{key}.json
});

export async function evaluateScoring(
  answers: MamiAnswerMapping[]
): Promise<Finding[]> {
  const result = await engine.evaluate('mami-scoring', { answers });
  return result.result as Finding[];
}
```

---

### Pattern 4: URL Check as Async Job with Consent Gate

**What:** When a user submits URLs for checking, the API records consent and enqueues a job. The worker process picks up the job, runs HTTP probes (status code, keyword presence), computes SHA-256 hash, stores a snapshot, and writes results back to the DB. The report generator reads snapshots when assembling the report.

**When to use:** For all URL checks. Never perform HTTP probes synchronously in the API request path — they can take seconds and will time out.

**Trade-offs:** Pros: non-blocking, retryable, auditable. Cons: results are eventually consistent (report generation must wait for pending jobs or show "pending" state).

**Example:**
```typescript
// apps/worker/jobs/url-probe.job.ts
export async function runUrlProbe(job: UrlProbeJob): Promise<void> {
  const { url, consentId, initiativeId, mamiCodeId } = job.data;

  // 1. Verify consent record exists and is not expired
  await verifyConsent(consentId, url);

  // 2. Rate-limit check (per domain, per hour)
  await rateLimit.checkAndIncrement(new URL(url).hostname);

  // 3. HTTP probe
  const result = await probe(url);

  // 4. Snapshot
  await storeSnapshot({ url, hash: sha256(result.body), timestamp: new Date(), statusCode: result.status });

  // 5. Write findings
  await db.urlCheckResult.upsert({ initiativeId, mamiCodeId, url, ...result });
}
```

---

### Pattern 5: Report Generator as Read-Only Assembler

**What:** Report generation is a read operation: it queries completed answer sets, rule engine findings (pre-computed or recomputed), and URL check results, then renders them through an HTML template. A snapshot of the rendered HTML is stored to support "view last report" without recomputation.

**When to use:** When a user triggers report (re-)generation. The generator is stateless — it reads, renders, stores.

**Trade-offs:** Pros: idempotent, fast, no mutations. Cons: if user re-answers and re-generates, the old snapshot is replaced (versioned snapshots are a future enhancement).

---

## Data Flow

### Primary Flow: User Completes Assessment and Gets Report

```
User fills questionnaire answers
    ↓
POST /initiatives/{id}/answers
    ↓
Questionnaire Engine validates answers against JSON schema
    ↓ (valid)
Answers stored: initiative_answers table (version-stamped)
    ↓
User clicks "Generate Report"
    ↓
POST /initiatives/{id}/report
    ↓
Rule Engine evaluates: answers → MamiAnswerMappings → Findings[]
    ↓
Report Generator assembles: Findings + URL check results → HTML
    ↓
HTML stored: reports table (with timestamp)
    ↓
GET /initiatives/{id}/report → Returns stored HTML
```

### URL Check Flow

```
User submits URL with consent checkbox
    ↓
POST /initiatives/{id}/url-checks (consent flag required)
    ↓
API records ConsentRecord (url, userId, timestamp)
    ↓
Job enqueued: UrlProbeJob { url, consentId, initiativeId, mamiCodeId }
    ↓
Worker picks up job
    ↓
Rate limiter check (per domain)
    ↓
HTTP probe: status code + keyword scan
    ↓
SHA-256 hash of response body
    ↓
UrlCheckResult + Snapshot written to DB
    ↓
(next report generation includes URL evidence)
```

### Admin Analytics Flow

```
GET /admin/analytics/heatmap
    ↓
Admin Service queries aggregate: findings grouped by mamiCodeId
    ↓
Returns matrix of {mamiCodeId, scoreAvg, criticalCount, totalInitiatives}
    ↓
Dashboard module renders heatmap (ECharts)
```

### Key Data Models

```
User
  id, email, passwordHash, role (USER|ADMIN), createdAt, deletedAt

Initiative
  id, userId, name, description, createdAt, updatedAt

QuestionnaireAnswer
  id, initiativeId, questionnaireVersion, answers (JSONB), submittedAt

ConsentRecord
  id, initiativeId, userId, url, givenAt, ipAddress

UrlCheckResult
  id, initiativeId, mamiCodeId, url, statusCode, keywordMatches,
  bodyHash, checkedAt, jobId

Report
  id, initiativeId, questionnaireVersion, htmlContent, generatedAt,
  findingsSnapshot (JSONB)

AuditLog
  id, eventType (URL_CHECK|REPORT_GENERATED), initiativeId, userId,
  metadata (JSONB), createdAt
```

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| External URLs (user-provided) | HTTP GET with timeout; rate-limited per domain | Respect robots.txt, set custom User-Agent identifying the tool |
| coe-dsc.nl embedding | Iframe or reverse proxy at /mami-checker path | CSS custom properties for color scheme theming |
| Dashboard (ECharts) | Embedded React component; reads from Admin API | Self-hosted, no external data leaves system |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| API ↔ Worker | Job queue (Bull + Redis, or pg-boss with Postgres) | Use pg-boss for under-50-users scale — avoids Redis dependency |
| API ↔ Rule Engine | In-process function call (ZEN embedded) | ZEN engine loaded once at startup; JDM files on disk |
| API ↔ MAMI Framework | In-process module import | JSON loaded at startup; validated against TypeScript types |
| Questionnaire Engine ↔ MAMI Framework | Import dependency (engine imports framework) | Never the reverse |
| Report Generator ↔ Rule Engine | Rule engine runs first; generator reads results | Generator does NOT re-run scoring; it reads pre-computed findings |
| Admin UI ↔ JDM Editor | React component embedded in admin; saves via PUT /admin/rules/{key} | JDM files written to disk; worker/API process reloads on change |

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-50 users (current target) | Monolith fine. pg-boss for jobs (no Redis). Single Postgres. Single process for API + embedded rule engine. |
| 50-1K users | Add Redis for job queue. Consider read replica for reports/analytics. Separate worker to its own dyno/container. |
| 1K+ users | Extract rule engine to standalone service if evaluation becomes a bottleneck. Cache rendered reports. CDN for static assets. |

### Scaling Priorities

1. **First bottleneck:** URL check jobs — fix by scaling worker process count, not API process.
2. **Second bottleneck:** Report generation HTML rendering — fix by caching stored HTML snapshots (already part of base design).

---

## Anti-Patterns

### Anti-Pattern 1: Scoring Logic Embedded in Application Code

**What people do:** Hardcode `if (answer.moscowLevel === 'MUST' && answer.value === 'NO') severity = 'CRITICAL'` directly in service files.

**Why it's wrong:** Every rule change requires a code deploy. Non-technical admins cannot adjust scoring. Violates the core "config-driven" requirement.

**Do this instead:** All scoring logic lives in GoRules JDM decision files. Application code only calls `engine.evaluate(answers)` and reads back results.

---

### Anti-Pattern 2: Synchronous URL Probing in API Request Path

**What people do:** Call `fetch(userProvidedUrl)` directly inside the POST handler and return results in the response.

**Why it's wrong:** External URLs can be slow or unreachable. A 30-second timeout will block the request. The API becomes unreliable.

**Do this instead:** Enqueue a job, return 202 Accepted with a job ID. The client polls or waits for a webhook/websocket notification.

---

### Anti-Pattern 3: Monolithic Report Object Containing Live Data

**What people do:** `GET /report` runs the questionnaire evaluation, rule engine, and template rendering on every request.

**Why it's wrong:** Report generation is expensive and should be explicitly triggered, not implicit on every view. Users expect to see the same report they generated, not a live recalculation that may differ.

**Do this instead:** Report generation is triggered explicitly (POST /report). The result is stored as a snapshot. GET /report returns the stored snapshot. Users re-trigger when they want a fresh report.

---

### Anti-Pattern 4: MAMI Framework Hardcoded in Multiple Places

**What people do:** Repeat MAMI code strings `"S-HRA-1.1"` directly in questionnaire config, rule engine config, seed data, and report templates.

**Why it's wrong:** Any framework update requires hunting across all files. Typos create silent mismatches.

**Do this instead:** `packages/mami-framework/` is the single source. All other packages import from it. The framework JSON is the only file to update when MAMI changes.

---

### Anti-Pattern 5: Treating the Visual Builder as the Source of Truth

**What people do:** Allow the SurveyJS Creator admin UI to write directly to the production questionnaire schema with no version bump.

**Why it's wrong:** Existing in-progress answers are now incompatible with the new schema. Report regeneration for old answers breaks.

**Do this instead:** Schema edits create a new version. New initiatives start on the new version. Old initiatives stay on their current version until explicitly migrated.

---

## Build Order (Dependency Implications for Roadmap)

The component graph has a clear bottom-up dependency order:

```
Level 0 (no dependencies):
  MAMI Framework Service (config + types only)

Level 1 (depends on L0):
  Auth / User Service  (depends on: nothing except DB)
  Questionnaire Engine (depends on: MAMI Framework)
  Rule Engine Service  (depends on: MAMI Framework, Questionnaire Engine types)

Level 2 (depends on L1):
  URL Check Subsystem  (depends on: Auth/consent record, DB)
  Admin Service        (depends on: Auth, all data tables)

Level 3 (depends on L1+L2):
  Report Generator     (depends on: Rule Engine, URL Check results, MAMI Framework)
  Dashboard Module     (depends on: Report data, Admin Service)
```

**Recommended build sequence for phases:**

1. **Phase 1 — Foundation:** DB schema, migrations, Auth/User service, RBAC middleware, basic REST shell, OpenAPI spec stub. No domain logic yet.
2. **Phase 2 — MAMI Core:** MAMI Framework package, Questionnaire Engine (schema + answer storage), basic questionnaire API endpoints.
3. **Phase 3 — Scoring:** Rule Engine integration, scoring evaluation, findings generation. This phase delivers end-to-end: answer → finding.
4. **Phase 4 — Report:** Report Generator (HTML template, snapshot storage). First complete user flow: register → answer → generate report → view report.
5. **Phase 5 — URL Checks:** URL Check Subsystem (worker, consent, probes, snapshots). Integrates into report as evidence.
6. **Phase 6 — Admin + Dashboard:** Admin endpoints, analytics, heatmap, dashboard embedding.
7. **Phase 7 — Visual Editors:** SurveyJS Creator for questionnaire builder, JDM Editor for rule editor. Admin-facing configuration UIs.

This order ensures each phase is independently deliverable and testable. Phases 1-4 deliver the core user value; Phases 5-7 add depth and admin tooling.

---

## Sources

- SurveyJS Architecture Documentation: https://surveyjs.io/documentation/surveyjs-architecture (MEDIUM confidence — official docs, verified)
- SurveyJS Backend Integration: https://surveyjs.io/documentation/backend-integration (MEDIUM confidence — official docs, verified)
- GoRules ZEN Engine Overview: https://docs.gorules.io/reference/overview (MEDIUM confidence — official docs, verified)
- GoRules JDM Editor: https://github.com/gorules/jdm-editor (MEDIUM confidence — official GitHub, verified)
- Rules Engine Design Patterns: https://www.nected.ai/us/blog-us/rules-engine-design-pattern (LOW confidence — WebSearch only)
- Web-Queue-Worker Architecture: https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/web-queue-worker (HIGH confidence — official Microsoft docs)
- Modular Monolith Architecture: https://software-architecture-guild.com/guide/architecture/styles/modular-monolith/ (LOW confidence — WebSearch, multiple sources agree on pattern)
- Rule Engine Microservice Pattern: https://www.nected.ai/blog/rule-engine-microservice (LOW confidence — WebSearch only)

---

*Architecture research for: MAMI Compliance Checker — Config-driven compliance assessment system*
*Researched: 2026-02-14*
