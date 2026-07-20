# Phase 6: Demo Readiness — Admin Panel, Password Reset, and 50-User Scalability - Research

**Researched:** 2026-03-03
**Domain:** FastAPI admin panel, password reset (JWT/DB token), email (Resend), SQLAlchemy pool tuning, React 19 error resilience, TanStack Query v5 mutations, TanStack Router v1 auth guards, Ant Design v6 tables
**Confidence:** HIGH (core stack verified against official docs and existing codebase)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Admin Panel**
- Access: Protected by existing `require_admin()` dependency + a new `/admin` route group on the frontend, only visible/accessible to ADMIN role users.
- Users view: Table listing all registered users (email, role, participant_type, created_at, initiative status). Admin can delete a user (hard delete — cascades to all their data). No soft delete for demo simplicity.
- Questionnaires view: Table listing all submitted initiatives with their answers and compliance status. Admin can delete an initiative independently of its user.
- Dataset download: Single button — exports all initiatives + all answers + all evidence URLs as a CSV (or Excel). One API endpoint: `GET /api/v1/admin/export`. Streamed as a file download.
- Demo data reset: Admin endpoint `POST /api/v1/admin/reset-demo` — deletes all non-admin users and all their data. Requires confirmation (button + modal "Are you sure?"). This lets the demo organizer clean up between runs without touching the Railway DB directly.

**Password Reset Flow**
- Trigger: "Forgot password?" link on the login page.
- Flow: User enters email → backend generates a short-lived token (15-minute expiry, stored in DB or signed JWT) → email sent with reset link → user clicks link → enters new password → password updated, token invalidated.
- Email infrastructure: Use Resend (simplest API, generous free tier, reliable deliverability). Configured via `RESEND_API_KEY` environment variable in Railway. Falls back gracefully if not configured (logs the reset link instead of sending — useful for local dev).
- New DB fields: `password_reset_token` (nullable string) + `password_reset_expires` (nullable datetime) on the User model. Alembic migration required.
- New endpoints: `POST /api/v1/auth/forgot-password` + `POST /api/v1/auth/reset-password`.
- Frontend: Two new auth routes — `/forgot-password` (email form) and `/reset-password?token=...` (new password form).

