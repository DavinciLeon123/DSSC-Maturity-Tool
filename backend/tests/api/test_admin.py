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

from app.models.assessment import Assessment, AssessmentStatus
from app.models.questionnaire import QuestionnaireAnswer
from app.models.report import ComplianceReport
from app.services.mami_config import load_dssc_questionnaire_config
from tests.factories import (
    make_answer,
    make_assessment,
    make_initiative,
    make_report,
    make_user,
)


def _config() -> dict:
    return load_dssc_questionnaire_config()


def _six_scores(value: float) -> list[dict]:
    return [
        {"category_id": cat["id"], "name": cat["name"], "score": value}
        for cat in _config()["categories"]
    ]


def _submit_with_scores(session, *, initiative, scores: list[dict]):
    assessment = make_assessment(session, initiative=initiative, status=AssessmentStatus.submitted)
    assessment.dimension_scores = scores
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


def _answers_for_initiative(session, initiative_id: int) -> list[QuestionnaireAnswer]:
    """D-06: questionnaire_answer keys off assessment_id now — join through
    Assessment to fetch answers for an initiative, same as the app itself."""
    return session.exec(
        select(QuestionnaireAnswer)
        .join(Assessment, QuestionnaireAnswer.assessment_id == Assessment.id)
        .where(Assessment.initiative_id == initiative_id)
    ).all()


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
    # manual FK-order delete must leave zero orphaned rows in all child
    # tables, not just return a 200. RESEARCH.md Pattern 4. (Evidence-table
    # cascade removed per MIGR-02 — the evidence subsystem no longer exists.)
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    make_answer(session, initiative=initiative)
    make_answer(session, initiative=initiative)
    make_report(session, initiative=initiative)

    initiative_id = initiative.id
    user_id = user.id

    response = admin_client.delete(f"/api/v1/admin/users/{user_id}")
    assert response.status_code == 200

    assert _answers_for_initiative(session, initiative_id) == []
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

    initiative_id = initiative.id
    user_id = user.id

    response = admin_client.delete(f"/api/v1/admin/initiatives/{initiative_id}")
    assert response.status_code == 200

    assert _answers_for_initiative(session, initiative_id) == []
    # The user itself must survive — only the initiative and its children
    # are removed by delete_initiative.
    from app.models.user import User

    assert session.get(User, user_id) is not None


def test_export_dataset_csv_shape(admin_client, session):
    # D-04 characterization lock, updated deliberately this phase (D-02/D-06):
    # mami_code/answer_value/followup_* no longer exist on the new-schema
    # answer table — replaced by category_id/score.
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
        "category_id",
        "score",
    ]
    rows = list(reader)
    assert len(rows) == 3


def test_admin_heatmap_returns_org_aggregate_and_per_initiative_rows(admin_client, session):
    # ADMN-01/D-07/D-08: real 6-dimension aggregation replaces the Phase 14
    # fixed degraded stub. Two submitted initiatives (all-2 / all-4) plus a
    # draft-only initiative that must appear with has_data=False and never
    # drag the org average toward zero.
    user_a = make_user(session)
    initiative_a = make_initiative(session, user=user_a)
    assessment_a = _submit_with_scores(session, initiative=initiative_a, scores=_six_scores(2.0))

    user_b = make_user(session)
    initiative_b = make_initiative(session, user=user_b)
    assessment_b = _submit_with_scores(session, initiative=initiative_b, scores=_six_scores(4.0))

    user_c = make_user(session)
    initiative_c = make_initiative(session, user=user_c)
    make_assessment(session, initiative=initiative_c, status=AssessmentStatus.draft)

    response = admin_client.get("/api/v1/admin/heatmap")
    assert response.status_code == 200
    body = response.json()

    assert body["org_average_scores"] != []
    for entry in body["org_average_scores"]:
        assert entry["score"] == 3.0
    assert body["org_radar_chart_svg"] is not None
    assert "<svg" in body["org_radar_chart_svg"]

    rows_by_id = {row["id"]: row for row in body["initiatives"]}

    row_a = rows_by_id[initiative_a.id]
    assert row_a["has_data"] is True
    assert row_a["report_assessment_id"] == assessment_a.id
    assert row_a["overall_average"] == 2.0
    assert row_a["dimension_scores"] is not None

    row_b = rows_by_id[initiative_b.id]
    assert row_b["has_data"] is True
    assert row_b["report_assessment_id"] == assessment_b.id
    assert row_b["overall_average"] == 4.0

    row_c = rows_by_id[initiative_c.id]
    assert row_c["has_data"] is False
    assert row_c["dimension_scores"] is None
    assert row_c["overall_average"] is None
    assert row_c["report_assessment_id"] is None


def test_admin_heatmap_empty_org_suppresses_radar_and_average(admin_client, session):
    # RESEARCH Pitfall 5: zero submitted assessments org-wide must suppress
    # the radar (None), never render an all-zero degenerate hexagon.
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    make_assessment(session, initiative=initiative, status=AssessmentStatus.draft)

    response = admin_client.get("/api/v1/admin/heatmap")
    assert response.status_code == 200
    body = response.json()
    assert body["org_radar_chart_svg"] is None
    assert body["org_average_scores"] == []
