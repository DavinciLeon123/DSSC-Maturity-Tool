"""Characterization tests for the assessment-first answer upsert flow
(backend/app/api/v1/questionnaire.py — Phase 13, D-06/D-07).

No test previously existed for PUT/GET
/questionnaire/initiatives/{id}/answers (pre-existing coverage gap, not
introduced by this plan) — added here since this plan reshapes the
endpoint's behavior significantly: an Assessment is now created lazily on
the first answer, and every answer/assessment lookup re-derives ownership
through Initiative.user_id (security V4).
"""

from sqlmodel import select

from app.models.assessment import Assessment, AssessmentStatus
from tests.factories import make_initiative, make_user

VALID_PASSWORD = "Str0ngPassw0rd!123"


def _login(client, email, password):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_upsert_answer_creates_draft_assessment_lazily(client, session):
    # D-06/D-07: no Assessment exists until the first answer write.
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    assert (
        session.exec(select(Assessment).where(Assessment.initiative_id == initiative.id)).first()
        is None
    )

    response = client.put(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/answers/q-1-1",
        json={"question_id": "q-1-1", "category_id": "cat-1", "score": 4},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category_id"] == "cat-1"
    assert body["score"] == 4
    assert body["question_id"] == "q-1-1"

    assessment = session.exec(
        select(Assessment).where(Assessment.initiative_id == initiative.id)
    ).first()
    assert assessment is not None
    assert assessment.status == AssessmentStatus.draft
    assert body["assessment_id"] == assessment.id


def test_upsert_answer_twice_updates_score_not_duplicate_row(client, session):
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    client.put(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/answers/q-1-1",
        json={"question_id": "q-1-1", "category_id": "cat-1", "score": 2},
    )
    second = client.put(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/answers/q-1-1",
        json={"question_id": "q-1-1", "category_id": "cat-1", "score": 5},
    )
    assert second.status_code == 200
    assert second.json()["score"] == 5

    # Reuses the same draft Assessment — does not create a second one.
    assessments = session.exec(
        select(Assessment).where(Assessment.initiative_id == initiative.id)
    ).all()
    assert len(assessments) == 1


def test_get_answers_returns_saved_answers_for_owner(client, session):
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    client.put(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/answers/q-1-1",
        json={"question_id": "q-1-1", "category_id": "cat-1", "score": 3},
    )

    response = client.get(f"/api/v1/questionnaire/initiatives/{initiative.id}/answers")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["question_id"] == "q-1-1"
    assert body[0]["score"] == 3


def test_get_answers_with_no_assessment_returns_empty_list(client, session):
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/questionnaire/initiatives/{initiative.id}/answers")
    assert response.status_code == 200
    assert response.json() == []


def test_upsert_answer_rejects_non_owner(client, session):
    # security V4 — a user cannot write an answer on another user's
    # initiative, re-derived through the ownership check before any
    # Assessment lookup/creation happens.
    owner = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=owner)

    other = make_user(session, password=VALID_PASSWORD)
    _login(client, other.email, VALID_PASSWORD)

    response = client.put(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/answers/q-1-1",
        json={"question_id": "q-1-1", "category_id": "cat-1", "score": 3},
    )
    assert response.status_code == 403

    # No Assessment should have been created as a side effect of the
    # rejected write.
    assert (
        session.exec(select(Assessment).where(Assessment.initiative_id == initiative.id)).first()
        is None
    )
