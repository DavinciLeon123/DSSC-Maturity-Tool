"""Admin endpoints — protected by require_admin() dependency.

All endpoints require ADMIN role. Available via GET/DELETE/POST on /api/v1/admin/*.
"""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session, select
from sqlmodel import delete as sql_delete

from app.core.deps import require_admin
from app.db.session import get_session
from app.models.assessment import Assessment
from app.models.initiative import Initiative
from app.models.questionnaire import QuestionnaireAnswer
from app.models.report import ComplianceReport
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


# ─── Admin heatmap response models ────────────────────────────────────────────


class AdminHeatmapResponse(BaseModel):
    """Phase 14 (D-01b): reduced to a fixed, deliberately trivial degraded
    response. The MAMI-matrix aggregation this endpoint used to build is
    gone entirely — Phase 16 (ADMN-01) rebuilds this against the new
    6-category dimension-score model."""

    degraded: bool = True
    cells: list[dict] = []


# ─── Response schemas ─────────────────────────────────────────────────────────


class AdminUserRow(BaseModel):
    id: int
    email: str
    role: str
    participant_type: str | None  # D-12/Pitfall 5 — nullable on the model now
    created_at: str
    initiative_name: str | None = None
    initiative_status: str | None = None
    answer_count: int = 0


class AdminInitiativeRow(BaseModel):
    id: int
    user_email: str
    name: str
    participant_type: str | None  # D-12/Pitfall 5 — nullable on the model now
    status: str
    created_at: str
    answer_count: int


# ─── Cascade delete helpers ────────────────────────────────────────────────────


def _delete_initiative_children(initiative_id: int, session: Session) -> None:
    """Delete all child rows of an initiative in correct FK order.
    Models have no ondelete=CASCADE — must delete children manually.

    D-06: questionnaire_answer is now keyed by assessment_id, not
    initiative_id directly — answers must be deleted before their
    Assessment(s), which must be deleted before the Initiative itself.
    (This deliberately does NOT touch questionnaire_answer_v1_archive —
    archived legacy rows have no FK to initiative and must survive an
    admin hard-delete of the initiative, RESEARCH Anti-Pattern / A2.)
    """
    # SQLModel has no mypy plugin, so `Model.field == value` type-checks as plain `bool`
    # here instead of `ColumnElement[bool]` — the query itself is the standard SQLModel pattern.
    assessment_ids = session.exec(
        select(Assessment.id).where(Assessment.initiative_id == initiative_id)
    ).all()
    if assessment_ids:
        session.exec(
            sql_delete(QuestionnaireAnswer).where(
                QuestionnaireAnswer.assessment_id.in_(assessment_ids)  # type: ignore[attr-defined]
            )
        )
        session.exec(sql_delete(Assessment).where(Assessment.initiative_id == initiative_id))  # type: ignore[arg-type]
    session.exec(
        sql_delete(ComplianceReport).where(ComplianceReport.initiative_id == initiative_id)  # type: ignore[arg-type]
    )


