"""Admin endpoints — protected by require_admin() dependency.

All endpoints require ADMIN role. Available via GET/DELETE/POST on /api/v1/admin/*.
"""
import csv
import io
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select, delete as sql_delete
from sqlalchemy import func, text
from datetime import datetime

from app.db.session import get_session
from app.core.deps import require_admin
from app.models.user import User
from app.models.initiative import Initiative
from app.models.questionnaire import QuestionnaireAnswer
from app.models.evidence import EvidenceURL
from app.models.report import ComplianceReport
from app.services.report_generator import _build_topic_structure

router = APIRouter(prefix="/admin", tags=["admin"])


# ─── Admin heatmap response models ────────────────────────────────────────────

class AdminHeatmapCell(BaseModel):
    yes: int = 0
    not_yet: int = 0
    n_a: int = 0


class AdminHeatmapResponse(BaseModel):
    total_submitted: int
    matrix: Dict[str, Dict[str, Dict[str, AdminHeatmapCell]]]
    topic_structure: Dict[str, List[dict]]


# ─── Response schemas ─────────────────────────────────────────────────────────

class AdminUserRow(BaseModel):
    id: int
    email: str
    role: str
    participant_type: str
    created_at: str
    initiative_name: Optional[str] = None
    initiative_status: Optional[str] = None
    answer_count: int = 0


class AdminInitiativeRow(BaseModel):
    id: int
    user_email: str
    name: str
    participant_type: str
    status: str
    created_at: str
    answer_count: int


# ─── Cascade delete helpers ────────────────────────────────────────────────────

def _delete_initiative_children(initiative_id: int, session: Session) -> None:
    """Delete all child rows of an initiative in correct FK order.
    Models have no ondelete=CASCADE — must delete children manually."""
    session.exec(sql_delete(QuestionnaireAnswer).where(
        QuestionnaireAnswer.initiative_id == initiative_id
    ))
    session.exec(sql_delete(EvidenceURL).where(
        EvidenceURL.initiative_id == initiative_id
    ))
    session.exec(sql_delete(ComplianceReport).where(
        ComplianceReport.initiative_id == initiative_id
    ))


def _delete_user_cascade(user_id: int, session: Session) -> None:
    """Hard-delete a user and all their data. Children must be deleted before parent."""
    initiative = session.exec(
        select(Initiative).where(Initiative.user_id == user_id)
    ).first()
    if initiative:
        _delete_initiative_children(initiative.id, session)
        session.delete(initiative)
    user = session.get(User, user_id)
    if user:
        session.delete(user)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/users", response_model=List[AdminUserRow])