**50-User Scalability**
- DB connection pool: Explicitly configure SQLAlchemy engine with `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, `pool_recycle=1800`. Change in `backend/app/db/session.py`.
- Rate limiting on answer endpoints: Apply `slowapi` limiter to `PUT /questionnaire/initiatives/{id}/answers/{qid}` — limit to 60 requests/minute per user.
- Railway deployment: Ensure Railway service has sufficient memory (512MB+). No horizontal scaling needed for 50 users — vertical is sufficient.

**Frontend Resilience**
- Autosave status indicator: Visible "Saved / Saving... / Save failed" badge in the wizard header reflecting current mutation state from React Query.
- Graceful error pages: Global Axios response interceptor + React error boundary. Network errors and 5xx show user-friendly message.
- 401 token-expiry redirect: Add 401 interceptor to Axios. Clear localStorage and redirect to `/login?session=expired` that shows a banner.
- Submission confirmation screen: After questionnaire submit, show dedicated confirmation with CTA to generate report.

### Claude's Discretion

(No explicit discretion areas noted in CONTEXT.md — all implementation decisions are locked above.)

### Deferred Ideas (OUT OF SCOPE)

- Soft delete for users: A soft-delete (is_deleted flag) with recovery capability — revisit before going to full production.
- Refresh tokens / token renewal: JWT is currently 24h with no refresh. Refresh token flow deferred.
- Sentry / error monitoring: Structured error reporting not required for the demo itself.
- Aggregate compliance heatmap (Phase 5): Admin analytics across all initiatives — deferred to Phase 5.
- Audit logging (Phase 5): Insert-only audit log for all admin and user actions — deferred to Phase 5.
- PDF export (Phase 5): WeasyPrint PDF download — deferred to Phase 5.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADMN-DEMO-01 | Admin can view all users in a table (email, role, participant_type, created_at, initiative status) | Ant Design v6 Table + `require_admin()` dep + new `GET /api/v1/admin/users` endpoint |
| ADMN-DEMO-02 | Admin can hard-delete a user (cascades to all their data) | Manual delete order pattern: questionnaire_answer → evidence_url → compliance_report → initiative → user; no CASCADE FK on current models |
| ADMN-DEMO-03 | Admin can view all initiatives/questionnaire submissions with status | `GET /api/v1/admin/initiatives` endpoint; Ant Design Table with status column |
| ADMN-DEMO-04 | Admin can delete an initiative independently of its user | `DELETE /api/v1/admin/initiatives/{id}` — cascades owned rows; requires delete-order pattern |
| ADMN-DEMO-05 | Admin can download full dataset as CSV and reset demo data | `GET /api/v1/admin/export` (StreamingResponse CSV) + `POST /api/v1/admin/reset-demo` (confirm modal) |
| AUTH-RESET-01 | User can trigger password reset via "Forgot password?" on login page | New frontend route `/_auth/forgot-password`; calls `POST /api/v1/auth/forgot-password` |
| AUTH-RESET-02 | Backend generates short-lived token, stores in DB, sends email via Resend | DB-stored token in `password_reset_token`/`password_reset_expires` on User; Resend SDK `resend.Emails.send()` with BackgroundTasks |
| AUTH-RESET-03 | User clicks link, sets new password, token is invalidated | `POST /api/v1/auth/reset-password` validates token, hashes new password, nulls out token fields |
| AUTH-RESET-04 | Falls back to log-only when RESEND_API_KEY not configured | `if not settings.RESEND_API_KEY: logger.info(f"[DEV] Reset link: {link}")` |
| INFR-SCALE-01 | DB connection pool tuned: pool_size=10, max_overflow=20, pool_pre_ping=True, pool_recycle=1800 | `create_engine()` kwargs in `backend/app/db/session.py` |
| INFR-SCALE-02 | Answer endpoint rate-limited to 60 req/min per user (IP-based via slowapi) | `@limiter.limit("60/minute")` on `PUT /questionnaire/initiatives/{id}/answers/{qid}`; `Request` param required |
| INFR-SCALE-03 | Railway service verified for 512MB+ memory headroom | Documentation only — verify Railway dashboard settings |
| UX-RESIL-01 | Autosave status indicator ("Saved / Saving... / Save failed") in wizard header | TanStack Query v5 `useMutation` → `isPending` / `isSuccess` / `isError` state |
| UX-RESIL-02 | 401 interceptor clears token and redirects to `/login?session=expired` | Axios response interceptor enhancement (already partially implemented in `api.ts`) |
| UX-RESIL-03 | Submission confirmation screen after questionnaire submit | New wizard state/page shown on successful `POST /submit`; CTA to generate report |
| UX-RESIL-04 | 5xx / network errors show user-friendly message | Axios 5xx interceptor branch + React error boundary wrapping app routes |
</phase_requirements>

---

## Summary

Phase 6 delivers four independent feature tracks on top of a stable codebase: an admin panel, a password reset flow, connection pool tuning, and frontend resilience. The codebase already has `require_admin()` and `slowapi` in place — this phase extends rather than replaces existing patterns.

The most architecturally significant decision is **password reset token storage**: DB-stored tokens (nullable `password_reset_token` + `password_reset_expires` columns on User) are the correct choice for this stack. They allow immediate invalidation after single use, which JWT tokens cannot provide without a blocklist. The existing `security.py` JWT signing/decoding pattern is kept for session auth only; password reset tokens use random secrets stored as plain strings (not JWTs).

The DB connection pool change is a single-file, three-line change to `backend/app/db/session.py`. The current default pool (pool_size=5, no overflow config) will exhaust under 50 concurrent users who are all actively saving answers. Pool tuning to `pool_size=10, max_overflow=20` provides headroom for 30 simultaneous connections, which is safe for one Railway Uvicorn worker serving 50 users who do not all hit the DB simultaneously.

**Primary recommendation:** Implement in four independent tracks (admin backend + admin frontend, password reset backend + frontend, pool tuning + rate limiting, frontend resilience) that can be planned and executed as separate waves with no cross-track blocking dependencies.

---

## Standard Stack

### Core (all already installed — no new backend dependencies except `resend`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | >=0.115.0 | API framework | Already in use; `require_admin()` and `slowapi` already wired |
| SQLModel | 0.0.33 | ORM + schema | Already in use; `User` model gets two new nullable columns |
| SQLAlchemy | >=2.0.14,<2.1.0 | Engine / pool config | Pool kwargs go on `create_engine()` directly |
| Alembic | >=1.13.0 | DB migrations | Manual migration (DB unreachable locally) — follow established pattern |
| slowapi | >=0.1.9 | Rate limiting | Already installed and wired in `main.py` |
| PyJWT | >=2.8.0 | JWT (session auth only) | Password reset uses DB tokens, NOT JWT |
| bcrypt | >=4.2.0 | Password hashing | Already in use; new password in reset flow hashed with same `hash_password()` |
| resend | 2.x (latest) | Transactional email | Official Python SDK; simplest API for one-off email sending |

### Frontend (all already installed — no new packages required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @tanstack/react-query | ^5.90.21 | Server state + mutation states | `useMutation` returns `isPending`, `isError`, `isSuccess` for autosave indicator |
| @tanstack/react-router | ^1.160.0 | File-based routing + auth guards | `beforeLoad` for admin route protection; search params for session-expired message |
| antd | ^6.3.0 | UI component library | Table + Popconfirm + Modal for admin panel |
| axios | ^1.13.5 | HTTP client | Interceptors already partially set up in `api.ts` |
| react | ^19.2.0 | UI framework | Error boundary pattern supported |

### New Dependency (backend only)

```bash
# In backend/ directory
uv add resend
```

The `resend` Python SDK (v2.x) provides `resend.Emails.send()`. No additional frontend packages are needed.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| DB-stored reset token | JWT signed reset token | JWT cannot be invalidated after single use without a blocklist; DB token is simpler and more secure for this use case |
| Resend SDK | SMTP via fastapi-mail | Resend has a free tier, better deliverability, and a cleaner API; SMTP requires more infra config |
| Ant Design Table | Custom table | Ant Design already in use; Table + Popconfirm handles pagination, sorting, confirm-delete out of the box |
| `react-error-boundary` package | Custom class component | The project has no `react-error-boundary` installed; a simple class-based boundary or the Axios interceptor alone covers the 5xx use case without adding a dependency |

---

## Architecture Patterns

### Recommended File Structure (additions to existing)

```
backend/app/
├── api/v1/
│   ├── admin.py            # NEW: all /admin/* endpoints
│   └── auth.py             # EXTEND: add forgot-password + reset-password
├── db/
│   └── session.py          # CHANGE: add pool kwargs to create_engine()
├── models/
│   └── user.py             # CHANGE: add password_reset_token + password_reset_expires
└── alembic/versions/
    └── g7b5c4d3e2f1_add_password_reset_fields.py  # NEW migration

