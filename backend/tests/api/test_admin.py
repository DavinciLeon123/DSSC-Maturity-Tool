"""Characterization tests for admin user/initiative management
(backend/app/api/v1/admin.py).

Per D-01, these tests run against a real Postgres instance (raw `text()` SQL
in list_users/list_initiatives/export_dataset/get_admin_heatmap operates on
Postgres-native ENUM columns SQLite cannot faithfully reproduce). Per D-04,
current behavior is characterized and pinned as the regression baseline;
any bug discovered while writing these tests is logged in the SUMMARY as a
backlog item, not fixed inline.
"""

import csv
import io

import pytest
from sqlmodel import select

from app.models.evidence import EvidenceURL
from app.models.questionnaire import QuestionnaireAnswer
from app.models.report import ComplianceReport
from tests.factories import (
    make_answer,
    make_evidence,
    make_initiative,
    make_report,
    make_submitted_initiative,
    make_user,
)

# ---------------------------------------------------------------------------
# Task 1: Access-control boundary + list_users / list_initiatives
# ---------------------------------------------------------------------------

ADMIN_ENDPOINTS = [
    ("GET", "/api/v1/admin/users"),
    ("GET", "/api/v1/admin/initiatives"),
    ("GET", "/api/v1/admin/export"),
    ("GET", "/api/v1/admin/heatmap"),
    ("DELETE", "/api/v1/admin/users/999999"),
    ("DELETE", "/api/v1/admin/initiatives/999999"),
    ("POST", "/api/v1/admin/reset-demo"),
]


@pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
def test_admin_endpoints_reject_plain_user_token_with_403(user_client, method, path):
    # Pins T-12-03-PRIV (STRIDE: Elevation of Privilege): every admin
    # endpoint depends on require_admin — a plain USER-role token must be
    # rejected with 403 on all of them, not just some. Parametrized so a
    # future endpoint that forgets require_admin fails this suite loudly.
    response = user_client.request(method, path)
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_list_users_returns_initiative_and_answer_fields(admin_client, session):
    user_a = make_user(session)
    initiative_a = make_initiative(session, user=user_a)
    make_answer(session, initiative=initiative_a)
    make_answer(session, initiative=initiative_a)

    user_b = make_user(session)
    initiative_b = make_initiative(session, user=user_b)
    make_answer(session, initiative=initiative_b)

    response = admin_client.get("/api/v1/admin/users")
    assert response.status_code == 200
    rows_by_email = {row["email"]: row for row in response.json()}

    row_a = rows_by_email[user_a.email]
    assert row_a["initiative_name"] == initiative_a.name
    assert row_a["initiative_status"] == initiative_a.status.value
    assert row_a["answer_count"] == 2

    row_b = rows_by_email[user_b.email]
    assert row_b["initiative_name"] == initiative_b.name
    assert row_b["initiative_status"] == initiative_b.status.value
    assert row_b["answer_count"] == 1


def test_list_initiatives_returns_user_email_and_answer_count(admin_client, session):
    user_a = make_user(session)
    initiative_a = make_initiative(session, user=user_a)
    make_answer(session, initiative=initiative_a)
    make_answer(session, initiative=initiative_a)
    make_answer(session, initiative=initiative_a)

    user_b = make_user(session)
    initiative_b = make_initiative(session, user=user_b)

    response = admin_client.get("/api/v1/admin/initiatives")
    assert response.status_code == 200
    rows_by_name = {row["name"]: row for row in response.json()}

    row_a = rows_by_name[initiative_a.name]
    assert row_a["user_email"] == user_a.email
    assert row_a["answer_count"] == 3

    row_b = rows_by_name[initiative_b.name]
    assert row_b["user_email"] == user_b.email
    assert row_b["answer_count"] == 0


# ---------------------------------------------------------------------------
# Task 2: Cascade-delete + CSV export + heatmap
# ---------------------------------------------------------------------------


def test_delete_user_cascades_all_child_rows(admin_client, session):
    # Pins T-12-03-CASCADE (STRIDE: Tampering) — _delete_user_cascade's
    # manual FK-order delete must leave zero orphaned rows in ALL three
    # child tables, not just return a 200. RESEARCH.md Pattern 4.
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    make_answer(session, initiative=initiative)
    make_answer(session, initiative=initiative)
    make_evidence(session, initiative=initiative)
    make_report(session, initiative=initiative)

    initiative_id = initiative.id
    user_id = user.id

    response = admin_client.delete(f"/api/v1/admin/users/{user_id}")
    assert response.status_code == 200

    assert (
        session.exec(
            select(QuestionnaireAnswer).where(QuestionnaireAnswer.initiative_id == initiative_id)
        ).all()
        == []
    )
    assert (
        session.exec(select(EvidenceURL).where(EvidenceURL.initiative_id == initiative_id)).all()
        == []
    )
    assert (
        session.exec(
            select(ComplianceReport).where(ComplianceReport.initiative_id == initiative_id)
        ).all()
        == []
    )


def test_delete_user_missing_returns_404(admin_client):
    response = admin_client.delete("/api/v1/admin/users/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_delete_user_target_is_admin_returns_403(admin_client, session):
    # Pins T-12-03-ADMINDEL — deleting an ADMIN-role target must be
    # rejected, guarding against removing the last admin.
    target_admin = make_user(session, role="ADMIN")

    response = admin_client.delete(f"/api/v1/admin/users/{target_admin.id}")
    assert response.status_code == 403
    assert response.json()["detail"] == "Cannot delete admin users"


def test_delete_initiative_removes_children_but_keeps_user(admin_client, session):
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    make_answer(session, initiative=initiative)
    make_evidence(session, initiative=initiative)

    initiative_id = initiative.id
    user_id = user.id

    response = admin_client.delete(f"/api/v1/admin/initiatives/{initiative_id}")
    assert response.status_code == 200

    assert (
        session.exec(
            select(QuestionnaireAnswer).where(QuestionnaireAnswer.initiative_id == initiative_id)
        ).all()
        == []
    )
    assert (
        session.exec(select(EvidenceURL).where(EvidenceURL.initiative_id == initiative_id)).all()
        == []
    )
    # The user itself must survive — only the initiative and its children
    # are removed by delete_initiative.
    from app.models.user import User

    assert session.get(User, user_id) is not None


def test_export_dataset_csv_shape(admin_client, session):
    # D-04 characterization lock: the exact 9-column header list, flagged
    # for Phase 13 to update deliberately when answer_value's ENUM changes.
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    make_answer(session, initiative=initiative)
    make_answer(session, initiative=initiative)
    make_answer(session, initiative=initiative)

    response = admin_client.get("/api/v1/admin/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    reader = csv.reader(io.StringIO(response.text))
    header = next(reader)
    assert header == [
        "user_email",
        "initiative_name",
        "participant_type",
        "initiative_status",
        "question_id",
        "mami_code",
        "answer_value",
        "followup_selections",
        "followup_other",
    ]
    rows = list(reader)
    assert len(rows) == 3


def test_admin_heatmap_reflects_submitted_initiatives(admin_client, session):
    # Pitfall 1: this test proves the lifespan-populated app.state.mami_config
    # path works (admin_client is built via the lifespan-aware TestClient).
    user = make_user(session)
    initiative = make_submitted_initiative(session, user=user)
    make_answer(session, initiative=initiative)

    response = admin_client.get("/api/v1/admin/heatmap")
    assert response.status_code == 200
    body = response.json()
    assert body["total_submitted"] >= 1
    assert "matrix" in body
    assert "topic_structure" in body
