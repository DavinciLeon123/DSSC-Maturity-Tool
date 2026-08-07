"""Integration tests for POST /api/v1/initiatives/{id}/score (D-04, SCOR-04).

First-ever automated coverage for this endpoint (test_scoring.py did not
previously exist). Mirrors test_reports.py's client/session fixture usage
and ownership/422 assertion idiom. Question/category ids are driven from
the real config/dssc-questionnaire.json (via `load_dssc_questionnaire_config`)
rather than hardcoded, so these tests keep passing unchanged once the
placeholder config is replaced with real content (QSTN-05).
"""

from app.services.mami_config import load_dssc_questionnaire_config
from tests.factories import make_answer, make_assessment, make_initiative, make_user

VALID_PASSWORD = "Str0ngPassw0rd!123"


def _login(client, email, password):
    """Authenticate the shared `client` fixture as a specific user.

    /score checks `initiative.user_id == current_user.id`, so tests need a
    client bound to the SAME user that owns the initiative — the plain
    `client` fixture from conftest.py is otherwise anonymous.
    """
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _answer_all_questions(session, initiative, assessment, config, *, skip=None):
    """Answer every question in `config` for `assessment`, optionally
    skipping one question id (for the incomplete-assessment test)."""
    for cat in config["categories"]:
        for question in cat["questions"]:
            if skip is not None and question["id"] == skip:
                continue
            make_answer(
                session,
                initiative=initiative,
                assessment=assessment,
                question_id=question["id"],
                category_id=cat["id"],
                score=3,
            )


def test_score_returns_dimension_scores(client, session):
    """Happy path: a fully-answered initiative's owner gets 200 with the new
    per-dimension shape — 6 entries, every score in [1.0, 5.0] — and the old
    ZEN/MoSCoW findings shape is gone."""
    config = load_dssc_questionnaire_config()
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative)
    _answer_all_questions(session, initiative, assessment, config)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/score")

    assert response.status_code == 200
    body = response.json()
    assert body["initiative_id"] == initiative.id
    assert "dimension_scores" in body
    assert len(body["dimension_scores"]) == 6
    assert all(1.0 <= d["score"] <= 5.0 for d in body["dimension_scores"])
    assert all({"category_id", "name", "score"} == set(d.keys()) for d in body["dimension_scores"])
    # Old ZEN/MoSCoW response shape must be gone (D-04)
    assert "findings" not in body
    assert "critical_count" not in body
    assert "non_critical_count" not in body
    assert "total_answers" not in body


def test_score_422_when_incomplete(client, session):
    """An assessment missing at least one answer gets 422, not 200 all-zeros
    (SCOR-04, this is NEW behavior — RESEARCH Pitfall 2)."""
    config = load_dssc_questionnaire_config()
    first_question_id = config["categories"][0]["questions"][0]["id"]
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative)
    _answer_all_questions(session, initiative, assessment, config, skip=first_question_id)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/score")

    assert response.status_code == 422
    assert response.json()["detail"] == "Questionnaire not fully answered"


def test_score_422_when_no_assessment_exists(client, session):
    """An initiative with no draft assessment at all (no answers ever
    written) also gets 422, not 200 all-zeros."""
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/score")

    assert response.status_code == 422
    assert response.json()["detail"] == "Questionnaire not fully answered"


def test_score_ownership_before_completion_gate(client, session):
    """A different user requesting someone else's (incomplete) initiative
    gets 403 — NOT 422 — proving the ownership check fires before the
    completion gate (T-14-01)."""
    owner = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=owner)
    # Deliberately leave the initiative's assessment incomplete/nonexistent
    # — if ownership did not fire first, this would otherwise 422.

    other_user = make_user(session, password=VALID_PASSWORD)
    _login(client, other_user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/score")

    assert response.status_code in (403, 404)
    assert response.status_code != 422