frontend/src/
├── routes/
│   ├── _auth/
│   │   ├── forgot-password.tsx     # NEW: email form
│   │   └── reset-password.tsx      # NEW: new password form (reads ?token= from search)
│   └── _app/
│       └── admin/
│           └── index.tsx           # NEW: admin panel (users + initiatives tables)
└── lib/
    └── api.ts              # CHANGE: enhance 401 interceptor + add 5xx handling
```

### Pattern 1: DB Connection Pool Tuning

**What:** Replace `create_engine(settings.DATABASE_URL)` with explicit pool kwargs.
**When to use:** Always in production; the default pool_size=5 exhausts under concurrent load.

```python
# backend/app/db/session.py — FULL REPLACEMENT
# Source: https://docs.sqlalchemy.org/en/20/core/pooling.html
from sqlmodel import Session, create_engine
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,        # Maintained connections (sleeping)
    max_overflow=20,     # Extra connections during peak (total max = 30)
    pool_pre_ping=True,  # Validate connections before use (catches stale)
    pool_recycle=1800,   # Recycle connections after 30 min (prevents idle timeout)
)

def get_session():
    with Session(engine) as session:
        yield session
```

**Why these values for 50 users:** With one Uvicorn worker and 50 concurrent users who are NOT all hitting the DB simultaneously (most are reading the page, not saving), 30 max connections (10 + 20) provides a 60% safety margin over the default 5.

### Pattern 2: slowapi Rate Limiting on Specific Endpoint

**What:** Add per-request rate limit to the answer upsert endpoint. Uses IP-based key (existing `get_remote_address` from `main.py`). `Request` must be an explicit parameter.
**When to use:** Endpoints that hit the DB on every call from potentially many concurrent users.

```python
# backend/app/api/v1/questionnaire.py
# Source: https://slowapi.readthedocs.io/
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.put("/questionnaire/initiatives/{initiative_id}/answers/{question_id}", response_model=AnswerRead)
@limiter.limit("60/minute")
def upsert_answer(
    request: Request,          # REQUIRED: slowapi needs Request as explicit param
    initiative_id: int,
    question_id: str,
    answer_in: AnswerCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    ...
```

**Critical:** `request: Request` MUST be the first parameter after decorator or slowapi silently fails to hook in. The `Limiter` instance in the router can reuse `get_remote_address` — no need for a custom per-user JWT key_func since IP-based is sufficient for a 50-user demo.

### Pattern 3: Resend Email with FastAPI BackgroundTasks

**What:** Send password reset email without blocking the HTTP response. Falls back to log-only when `RESEND_API_KEY` is unset.
**When to use:** Any email send in a request path; email delivery is slow and should never block the response.

```python
# backend/app/api/v1/auth.py (password reset endpoints)
# Source: https://resend.com/docs/send-with-python (SDK 2.x)
import resend
from fastapi import BackgroundTasks
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def _send_reset_email(email: str, token: str) -> None:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    if not settings.RESEND_API_KEY:
        logger.info(f"[DEV] Password reset link for {email}: {reset_url}")
        return
    resend.api_key = settings.RESEND_API_KEY
    params: resend.Emails.SendParams = {
        "from": "noreply@coe-dsc.nl",
        "to": [email],
        "subject": "Reset your MAMI Checker password",
        "html": f"<p>Click the link to reset your password (expires in 15 minutes):</p>"
                f"<p><a href='{reset_url}'>{reset_url}</a></p>",
    }
    resend.Emails.send(params)

@router.post("/auth/forgot-password", status_code=202)
def forgot_password(
    email_in: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.email == email_in.email)).first()
    # Always return 202 regardless — never reveal whether email exists
    if user:
        token = secrets.token_urlsafe(32)
        user.password_reset_token = token
        user.password_reset_expires = datetime.utcnow() + timedelta(minutes=15)
        session.add(user)
        session.commit()
        background_tasks.add_task(_send_reset_email, user.email, token)
    return {"message": "If this email is registered, a reset link has been sent."}
