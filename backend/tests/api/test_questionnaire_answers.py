"""Characterization tests for the assessment-first answer upsert flow
(backend/app/api/v1/questionnaire.py — Phase 13, D-06/D-07).

No test previously existed for PUT/GET
/questionnaire/initiatives/{id}/answers (pre-existing coverage gap, not
introduced by this plan) — added here since this plan reshapes the
endpoint's behavior significantly: an Assessment is now created lazily on
the first answer, and every answer/assessment lookup re-derives ownership
through Initiative.user_id (security V4).
"""

from datetime import datetime

from sqlmodel import select

from app.api.v1.questionnaire import get_user_or_ip_key
from app.core.security import create_access_token
from app.models.assessment import Assessment, AssessmentStatus
from tests.factories import make_assessment, make_initiative, make_user

VALID_PASSWORD = "Str0ngPassw0rd!123"


class _StubRequest:
    """Minimal stand-in for a FastAPI/Starlette Request — get_user_or_ip_key
    only ever touches `.headers.get(...)` and (via slowapi's
    get_remote_address fallback) `.client.host`. Used to unit-test the key
    function directly rather than only through an HTTP round-trip, per
    RESEARCH.md Pitfall 1's explicit warning that a per-user key function
    must be tested this way to catch a Depends()-based mismatch early."""

    def __init__(self, *, authorization: str | None = None, client_host: str = "203.0.113.5"):
        self.headers = {"Authorization": authorization} if authorization else {}

        class _Client:
            def __init__(self, host: str) -> None:
                self.host = host

        self.client = _Client(client_host)


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


# ---------------------------------------------------------------------------
# SAVE-03: get_user_or_ip_key direct unit tests (RESEARCH Pitfall 1 — must be
# tested by calling the function directly, not just via HTTP, since slowapi's
# key_func receives only the raw Request and a Depends()-based mismatch would
# only surface at decoration/call time).
# ---------------------------------------------------------------------------


def test_rate_limit_key_uses_bearer_token_email(session):
    user = make_user(session, password=VALID_PASSWORD)
    token = create_access_token(user.email)
    request = _StubRequest(authorization=f"Bearer {token}")

    assert get_user_or_ip_key(request) == f"user:{user.email}"


def test_rate_limit_key_falls_back_to_ip_without_token():
    request = _StubRequest(authorization=None, client_host="198.51.100.7")
    assert get_user_or_ip_key(request) == "198.51.100.7"


def test_rate_limit_key_falls_back_to_ip_for_malformed_token():
    request = _StubRequest(authorization="Bearer not-a-real-token", client_host="198.51.100.9")
    assert get_user_or_ip_key(request) == "198.51.100.9"


def test_rate_limit_key_is_idempotent_for_same_token(session):
    # Two calls for the same user's token must return the identical key, so
    # both saves from one user count against a single shared bucket.
    user = make_user(session, password=VALID_PASSWORD)
    token = create_access_token(user.email)
    request = _StubRequest(authorization=f"Bearer {token}")

    assert get_user_or_ip_key(request) == get_user_or_ip_key(request)


def test_rate_limit_key_distinct_users_never_collide(session):
    user_a = make_user(session, password=VALID_PASSWORD)
    user_b = make_user(session, password=VALID_PASSWORD)
    token_a = create_access_token(user_a.email)
    token_b = create_access_token(user_b.email)
    key_a = get_user_or_ip_key(_StubRequest(authorization=f"Bearer {token_a}"))
    key_b = get_user_or_ip_key(_StubRequest(authorization=f"Bearer {token_b}"))

    assert key_a != key_b
    assert key_a == f"user:{user_a.email}"
    assert key_b == f"user:{user_b.email}"


# ---------------------------------------------------------------------------
# HIST-01/D-15: version-increment on retake
# ---------------------------------------------------------------------------


def test_version_increment_on_retake_after_prior_submission(client, session):
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    # First answer creates a draft Assessment at version 1.
    first = client.put(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/answers/q-1-1",
        json={"question_id": "q-1-1", "category_id": "cat-1", "score": 4},
    )
    assert first.status_code == 200
    first_assessment_id = first.json()["assessment_id"]

    first_assessment = session.get(Assessment, first_assessment_id)
    assert first_assessment is not None
    assert first_assessment.version == 1

    # Flip that assessment to submitted directly (simulating a completed
    # first submission) without flipping the Initiative itself, so a
    # subsequent answer-save PUT is still permitted (initiative-level
    # submission-lock is a separate concern from this plan's scope).
    first_assessment.status = AssessmentStatus.submitted
    first_assessment.submitted_at = datetime.utcnow()
    session.add(first_assessment)
    session.commit()

    # A new answer now must land on a fresh draft at version == 2, never a
    # hardcoded 1 (D-15/HIST-01) — and the first (submitted) row is
    # untouched (D-14: no answers carried forward, prior version immutable).
    second = client.put(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/answers/q-1-2",
        json={"question_id": "q-1-2", "category_id": "cat-1", "score": 2},
    )
    assert second.status_code == 200
    second_assessment_id = second.json()["assessment_id"]
    assert second_assessment_id != first_assessment_id

    second_assessment = session.get(Assessment, second_assessment_id)
    assert second_assessment is not None
    assert second_assessment.version == 2
    assert second_assessment.status == AssessmentStatus.draft

    # The first (submitted) assessment row is untouched.
    session.refresh(first_assessment)
    assert first_assessment.version == 1
    assert first_assessment.status == AssessmentStatus.submitted


# ---------------------------------------------------------------------------
# D-08: dedicated last-viewed-category endpoint — writes unconditionally,
# independent of any answer save.
# ---------------------------------------------------------------------------


def test_last_viewed_category_updates_with_zero_answers_saved(client, session):
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative)
    _login(client, user.email, VALID_PASSWORD)

    response = client.patch(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/last-viewed-category",
        json={"category_id": "cat-4"},
    )
    assert response.status_code == 200
    assert response.json()["last_viewed_category_id"] == "cat-4"

    session.refresh(assessment)
    assert assessment.last_viewed_category_id == "cat-4"
    # Proves the write is unconditional — no answer exists on this
    # assessment at all, yet the category still persisted.
    assert (
        session.exec(select(Assessment).where(Assessment.initiative_id == initiative.id)).one()
        is assessment
    )


def test_last_viewed_category_creates_draft_lazily_if_none_exists(client, session):
    # A user who opens the wizard and navigates categories before ever
    # answering a question still gets a resumable draft (D-08 must not be
    # gated on an Assessment already existing).
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    assert (
        session.exec(select(Assessment).where(Assessment.initiative_id == initiative.id)).first()
        is None
    )

    response = client.patch(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/last-viewed-category",
        json={"category_id": "cat-2"},
    )
    assert response.status_code == 200

    assessment = session.exec(
        select(Assessment).where(Assessment.initiative_id == initiative.id)
    ).one()
    assert assessment.last_viewed_category_id == "cat-2"
    assert assessment.version == 1


def test_last_viewed_category_rejects_non_owner(client, session):
    owner = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=owner)

    other = make_user(session, password=VALID_PASSWORD)
    _login(client, other.email, VALID_PASSWORD)

    response = client.patch(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/last-viewed-category",
        json={"category_id": "cat-1"},
    )
    assert response.status_code == 403
