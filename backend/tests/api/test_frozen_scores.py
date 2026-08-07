"""Freeze-proof test for HIST-02 (gap-closure plan 15-07).

Proves the actual bug the verifier found: `compute_dimension_scores` used
to always recompute against the LIVE questionnaire config at read time.
Once a submitted assessment carries a frozen `dimension_scores` snapshot
(written by `submit_initiative`), a later edit to the live config must not
change what `GET /initiatives/{id}/assessments` returns for that already-
submitted version.

Mirrors test_assessment_history.py's client/session fixture usage and
login idiom. Answers are written through the real
`PUT /questionnaire/initiatives/{id}/answers/{question_id}` endpoint (not
seeded directly) and submission goes through the real
`POST /initiatives/{id}/submit` endpoint, so the snapshot is written by the
exact code path a real user exercises — not bypassed via direct session
manipulation like test_assessment_history.py's seeded rows.
"""

import copy
from datetime import datetime

from sqlmodel import select

from app.core.deps import get_dssc_questionnaire_config
from app.main import app
from app.models.assessment import Assessment, AssessmentStatus
from app.services.mami_config import load_dssc_questionnaire_config
from tests.factories import make_answer, make_assessment, make_initiative, make_user

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


def test_history_serves_frozen_snapshot_not_mutated_live_config(client, session):
    """Freeze proof: submit through the real endpoint (writing the
    snapshot), then mutate the LIVE config via dependency override and
    assert the history response still reflects the ORIGINAL category names/
    scores — proving the frozen snapshot is served, not a live recompute."""
    config = load_dssc_questionnaire_config()
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    _answer_all_questions_via_http(client, initiative.id, config, score=4)

    submit_response = client.post(f"/api/v1/initiatives/{initiative.id}/submit")
    assert submit_response.status_code == 200

    # Assert the snapshot was actually written to the DB by the real submit
    # path — not just that the history endpoint happens to look right.
    assessment = session.exec(
        select(Assessment).where(
            Assessment.initiative_id == initiative.id,
            Assessment.status == AssessmentStatus.submitted,
        )
    ).first()
    assert assessment is not None
    assert assessment.dimension_scores is not None
    assert len(assessment.dimension_scores) == 6
    original_names = {d["category_id"]: d["name"] for d in assessment.dimension_scores}
    assert original_names == {cat["id"]: cat["name"] for cat in config["categories"]}

    # Simulate config drift: mutate a deep copy so the real config object
    # (and file) is never touched, then serve it via a dependency override
    # for the duration of the history GET only.
    mutated_config = copy.deepcopy(config)
    mutated_config["categories"][0]["name"] = "MUTATED CATEGORY NAME"
    # Also trim a category's question list, changing what a live recompute's
    # divisor would be (a second, independent signal of live-vs-frozen).
    mutated_config["categories"][1]["questions"] = mutated_config["categories"][1]["questions"][:1]

    app.dependency_overrides[get_dssc_questionnaire_config] = lambda: mutated_config
    try:
        history_response = client.get(f"/api/v1/initiatives/{initiative.id}/assessments")
    finally:
        app.dependency_overrides.pop(get_dssc_questionnaire_config, None)

    assert history_response.status_code == 200
    body = history_response.json()
    assert len(body) == 1
    returned_names = {d["category_id"]: d["name"] for d in body[0]["dimension_scores"]}

    # The ORIGINAL name is what's returned — NOT the mutated live-config name.
    assert returned_names == original_names
    assert "MUTATED CATEGORY NAME" not in returned_names.values()
    assert len(body[0]["dimension_scores"]) == 6
    assert all(d["score"] == 4 for d in body[0]["dimension_scores"])
    assert body[0]["overall_average"] == 4


def test_history_falls_back_to_live_compute_for_legacy_row_without_snapshot(client, session):
    """Negative control: a directly-seeded submitted row with
    dimension_scores=None (the legacy shape, predating this column) still
    falls back to a live recompute — documents the intended legacy path."""
    config = load_dssc_questionnaire_config()
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)

    assessment = make_assessment(session, initiative=initiative, status=AssessmentStatus.draft)
    for cat in config["categories"]:
        for question in cat["questions"]:
            make_answer(
                session,
                initiative=initiative,
                assessment=assessment,
                question_id=question["id"],
                category_id=cat["id"],
                score=2,
            )
    assessment.status = AssessmentStatus.submitted
    assessment.submitted_at = datetime.utcnow()
    assert assessment.dimension_scores is None
    session.add(assessment)
    session.commit()

    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/assessments")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert len(body[0]["dimension_scores"]) == 6
    assert all(d["score"] == 2 for d in body[0]["dimension_scores"])
    assert body[0]["overall_average"] == 2