```

### Pattern 4: DB-Stored Reset Token Validation (Reset Password Endpoint)

```python
# Source: established security pattern — https://supertokens.com/blog/implementing-a-forgot-password-flow
@router.post("/auth/reset-password", status_code=200)
def reset_password(
    payload: ResetPasswordRequest,
    session: Session = Depends(get_session),
):
    user = session.exec(
        select(User).where(User.password_reset_token == payload.token)
    ).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    if user.password_reset_expires is None or \
       user.password_reset_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")

    user.hashed_password = hash_password(payload.new_password)
    user.password_reset_token = None     # Invalidate immediately — one-time use
    user.password_reset_expires = None
    session.add(user)
    session.commit()
    return {"message": "Password reset successfully. Please log in."}
```

### Pattern 5: Alembic Migration — Add Nullable Columns to User Table

**What:** Manually written migration following the existing project pattern (DB not reachable locally, so autogenerate is not used).
**When to use:** Every time a new column is added to an existing table.

```python
# backend/alembic/versions/g7b5c4d3e2f1_add_password_reset_fields.py
# Source: https://alembic.sqlalchemy.org/en/latest/ops.html
from alembic import op
import sqlalchemy as sa

revision = 'g7b5c4d3e2f1'
down_revision = 'f7b8c9d0e1f2'  # make_initiative_description_nullable — confirmed HEAD
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('user',
        sa.Column('password_reset_token', sa.String(), nullable=True)
    )
    op.add_column('user',
        sa.Column('password_reset_expires', sa.DateTime(), nullable=True)
    )

def downgrade() -> None:
    op.drop_column('user', 'password_reset_expires')
    op.drop_column('user', 'password_reset_token')
```

The `User` SQLModel must also be updated to declare these fields:
```python
# backend/app/models/user.py (additions)
password_reset_token: Optional[str] = None
password_reset_expires: Optional[datetime] = None
```

### Pattern 6: Admin Hard-Delete — Manual Delete Order

**What:** The current models do NOT have `ondelete="CASCADE"` foreign keys. Hard-deleting a user requires manually deleting child rows in correct order.
**When to use:** Hard delete of a user or initiative in the admin endpoints.

```python
# Source: derived from model FK structure in this codebase
# Delete order for a user (cascade manually):
# 1. questionnaire_answer rows (via initiative_id)
# 2. evidence_url rows (via initiative_id)
# 3. compliance_report rows (via initiative_id)
# 4. initiative row (via user_id)
# 5. user row

def delete_user_cascade(user_id: int, session: Session) -> None:
    initiative = session.exec(
        select(Initiative).where(Initiative.user_id == user_id)
    ).first()
    if initiative:
        session.exec(
            delete(QuestionnaireAnswer).where(
                QuestionnaireAnswer.initiative_id == initiative.id
            )
        )
        session.exec(
            delete(EvidenceURL).where(EvidenceURL.initiative_id == initiative.id)
        )
        session.exec(
            delete(ComplianceReport).where(
                ComplianceReport.initiative_id == initiative.id
            )
        )
        session.delete(initiative)
    user = session.get(User, user_id)
    if user:
        session.delete(user)
    session.commit()
```

**Why not add CASCADE FK constraints now:** Adding FK constraints to existing tables requires Alembic migrations and risk of breaking the Railway DB. For the demo, the manual delete-order approach is safer and more explicit.

### Pattern 7: FastAPI StreamingResponse CSV Export

**What:** Stream all initiatives + answers + evidence as CSV without loading everything into memory.
**When to use:** Any large data export endpoint.

```python
# Source: https://fastapi.tiangolo.com/advanced/custom-response/
import csv
import io
from fastapi.responses import StreamingResponse

@router.get("/admin/export")
def export_dataset(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["user_email", "initiative_name", "participant_type",
                         "question_id", "mami_code", "answer_value",
                         "followup_other", "evidence_url"])
        output.seek(0)
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)

        # Query all data in one JOIN or batched reads
        rows = session.exec(
            select(User, Initiative, QuestionnaireAnswer)
            .join(Initiative, Initiative.user_id == User.id)
            .join(QuestionnaireAnswer, QuestionnaireAnswer.initiative_id == Initiative.id)
        ).all()

        for user, initiative, answer in rows:
            writer.writerow([
                user.email, initiative.name, initiative.participant_type,
                answer.question_id, answer.mami_code, answer.answer_value,
                answer.followup_other or "", ""
            ])
            output.seek(0)
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mami-dataset.csv"},
    )
