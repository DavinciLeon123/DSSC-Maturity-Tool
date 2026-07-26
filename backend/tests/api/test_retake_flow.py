"""End-to-end retake-flow test (HIST-01 gap closure — 15-VERIFICATION.md Gap 1).

Unlike test_version_increment_on_retake_after_prior_submission in
test_questionnaire_answers.py (which bypasses the real HTTP path by flipping
Assessment.status directly in the DB session), every test here drives the
actual POST /submit and POST /retake endpoints. This is the real-HTTP proof
the verifier flagged as missing: submit locks editing, retake unlocks it and
creates a new version, and the prior submitted version stays immutable.
"""

from app.models.assessment import Assessment, AssessmentStatus
from app.models.initiative import InitiativeStatus
from app.services.mami_config import load_dssc_questionnaire_config
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


def _answer_all_questions_via_http(client, initiative_id, config, *, score=3):
    """Fully answer every question in `config` through the real PUT
    endpoint (mirrors test_frozen_scores.py) so a submit against this draft
    legitimately passes the SCOR-04 completeness gate (gap-closure 15-08)."""
    for cat in config["categories"]:
        for question in cat["questions"]:
            response = client.put(
                f"/api/v1/questionnaire/initiatives/{initiative_id}/answers/{question['id']}",
                json={
                    "question_id": question["id"],
                    "category_id": cat["id"],
                    "score": score,
                },
            )
            assert response.status_code == 200


def test_submit_then_retake_unlocks_editing_and_creates_v2_draft(client, session):
    """Test A (happy path): submit locks editing; retake unlocks it and
    creates version 2; the prior submitted version stays immutable."""
    config = load_dssc_questionnaire_config()
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    # First answer creates a draft Assessment at version 1.
    put_v1 = client.put(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/answers/q-1-1",
        json={"question_id": "q-1-1", "category_id": "cat-1", "score": 4},
    )
    assert put_v1.status_code == 200
    v1_assessment_id = put_v1.json()["assessment_id"]

    # Gap-closure 15-08: submit now enforces the SCOR-04 completeness gate,
    # so the rest of the config must be answered before a legitimate 200.
    _answer_all_questions_via_http(client, initiative.id, config)

    # Real HTTP submit — flips both Initiative.status AND the draft
    # Assessment to submitted.
    submit_response = client.post(f"/api/v1/initiatives/{initiative.id}/submit")
    assert submit_response.status_code == 200

    # Proves the lock is real (not the old test's direct-DB-flip bypass):
    # a further answer save now 403s.
    locked_put = client.put(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/answers/q-1-2",
        json={"question_id": "q-1-2", "category_id": "cat-1", "score": 3},
    )
    assert locked_put.status_code == 403

    # Real HTTP retake — the explicit action that unlocks editing.
    retake_response = client.post(f"/api/v1/initiatives/{initiative.id}/retake")
    assert retake_response.status_code == 201
    retake_body = retake_response.json()
    assert retake_body["version"] == 2

    # The lock is gone: the same question can now be saved again, 200 not 403.
    unlocked_put = client.put(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/answers/q-1-1",
        json={"question_id": "q-1-1", "category_id": "cat-1", "score": 5},
    )
    assert unlocked_put.status_code == 200
    unlocked_body = unlocked_put.json()
    assert unlocked_body["assessment_id"] != v1_assessment_id

    new_assessment = session.get(Assessment, unlocked_body["assessment_id"])
    assert new_assessment is not None
    assert new_assessment.version == 2
    assert new_assessment.status == AssessmentStatus.draft

    # The original v1 assessment row is completely untouched.
    v1_assessment = session.get(Assessment, v1_assessment_id)
    assert v1_assessment is not None
    assert v1_assessment.version == 1
    assert v1_assessment.status == AssessmentStatus.submitted

    # Initiative.status is back to draft.
    session.refresh(initiative)
    assert initiative.status == InitiativeStatus.draft


def test_retake_on_never_submitted_initiative_returns_409(client, session):
    """Test B (guard): retake on a draft-in-progress initiative is rejected,
    so a draft is never silently version-bumped (D-13/T-15-06-03)."""
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/retake")
    assert response.status_code == 409


def test_retake_rejects_non_owner(client, session):
    """Test C (ownership): a different user cannot retake someone else's
    initiative (security V4/T-15-06-01)."""
    config = load_dssc_questionnaire_config()
    owner = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=owner)
    _login(client, owner.email, VALID_PASSWORD)
    # Gap-closure 15-08: submit now enforces the SCOR-04 completeness gate.
    _answer_all_questions_via_http(client, initiative.id, config)
    submit_response = client.post(f"/api/v1/initiatives/{initiative.id}/submit")
    assert submit_response.status_code == 200

    other = make_user(session, password=VALID_PASSWORD)
    _login(client, other.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/retake")
    assert response.status_code == 403
