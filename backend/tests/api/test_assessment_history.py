"""Integration tests for GET /api/v1/initiatives/{id}/assessments (HIST-02).

First-ever automated coverage for the new greenfield history endpoint.
Mirrors test_scoring.py's/test_reports.py's client/session fixture usage and
ownership/404/403 assertion idiom. Question/category ids are driven from the
real config/dssc-questionnaire.json (via `load_dssc_questionnaire_config`)
rather than hardcoded, matching the established convention in this test
suite.

Submitted assessments are seeded directly via the session (constructing
`Assessment` rows with explicit `version`/`status`/`submitted_at`) rather
than the factory's `make_assessment` (which only builds draft rows) or the
real HTTP retake flow — this lets each test control distinct version
numbers per initiative without colliding on the new (initiative_id, version)
uniqueness Plan 15-01 introduces elsewhere in this phase.

Per RESEARCH Pitfall 5: `list_submitted_assessments` (the helper this route
calls) must never surface a draft assessment as if it were a submitted
version — one of the cases below asserts exactly that.
"""

from datetime import datetime, timedelta

from app.models.assessment import Assessment, AssessmentStatus
from app.services.dimension_scoring import compute_dimension_scores
from app.services.mami_config import load_dssc_questionnaire_config
from tests.factories import make_answer, make_initiative, make_user

VALID_PASSWORD = "Str0ngPassw0rd!123"


def _login(client, email, password):
    """Authenticate the shared `client` fixture as a specific user.

    The history endpoint checks `initiative.user_id == current_user.id`, so
    tests need a client bound to the SAME user that owns the initiative —
    the plain `client` fixture from conftest.py is otherwise anonymous.
    """
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _make_submitted_assessment(session, *, initiative, version, submitted_at=None) -> Assessment:
    """Build a SUBMITTED Assessment with an explicit version — the factory's
    `make_assessment` only ever builds draft-default rows and has no version
    parameter, so this test file constructs the row directly."""
    assessment = Assessment(
        initiative_id=initiative.id,
        version=version,
        status=AssessmentStatus.submitted,
        submitted_at=submitted_at or datetime.utcnow(),
    )
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


def _answer_all_questions(session, initiative, assessment, config, *, score=3):
    """Fully answer every question in `config` for `assessment` so
    compute_dimension_scores has real data for all 6 categories."""
    for cat in config["categories"]:
        for question in cat["questions"]:
            make_answer(
                session,
                initiative=initiative,
                assessment=assessment,
                question_id=question["id"],
                category_id=cat["id"],
                score=score,
            )


def test_assessment_history_empty_list_when_no_submissions(client, session):
    """An owner with zero submitted assessments gets 200 and an empty list
    (never a 404, never a draft masquerading as a version)."""
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/assessments")

    assert response.status_code == 200
    assert response.json() == []


def test_assessment_history_ordered_by_version_with_correct_scores(client, session):
    """Two submitted assessments (distinct versions 1 and 2) are returned
    ordered by version, each with the correct overall_average and 6
    dimension_scores matching a direct compute_dimension_scores call."""
    config = load_dssc_questionnaire_config()
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)

    # Version 2 is created/submitted "later" but with an earlier submitted_at
    # timestamp than version 1 would suggest, proving ordering is by
    # version, not submitted_at.
    now = datetime.utcnow()
    assessment_v1 = _make_submitted_assessment(
        session, initiative=initiative, version=1, submitted_at=now - timedelta(days=1)
    )
    _answer_all_questions(session, initiative, assessment_v1, config, score=2)

    assessment_v2 = _make_submitted_assessment(
        session, initiative=initiative, version=2, submitted_at=now
    )
    _answer_all_questions(session, initiative, assessment_v2, config, score=4)

    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/assessments")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert [item["version"] for item in body] == [1, 2]

    for item, assessment, expected_score in (
        (body[0], assessment_v1, 2),
        (body[1], assessment_v2, 4),
    ):
        assert item["id"] == assessment.id
        assert item["submitted_at"] != ""
        assert len(item["dimension_scores"]) == 6
        assert all(d["score"] == expected_score for d in item["dimension_scores"])
        assert item["overall_average"] == expected_score

        direct_scores = compute_dimension_scores(session, assessment.id, config)
        assert item["dimension_scores"] == direct_scores


def test_assessment_history_excludes_draft_assessment(client, session):
    """A draft (not-yet-submitted) retake must never appear in the history
    list alongside submitted versions (RESEARCH Pitfall 5)."""
    config = load_dssc_questionnaire_config()
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)

    submitted = _make_submitted_assessment(session, initiative=initiative, version=1)
    _answer_all_questions(session, initiative, submitted, config)

    draft = Assessment(initiative_id=initiative.id, version=2, status=AssessmentStatus.draft)
    session.add(draft)
    session.commit()
    session.refresh(draft)
    _answer_all_questions(session, initiative, draft, config)

    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/assessments")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == submitted.id
    assert body[0]["version"] == 1


def test_assessment_history_non_owner_forbidden(client, session):
    """A different user requesting someone else's history gets 403."""
    owner = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=owner)

    other_user = make_user(session, password=VALID_PASSWORD)
    _login(client, other_user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/assessments")

    assert response.status_code == 403


def test_assessment_history_missing_initiative_returns_404(client, session):
    """A non-existent initiative id returns 404."""
    user = make_user(session, password=VALID_PASSWORD)
    _login(client, user.email, VALID_PASSWORD)

    response = client.get("/api/v1/initiatives/999999/assessments")

    assert response.status_code == 404
