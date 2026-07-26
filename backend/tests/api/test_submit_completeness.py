"""Regression coverage for the SCOR-04 completeness gate on POST
/initiatives/{id}/submit (gap-closure plan 15-08, 15-VERIFICATION.md Gap 1).

Before this gate existed, `submit_initiative` would freeze a permanent
`dimension_scores` snapshot from an arbitrarily incomplete draft (e.g. 1 of
52 questions answered) and return 200 — permanently locking in a garbage
version with no correction path short of a destructive full retake. These
tests drive the real HTTP path (real `PUT` answers, real `POST /submit`, no
direct DB status flips), mirroring test_frozen_scores.py's style, so the
gate is proven against the exact code path a real user exercises.
"""

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
    endpoint, so the draft Assessment this creates/uses is indistinguishable
    from a real user's session."""
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


def test_submit_422_when_incomplete(client, session):
    """A draft with only one question answered gets 422, not 200 with a
    permanently frozen garbage snapshot (SCOR-04, the bug 15-VERIFICATION.md
    flagged)."""
    config = load_dssc_questionnaire_config()
    first_question = config["categories"][0]["questions"][0]
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    put_response = client.put(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/answers/{first_question['id']}",
        json={
            "question_id": first_question["id"],
            "category_id": config["categories"][0]["id"],
            "score": 4,
        },
    )
    assert put_response.status_code == 200

    submit_response = client.post(f"/api/v1/initiatives/{initiative.id}/submit")

    assert submit_response.status_code == 422
    assert submit_response.json()["detail"] == "Questionnaire not fully answered"

    # Prove the incomplete submit did NOT lock the initiative: another
    # answer still saves (200, not 403) since no freeze/submitted flip
    # happened.
    second_question = config["categories"][0]["questions"][1]
    unlocked_put = client.put(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/answers/{second_question['id']}",
        json={
            "question_id": second_question["id"],
            "category_id": config["categories"][0]["id"],
            "score": 2,
        },
    )
    assert unlocked_put.status_code == 200


def test_submit_200_when_complete(client, session):
    """A fully-answered draft still submits successfully (200) and freezes
    the snapshot, exactly as before this gate was added."""
    config = load_dssc_questionnaire_config()
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    _answer_all_questions_via_http(client, initiative.id, config)

    submit_response = client.post(f"/api/v1/initiatives/{initiative.id}/submit")

    assert submit_response.status_code == 200


def test_submit_idempotent_resubmit_stays_200(client, session):
    """Re-submitting an already-submitted initiative (no draft assessment
    remains) still returns 200 — the completeness gate must be skipped, not
    re-run as a spurious 422, on the idempotent path."""
    config = load_dssc_questionnaire_config()
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    _answer_all_questions_via_http(client, initiative.id, config)

    first_submit = client.post(f"/api/v1/initiatives/{initiative.id}/submit")
    assert first_submit.status_code == 200

    second_submit = client.post(f"/api/v1/initiatives/{initiative.id}/submit")
    assert second_submit.status_code == 200