```

### Pattern 8: TanStack Query v5 Autosave Mutation Status

**What:** Expose `isPending`, `isSuccess`, `isError` from `useMutation` to drive an autosave badge.
**When to use:** Any save-on-navigate or auto-save scenario.

```typescript
// Source: https://tanstack.com/query/v5/docs/react/reference/useMutation
const saveAnswerMutation = useMutation({
  mutationFn: (payload: AnswerPayload) =>
    api.put(`/questionnaire/initiatives/${initiativeId}/answers/${payload.questionId}`, payload),
});

// In WizardPage header:
function AutosaveBadge() {
  const { isPending, isSuccess, isError } = saveAnswerMutation;
  if (isPending) return <span style={{ color: "#6B7280" }}>Saving...</span>;
  if (isError)   return <span style={{ color: "#F59E0B" }}>Save failed — retrying</span>;
  if (isSuccess) return <span style={{ color: "#059669" }}>Saved</span>;
  return null;
}
```

**v5 migration note:** TanStack Query v5 renamed `isLoading` → `isPending` for mutations. The project already uses v5 (`^5.90.21`). Do NOT use `isLoading` — it is removed in v5.

### Pattern 9: Axios 401 Interceptor with session=expired Query Param

**What:** Enhance the existing 401 interceptor in `api.ts` to add `?session=expired` to the redirect URL so the login page can show a banner.
**When to use:** Token expiry during active session.

```typescript
// frontend/src/lib/api.ts — CHANGE the 401 branch
api.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error.response?.status;
    if (status === 401) {
      authStore.clearToken();
      window.location.href = "/login?session=expired";  // ADD ?session=expired
    }
    // 5xx: let it propagate — TanStack Query error state + error boundary handles it
    return Promise.reject(error);
  }
);
```

The login page reads `?session=expired` from the URL and shows a banner:
```typescript
// frontend/src/routes/_auth/login.tsx — read search param
import { useSearch } from "@tanstack/react-router";
const search = useSearch({ from: "/_auth/login" });
// If search.session === "expired": render <Alert type="warning" message="Session expired..." />
```

### Pattern 10: TanStack Router Admin Route Guard

**What:** Protect `/admin` route so only ADMIN role users can access it. Redirect non-admins to dashboard.
**When to use:** Role-based route protection beyond simple auth check.

```typescript
// frontend/src/routes/_app/admin/index.tsx
// Source: https://tanstack.com/router/v1/docs/framework/react/guide/authenticated-routes
export const Route = createFileRoute("/_app/admin/")({
  beforeLoad: async ({ context }) => {
    // authStore only checks token presence; we need to verify ADMIN role
    // Use a cached /auth/me response (via React Query) OR decode token client-side
    // Simplest approach: call /auth/me and check role
    const res = await api.get<{ role: string }>("/auth/me");
    if (res.data.role !== "ADMIN") {
      throw redirect({ to: "/dashboard" });
    }
  },
  component: AdminPage,
});
```

**Note on route file naming:** The project uses `_app.tsx` flat layout (not `_app/_layout.tsx` — this was a known path conflict from Phase 1). The admin route should be `frontend/src/routes/_app/admin/index.tsx` OR `frontend/src/routes/_app/admin.tsx`. Choose `_app/admin.tsx` to stay consistent with the flat pattern.

### Pattern 11: Ant Design v6 Table with Popconfirm Delete

**What:** Display user/initiative data in a sortable, paginated table with action column.
**When to use:** Admin panel data views.

```typescript
// Source: https://ant.design/components/table/ + https://ant.design/components/popconfirm/
import { Table, Button, Popconfirm, Space, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";

interface UserRow {
  id: number;
  email: string;
  role: string;
  participant_type: string;
  created_at: string;
}

const columns: ColumnsType<UserRow> = [
  { title: "Email", dataIndex: "email", sorter: (a, b) => a.email.localeCompare(b.email) },
  { title: "Role", dataIndex: "role", render: (r) => <Tag>{r}</Tag> },
  { title: "Type", dataIndex: "participant_type" },
  { title: "Created", dataIndex: "created_at" },
  {
    title: "Actions",
    render: (_, record) => (
      <Space>
        <Popconfirm
          title="Delete user?"
          description="This will permanently delete the user and all their data."
          okText="Delete"
          okButtonProps={{ danger: true }}
          cancelText="Cancel"
          onConfirm={() => handleDeleteUser(record.id)}
        >
          <Button danger size="small">Delete</Button>
        </Popconfirm>
      </Space>
    ),
  },
];

<Table
  dataSource={users}
  columns={columns}
  rowKey="id"
  pagination={{ pageSize: 20, showSizeChanger: false }}
/>
```

### Anti-Patterns to Avoid

- **Using JWT for password reset tokens:** JWTs cannot be invalidated before expiry without a blocklist. If the same JWT secret is used for both session and reset tokens, a reset token can be replayed until expiry. Use DB-stored random tokens for password reset.
- **Calling `resend.Emails.send()` synchronously in the request path:** Email delivery is slow (100-500ms). Always use `background_tasks.add_task()`. Never await or call it directly in the endpoint body.
- **Forgetting `request: Request` on rate-limited endpoints:** slowapi silently fails to hook if `Request` is not an explicit function parameter. The decorator `@limiter.limit("60/minute")` REQUIRES `request: Request` as a parameter.
- **Using `isLoading` from TanStack Query v5:** In v5, `isLoading` was renamed to `isPending` for both `useQuery` and `useMutation`. The project is on v5 — use `isPending` everywhere.
- **Hard-coding delete in wrong order:** The current User → Initiative → QuestionnaireAnswer chain has no DB-level CASCADE. Deleting `user` before `initiative` before `questionnaire_answer` will violate FK constraints. Always delete children first.
- **Loading all DB rows into memory for CSV export:** Use a generator that yields one row at a time to `StreamingResponse`. Do not call `session.exec(select(...)).all()` and build a giant list.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Email delivery | Custom SMTP wrapper | `resend` Python SDK | Handles auth, TLS, retries, bounces; free tier covers demo |
| Rate limiting | Custom counter in DB | `slowapi` (already installed) | Thread-safe, request-scoped, zero extra code |
| CSV streaming | Custom chunking logic | Python `csv` module + `io.StringIO` + `StreamingResponse` | stdlib handles quoting, escaping, encoding |
| Admin role check | Custom middleware | `require_admin()` dep (already in `deps.py`) | Already in use on other routes; no new code needed |
| Token generation | Custom random string | `secrets.token_urlsafe(32)` from stdlib | Cryptographically secure; no dependency needed |
| Confirm-delete modal | Custom modal component | Ant Design `Popconfirm` (already installed) | Built-in confirmation UX; accessible and styled |
| Error boundary | New package install | Simple class-based boundary or existing Axios interceptor | Project has no `react-error-boundary` installed; adding it for one use case adds unnecessary dependency |

**Key insight:** Every tool needed for this phase is already installed. The only NEW dependency is `resend` (Python SDK). The phase is primarily about wiring together existing capabilities, not adding infrastructure.

---

## Common Pitfalls

### Pitfall 1: Missing `request: Request` on slowapi-decorated Endpoints

**What goes wrong:** The rate limiter decorator `@limiter.limit("60/minute")` appears to work (no import error) but silently does not rate-limit requests.
**Why it happens:** slowapi reads the `Request` object to extract the client IP. If `Request` is not an explicit positional parameter in the function signature, the decorator cannot find it.
**How to avoid:** Always add `request: Request` as the FIRST parameter of any rate-limited endpoint function (before other Depends()).
**Warning signs:** Load tests show no 429 responses even at high rates; requests go through uncapped.

### Pitfall 2: Password Reset Token Timing Attack / Email Enumeration

**What goes wrong:** Returning different responses for registered vs. unregistered email addresses lets attackers enumerate valid accounts.
**Why it happens:** Natural impulse to return 404 when email not found.
**How to avoid:** Always return HTTP 202 with the same generic message regardless of whether the email exists. Only generate the token and send the email if the user exists (silently skip if not). This pattern is already used for login (dummy hash verification).
**Warning signs:** `/forgot-password` returns different status codes for existing vs. non-existing emails.

### Pitfall 3: Pool Exhaustion with Synchronous Endpoints + Uvicorn

**What goes wrong:** Under 50 concurrent users all saving answers simultaneously, the DB pool exhausts and requests block waiting for a connection, causing timeouts (500/503).
**Why it happens:** The current `create_engine(DATABASE_URL)` uses SQLAlchemy's default `pool_size=5`. With 50 users each making one DB request, 45 requests queue behind the 5 available connections.
**How to avoid:** Set `pool_size=10, max_overflow=20`. This allows up to 30 simultaneous DB connections — more than enough for 50 users whose requests are interleaved.
**Warning signs:** Occasional 500 errors during load testing that resolve when users stop; `QueuePool limit of size 5 overflow 10 reached` in logs.

### Pitfall 4: Reset Token Not Invalidated After Use

**What goes wrong:** A password reset token can be reused to reset the password again after initial use (e.g., if an attacker intercepts the reset link).
**Why it happens:** Forgetting to null out `password_reset_token` and `password_reset_expires` after successful password change.
**How to avoid:** In `reset_password` endpoint, always set both fields to `None` and commit before returning success.
**Warning signs:** Calling `POST /auth/reset-password` twice with the same token both succeed.

### Pitfall 5: Alembic Head Reference

**What goes wrong:** New migration fails because `down_revision` doesn't match the actual current head in the running DB.
**Why it happens:** The most recent migration is `make_initiative_description_nullable.py` (not the `f6a4b3c2d1e9` file despite sort order).
**How to avoid:** Before writing the migration, confirm the current head: `alembic history` or check `down_revision` chain. Use the actual HEAD revision value as `down_revision` in the new migration.
**Warning signs:** `alembic upgrade head` fails with "Can't locate revision" or "Multiple head revisions" error.

### Pitfall 6: Admin Route on TanStack Router — Flat vs. Nested

**What goes wrong:** Creating `_app/_layout.tsx` instead of using the flat `_app.tsx` pattern causes route conflicts (documented in project STATE.md as Phase 1 decision).
**Why it happens:** TanStack Router has two layout patterns; mixing them causes the router to fail to match routes.
**How to avoid:** Use the FLAT pattern: `_app.tsx` (exists), `_app/admin.tsx` (new). NOT `_app/_layout.tsx` or `_app/_app.tsx`.
**Warning signs:** Admin route renders the wrong layout or 404s despite the file existing.

### Pitfall 7: `useMutation` Status Resets After Navigation

**What goes wrong:** The "Saved" badge flashes briefly and disappears when the user navigates between wizard steps, even though data is actually saved.
**Why it happens:** `useMutation` status resets to `idle` after `mutationCachetime` elapses or when the component remounts.
**How to avoid:** Keep mutation state visible for a minimum duration using a `useEffect` timer that holds `isSuccess` visible for 2 seconds. Alternatively, use a local `useState` that captures the last-saved timestamp for display.
**Warning signs:** "Saved" badge flashes and immediately disappears.

---

## Code Examples

### Config: Add RESEND_API_KEY and FRONTEND_URL to Settings

```python
# backend/app/core/config.py (additions)
class Settings(BaseSettings):
    # ... existing fields ...
    RESEND_API_KEY: str = ""          # Empty = dev fallback (log only)
    FRONTEND_URL: str = "http://localhost:5173"  # Used in reset email link
```

### Demo Data Reset Endpoint

```python
# backend/app/api/v1/admin.py
# Source: project pattern — manual delete order
@router.post("/admin/reset-demo", status_code=200)
def reset_demo(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """Delete all non-admin users and all their data. DESTRUCTIVE."""
    non_admin_users = session.exec(
        select(User).where(User.role != "ADMIN")
    ).all()
    for user in non_admin_users:
        delete_user_cascade(user.id, session)
    return {"deleted_users": len(non_admin_users)}
```

### Frontend: Session Expired Banner on Login Page

```typescript
// frontend/src/routes/_auth/login.tsx (additions)
// Source: https://tanstack.com/router/v1/docs/framework/react/guide/authenticated-routes
import { useSearch } from "@tanstack/react-router";
import { Alert } from "antd";

// In LoginPage component:
const search = useSearch({ from: "/_auth/login" });
const sessionExpired = (search as { session?: string }).session === "expired";

return (
  <>
    {sessionExpired && (
      <Alert
        type="warning"
        message="Your session expired. Please log in again."
        showIcon
        style={{ marginBottom: "1rem" }}
      />
    )}
    {/* ... existing login form ... */}
  </>
);
```

### Frontend: Submission Confirmation State in WizardPage

```typescript
// On successful submit mutation:
const [submitted, setSubmitted] = useState(false);

const submitMutation = useMutation({
  mutationFn: () => api.post(`/questionnaire/initiatives/${initiativeId}/submit`),
  onSuccess: () => setSubmitted(true),
});

if (submitted) {
  return (
    <div style={{ textAlign: "center", padding: "3rem" }}>
      <h2>Thank you — your submission is complete.</h2>
      <p>You can now generate your compliance report.</p>
      <Button type="primary" onClick={() => navigate({ to: "/dashboard" })}>
        Generate Report
      </Button>
    </div>
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `isLoading` in React Query | `isPending` (mutations) | TanStack Query v5 (2023) | Use `isPending` not `isLoading` in this project — already on v5 |
| SMTP for transactional email | Resend API SDK | 2022-2024 | No SMTP server needed; simpler key-based auth |
| JWT for password reset | DB-stored random token | Security best practice | JWT cannot be invalidated; DB token can be nulled after use |
| `pool_size=5` default | Explicit pool config | Always needed for production | SQLAlchemy default is for development; must be tuned for concurrent load |
| `window.location.href = "/login"` | `/login?session=expired` | This phase | Enables visible session-expired feedback |

**Deprecated / outdated in this project context:**
- `isLoading` for mutations: renamed to `isPending` in TanStack Query v5
- `python-jose`: not used (PyJWT is the project choice per STATE.md)
- `passlib`: not used (direct bcrypt is the project choice per STATE.md)

---

## Open Questions

1. **Alembic head revision — RESOLVED**
   - **RESOLVED:** Current HEAD revision is `f7b8c9d0e1f2` (make_initiative_description_nullable, created 2026-02-20). Use this as `down_revision` in the new password reset migration.

2. **Does the project have a submit endpoint for questionnaires?**
   - What we know: The `Initiative` model has a `status` field with `InitiativeStatus.submitted`. The questionnaire.py router does not appear to have a `/submit` endpoint yet.
   - What's unclear: Whether a submit endpoint was added in a later plan or is expected to be added in this phase.
   - Recommendation: Check `backend/app/api/v1/questionnaire.py` for a submit endpoint. If absent, the UX-RESIL-03 (submission confirmation screen) plan must include creating `POST /questionnaire/initiatives/{id}/submit` that sets `status = submitted`.

3. **RESEND_API_KEY Railway env var — from email domain**
   - What we know: The `from` address in the reset email should match a verified domain in Resend. `noreply@coe-dsc.nl` is assumed but not confirmed.
   - What's unclear: Whether the coe-dsc.nl domain has been verified in Resend, or if the default Resend sandbox `onboarding@resend.dev` should be used for the demo.
   - Recommendation: Use `onboarding@resend.dev` (Resend's default sandbox) for demo, or document that the domain owner must verify `coe-dsc.nl` in the Resend dashboard before the `from` address works.

---

## Sources

### Primary (HIGH confidence)

- SQLAlchemy 2.0 Official Docs — https://docs.sqlalchemy.org/en/20/core/pooling.html — pool_size, max_overflow, pool_pre_ping, pool_recycle parameters verified
- Resend Python SDK GitHub — https://github.com/resend/resend-python — `resend.Emails.SendParams` and `resend.Emails.send()` API verified
- slowapi Official Docs — https://slowapi.readthedocs.io/ — `@limiter.limit()` decorator pattern, `Request` requirement verified
- TanStack Query v5 Reference — https://tanstack.com/query/v5/docs/react/reference/useMutation — `isPending`, `isError`, `isSuccess` return values confirmed
- TanStack Router v1 Docs — https://tanstack.com/router/v1/docs/framework/react/guide/authenticated-routes — `beforeLoad` + `redirect()` pattern confirmed
- Ant Design v6 Official Docs — https://ant.design/components/table/ + https://ant.design/components/popconfirm/ — Table + Popconfirm API confirmed
- FastAPI Custom Response Docs — https://fastapi.tiangolo.com/advanced/custom-response/ — StreamingResponse pattern confirmed
- Alembic Operations Docs — https://alembic.sqlalchemy.org/en/latest/ops.html — `op.add_column()` nullable pattern confirmed
- Project source files (read directly): `backend/app/db/session.py`, `backend/app/models/user.py`, `backend/app/api/v1/auth.py`, `backend/app/core/security.py`, `frontend/src/lib/api.ts`, `frontend/src/lib/auth.ts`, `frontend/package.json`, `backend/pyproject.toml`

### Secondary (MEDIUM confidence)

- SuperTokens Blog — https://supertokens.com/blog/implementing-a-forgot-password-flow — DB token vs JWT for password reset security tradeoff (multiple sources agree)
- Resend FastAPI Guide — https://resend.com/docs/send-with-fastapi — BackgroundTasks integration pattern
- FastAPI Background Tasks — https://fastapi.tiangolo.com/tutorial/background-tasks/ — official docs confirming `add_task()` pattern
- pythontutorials.net — https://www.pythontutorials.net/blog/how-to-properly-set-pool-size-and-max-overflow-in-sqlalchemy-for-asgi-app/ — pool sizing for ASGI with Uvicorn workers
- SQLModel Cascade Delete Docs — https://sqlmodel.tiangolo.com/tutorial/relationship-attributes/cascade-delete-relationships/ — ondelete pattern confirmed (but project uses manual delete order instead)

### Tertiary (LOW confidence — flag for validation)

- Resend Python SDK 2.0 changelog — https://resend.com/changelog/python-sdk-2-0 — SDK v2 released June 2024 with TypedDict params (used in `SendParams`) — verify exact `from_` vs `from` param name in current SDK version before coding (Python keyword conflict)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All libraries verified against official docs; codebase read directly to confirm versions
- DB pool tuning: HIGH — SQLAlchemy 2.0 official docs confirm exact parameter names and semantics
- Password reset flow: HIGH — DB token approach confirmed by multiple security sources; Resend SDK 2.x API confirmed
- Ant Design Table: HIGH — Official docs confirm v6 Table + Popconfirm pattern
- TanStack Query v5 mutations: HIGH — Official docs confirm `isPending` rename from `isLoading`
- TanStack Router admin guard: HIGH — Official docs confirm `beforeLoad` + `redirect()` pattern
- Architecture: HIGH — Derived directly from reading existing codebase patterns
- Pitfalls: MEDIUM-HIGH — Derived from official docs + known project decisions (STATE.md) + SQLAlchemy behavior docs

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (stable libraries; Resend SDK may have minor API changes — verify `from` param name)