def _delete_user_cascade(user_id: int, session: Session) -> None:
    """Hard-delete a user and all their data. Children must be deleted before parent."""
    initiative = session.exec(select(Initiative).where(Initiative.user_id == user_id)).first()
    if initiative:
        assert initiative.id is not None  # loaded from an existing DB row
        _delete_initiative_children(initiative.id, session)
        session.delete(initiative)
    user = session.get(User, user_id)
    if user:
        session.delete(user)


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/users", response_model=list[AdminUserRow])
def list_users(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """List all registered users with their initiative status."""
    # Use raw SQL to avoid enum deserialization errors on legacy data
    result = session.execute(
        text("""
        SELECT u.id, u.email, u.role, u.participant_type, u.created_at,
               i.name AS initiative_name, i.status AS initiative_status, i.id AS initiative_id
        FROM "user" u
        LEFT JOIN initiative i ON i.user_id = u.id
        ORDER BY u.created_at DESC
    """)
    )
    rows = []
    for row in result.mappings():
        initiative_id = row["initiative_id"]
        answer_count = 0
        if initiative_id:
            # D-06: questionnaire_answer keys off assessment_id, not
            # initiative_id — join through assessment to count answers.
            count_result = session.execute(
                text("""
                    SELECT COUNT(*) FROM questionnaire_answer qa
                    JOIN assessment a ON a.id = qa.assessment_id
                    WHERE a.initiative_id = :iid
                """),
                {"iid": initiative_id},
            )
            answer_count = count_result.scalar() or 0
        rows.append(
            AdminUserRow(
                id=row["id"],
                email=row["email"],
                role=row["role"],
                participant_type=row["participant_type"],
                created_at=row["created_at"].isoformat(),
                initiative_name=row["initiative_name"],
                initiative_status=row["initiative_status"],
                answer_count=answer_count,
            )
        )
    return rows


@router.delete("/users/{user_id}", status_code=200)
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """Hard-delete a user and all their data (initiative, answers, report)."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "ADMIN":
        raise HTTPException(status_code=403, detail="Cannot delete admin users")
    _delete_user_cascade(user_id, session)
    session.commit()
    return {"message": f"User {user.email} and all their data deleted"}


@router.get("/initiatives", response_model=list[AdminInitiativeRow])
def list_initiatives(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """List all initiatives with owner email, status, and answer count."""
    # Use raw SQL to avoid enum deserialization errors on legacy data.
    # D-06: questionnaire_answer keys off assessment_id, not initiative_id —
    # join through assessment to count answers per initiative.
    result = session.execute(
        text("""
        SELECT i.id, i.name, i.participant_type, i.status, i.created_at,
               u.email AS user_email,
               COUNT(qa.id) AS answer_count
        FROM initiative i
        LEFT JOIN "user" u ON u.id = i.user_id
        LEFT JOIN assessment a ON a.initiative_id = i.id
        LEFT JOIN questionnaire_answer qa ON qa.assessment_id = a.id
        GROUP BY i.id, i.name, i.participant_type, i.status, i.created_at, u.email
        ORDER BY i.created_at DESC
    """)
    )
    rows = []
    for row in result.mappings():
        rows.append(
            AdminInitiativeRow(
                id=row["id"],
                user_email=row["user_email"] or "unknown",
                name=row["name"],
                participant_type=row["participant_type"],
                status=row["status"],
                created_at=row["created_at"].isoformat(),
                answer_count=row["answer_count"] or 0,
            )
        )
    return rows


@router.delete("/initiatives/{initiative_id}", status_code=200)
def delete_initiative(
    initiative_id: int,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """Delete an initiative and its child rows (answers, report), keeping the user."""
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    assert initiative.id is not None  # loaded from an existing DB row
    _delete_initiative_children(initiative.id, session)
    session.delete(initiative)
    session.commit()
    return {"message": f"Initiative '{initiative.name}' and all its data deleted"}


@router.get("/export")
def export_dataset(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """Stream all initiatives + answers as a CSV file download.

    The CSV contains one row per questionnaire answer.
    """

    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        # Header row — columns reflect what is actually populated.
        # D-02/D-06: mami_code/answer_value/followup_* no longer exist on the
        # new-schema answer table — replaced by category_id/score. Legacy
        # v1.0 answers are preserved read-only in
        # questionnaire_answer_v1_archive (D-01/D-04, DB-level access only,
        # no export/endpoint this phase) and are intentionally NOT included
        # in this export.
        writer.writerow(
            [
                "user_email",
                "initiative_name",
                "participant_type",
                "initiative_status",
                "question_id",
                "category_id",
                "score",
            ]
        )
        output.seek(0)
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)

        # Use raw SQL to avoid enum deserialization errors on legacy data
        rows = session.execute(
            text("""
            SELECT u.email, i.name AS initiative_name, i.participant_type, i.status,
                   qa.question_id, qa.category_id, qa.score
            FROM "user" u
            JOIN initiative i ON i.user_id = u.id
            JOIN assessment a ON a.initiative_id = i.id
            JOIN questionnaire_answer qa ON qa.assessment_id = a.id
            ORDER BY u.email, i.id, qa.question_id
        """)
        )

        for row in rows.mappings():
            writer.writerow(
                [
                    row["email"],
                    row["initiative_name"],
                    row["participant_type"],
                    row["status"],
                    row["question_id"],
                    row["category_id"],
                    row["score"],
                ]
            )
            output.seek(0)
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mami-dataset.csv"},
    )


@router.post("/reset-demo", status_code=200)
def reset_demo(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """Delete all non-admin users and all their data. DESTRUCTIVE.

    Used by demo organizer to clean up between demo runs.
    Admin users are never deleted.
    """
    non_admin_users = session.exec(select(User).where(User.role != "ADMIN")).all()
    count = len(non_admin_users)
    for user in non_admin_users:
        assert user.id is not None  # loaded from an existing DB row
        _delete_user_cascade(user.id, session)
    session.commit()
    return {
        "message": f"Demo reset complete. Deleted {count} users and all their data.",
        "deleted_users": count,
    }


@router.get("/heatmap", response_model=AdminHeatmapResponse)
def get_admin_heatmap(
    request: Request,
    type: str | None = None,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """Fixed, deliberately trivial degraded response (D-01b).

    The MAMI-matrix aggregation this endpoint used to build (keyed off the
    legacy mami_code/answer_value shape) is deleted outright along with the
    ZEN/MoSCoW subsystem it depended on — Phase 16 (ADMN-01) rebuilds this
    endpoint against the new 6-category dimension-score model.
    """
    return AdminHeatmapResponse(degraded=True, cells=[])