def list_users(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """List all registered users with their initiative status."""
    # Use raw SQL to avoid enum deserialization errors on legacy data
    result = session.execute(text("""
        SELECT u.id, u.email, u.role, u.participant_type, u.created_at,
               i.name AS initiative_name, i.status AS initiative_status, i.id AS initiative_id
        FROM "user" u
        LEFT JOIN initiative i ON i.user_id = u.id
        ORDER BY u.created_at DESC
    """))
    rows = []
    for row in result.mappings():
        initiative_id = row["initiative_id"]
        answer_count = 0
        if initiative_id:
            count_result = session.execute(
                text("SELECT COUNT(*) FROM questionnaire_answer WHERE initiative_id = :iid"),
                {"iid": initiative_id}
            )
            answer_count = count_result.scalar() or 0
        rows.append(AdminUserRow(
            id=row["id"],
            email=row["email"],
            role=row["role"],
            participant_type=row["participant_type"],
            created_at=row["created_at"].isoformat(),
            initiative_name=row["initiative_name"],
            initiative_status=row["initiative_status"],
            answer_count=answer_count,
        ))
    return rows


@router.delete("/users/{user_id}", status_code=200)
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """Hard-delete a user and all their data (initiative, answers, evidence, report)."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "ADMIN":
        raise HTTPException(status_code=403, detail="Cannot delete admin users")
    _delete_user_cascade(user_id, session)
    session.commit()
    return {"message": f"User {user.email} and all their data deleted"}


@router.get("/initiatives", response_model=List[AdminInitiativeRow])
def list_initiatives(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """List all initiatives with owner email, status, and answer count."""
    # Use raw SQL to avoid enum deserialization errors on legacy data
    result = session.execute(text("""
        SELECT i.id, i.name, i.participant_type, i.status, i.created_at,
               u.email AS user_email,
               COUNT(qa.id) AS answer_count
        FROM initiative i
        LEFT JOIN "user" u ON u.id = i.user_id
        LEFT JOIN questionnaire_answer qa ON qa.initiative_id = i.id
        GROUP BY i.id, i.name, i.participant_type, i.status, i.created_at, u.email
        ORDER BY i.created_at DESC
    """))
    rows = []
    for row in result.mappings():
        rows.append(AdminInitiativeRow(
            id=row["id"],
            user_email=row["user_email"] or "unknown",
            name=row["name"],
            participant_type=row["participant_type"],
            status=row["status"],
            created_at=row["created_at"].isoformat(),
            answer_count=row["answer_count"] or 0,
        ))
    return rows


@router.delete("/initiatives/{initiative_id}", status_code=200)
def delete_initiative(
    initiative_id: int,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """Delete an initiative and its child rows (answers, evidence, report) without deleting the user."""
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
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

    Note: evidence URLs are stored in a separate EvidenceURL table and are not
    included in this export. The CSV contains one row per questionnaire answer.
    """

    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        # Header row — columns reflect what is actually populated
        writer.writerow([
            "user_email", "initiative_name", "participant_type", "initiative_status",
            "question_id", "mami_code", "answer_value", "followup_selections", "followup_other",
        ])
        output.seek(0)
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)

        # Use raw SQL to avoid enum deserialization errors on legacy data
        rows = session.execute(text("""
            SELECT u.email, i.name AS initiative_name, i.participant_type, i.status,
                   qa.question_id, qa.mami_code, qa.answer_value,
                   qa.followup_selections, qa.followup_other
            FROM "user" u
            JOIN initiative i ON i.user_id = u.id
            JOIN questionnaire_answer qa ON qa.initiative_id = i.id
            ORDER BY u.email, i.id, qa.question_id
        """))

        for row in rows.mappings():
            selections = row["followup_selections"]
            selections_str = "; ".join(selections) if selections else ""
            writer.writerow([
                row["email"],
                row["initiative_name"],
                row["participant_type"],
                row["status"],
                row["question_id"],
                row["mami_code"],
                row["answer_value"],
                selections_str,
                row["followup_other"] or "",
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


@router.post("/reset-demo", status_code=200)
def reset_demo(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """Delete all non-admin users and all their data. DESTRUCTIVE.

    Used by demo organizer to clean up between demo runs.
    Admin users are never deleted.
    """
    non_admin_users = session.exec(
        select(User).where(User.role != "ADMIN")
    ).all()
    count = len(non_admin_users)
    for user in non_admin_users:
        _delete_user_cascade(user.id, session)
    session.commit()
    return {"message": f"Demo reset complete. Deleted {count} users and all their data.", "deleted_users": count}


@router.get("/heatmap", response_model=AdminHeatmapResponse)
def get_admin_heatmap(
    request: Request,
    type: Optional[str] = None,   # "dsi" or "sp" — None means all types
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """Aggregate yes/not_yet/n_a counts per heatmap cell across all submitted initiatives."""
    type_filter = "AND LOWER(i.participant_type) = :ptype" if type else ""
    params: dict = {"ptype": type.lower()} if type else {}

    # Count submitted initiatives (alias 'i' matches type_filter which uses i.participant_type)
    count_result = session.execute(
        text(f"SELECT COUNT(*) FROM initiative i WHERE i.status = 'submitted' {type_filter}"),
        params,
    )
    total_submitted = int(count_result.scalar() or 0)

    # Aggregate answer counts per (mami_code, answer_value) for submitted initiatives only
    agg_result = session.execute(text(f"""
        SELECT qa.mami_code, qa.answer_value, COUNT(*) as cnt
        FROM questionnaire_answer qa
        JOIN initiative i ON i.id = qa.initiative_id
        WHERE i.status = 'submitted' {type_filter}
        GROUP BY qa.mami_code, qa.answer_value
    """), params)

    # Build counts dict: {mami_code: {answer_value: count}}
    counts: dict = {}
    for row in agg_result.mappings():
        code = row["mami_code"]
        val = row["answer_value"]
        cnt = int(row["cnt"])
        counts.setdefault(code, {})
        counts[code][val] = cnt

    # Load mami_config and build topic structure
    mami_config = request.app.state.mami_config
    topic_structure = _build_topic_structure(mami_config)

    # Build code lookup: {code_id: {dimension: dim_key, category: cat_key}}
    # mami_config uses a flat codes array with category, dimension, topic fields
    code_lookup: dict = {}
    for code in mami_config.get("codes", []):
        code_lookup[code["id"]] = {
            "dimension": code.get("dimension", ""),
            "category": code.get("category", ""),
            "topic": code.get("topic", ""),
        }

    # Collect all unique dimension keys from the config
    dimensions = list(dict.fromkeys(
        c.get("dimension", "") for c in mami_config.get("codes", []) if c.get("dimension")
    ))

    # Build matrix: {cat: {dim: {topic_id: AdminHeatmapCell}}}
    matrix: dict = {}
    for cat_key, topics in topic_structure.items():
        matrix.setdefault(cat_key, {})
        for dim_key in dimensions:
            matrix[cat_key].setdefault(dim_key, {})
            for topic in topics:
                topic_id = topic["topic_id"]
                yes_total = not_yet_total = na_total = 0
                for code_id in topic.get("codes", []):
                    meta = code_lookup.get(code_id, {})
                    if meta.get("dimension") != dim_key or meta.get("category") != cat_key:
                        continue
                    code_counts = counts.get(code_id, {})
                    yes_total += code_counts.get("yes", 0)
                    not_yet_total += code_counts.get("not_there_yet", 0)
                    na_total += code_counts.get("not_applicable", 0)
                matrix[cat_key][dim_key][topic_id] = AdminHeatmapCell(
                    yes=yes_total,
                    not_yet=not_yet_total,
                    n_a=na_total,
                )

    return AdminHeatmapResponse(
        total_submitted=total_submitted,
        matrix=matrix,
        topic_structure=topic_structure,
    )
