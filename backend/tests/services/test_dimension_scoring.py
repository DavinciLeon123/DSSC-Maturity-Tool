"""Unit tests for backend/app/services/dimension_scoring.py (SCOR-01/02/04).

Pure-service tests against the real Postgres `session` fixture and the
`make_assessment`/`make_answer` factories — no HTTP client needed (mirrors
`test_report_generator.py`'s fixture style). Question/category ids are
loaded from the real `config/dssc-questionnaire.json` via
`load_dssc_questionnaire_config()` rather than hardcoded, so these tests
keep passing unchanged once the placeholder config is replaced with real
content (QSTN-05).
"""

import pytest
from fastapi import HTTPException

from app.services.dimension_scoring import (
    assert_assessment_complete,
    compute_dimension_scores,
    get_current_assessment,
)
from app.services.mami_config import load_dssc_questionnaire_config
from tests.factories import make_answer, make_assessment, make_initiative, make_user


def _config() -> dict:
    return load_dssc_questionnaire_config()


def _answer_all_questions(session, initiative, assessment, config, *, score_for=None, skip=None):
    """Answer every question in `config` for `assessment`, scoring each via
    `score_for(question_id, category_id) -> int` (defaults to a fixed 3),
    optionally skipping one question id entirely (for the incomplete-gate
    tests)."""
    score_for = score_for or (lambda qid, cat_id: 3)
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
                score=score_for(question["id"], cat["id"]),
            )


def test_full_assessment_scores_per_category(session):
    """SCOR-01: every category scores exactly the fixed per-answer value
    when fully answered with that value, within [1.0, 5.0], and dimension
    scores come back in stable config category order."""
    config = _config()
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative)
    _answer_all_questions(session, initiative, assessment, config, score_for=lambda q, c: 4)

    scores = compute_dimension_scores(session, assessment.id, config)

    expected_category_ids = [cat["id"] for cat in config["categories"]]
    assert [s["category_id"] for s in scores] == expected_category_ids
    for entry in scores:
        assert entry["score"] == 4.0
        assert 1.0 <= entry["score"] <= 5.0


def test_full_assessment_all_ones_and_all_fives(session):
    """SCOR-01 boundary: an all-1s category scores 1.0, an all-5s category
    scores 5.0 — both within the closed [1.0, 5.0] range."""
    config = _config()
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative)

    def score_for(question_id: str, category_id: str) -> int:
        return 1 if category_id == "cat-1" else 5

    _answer_all_questions(session, initiative, assessment, config, score_for=score_for)

    scores = compute_dimension_scores(session, assessment.id, config)
    by_id = {s["category_id"]: s["score"] for s in scores}
    assert by_id["cat-1"] == 1.0
    assert all(v == 5.0 for k, v in by_id.items() if k != "cat-1")


def test_equal_weight_across_different_question_counts(session):
    """SCOR-02: a 9-question category (cat-1) and an 8-question category
    (cat-5) answered with the same per-answer value each average to the
    same score — proving no cross-category weighting/denominator sharing."""
    config = _config()
    counts = {cat["id"]: len(cat["questions"]) for cat in config["categories"]}
    assert counts["cat-1"] == 9
    assert counts["cat-5"] == 8

    user = make_user(session)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative)
    _answer_all_questions(session, initiative, assessment, config, score_for=lambda q, c: 3)

    scores = compute_dimension_scores(session, assessment.id, config)
    by_id = {s["category_id"]: s["score"] for s in scores}
    assert by_id["cat-1"] == by_id["cat-5"] == 3.0


def test_precision_rounds_to_two_decimals(session):
    """A category whose true mean is non-terminating (30/9 = 3.333...) is
    rounded to exactly 2 decimal places via Python's round() — no
    truncation/ceil/floor."""
    config = _config()
    cat1 = next(cat for cat in config["categories"] if cat["id"] == "cat-1")
    assert len(cat1["questions"]) == 9

    user = make_user(session)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative)

    # 6 questions scored 3, 3 questions scored 4 -> sum 30 / 9 = 3.3333...
    for i, question in enumerate(cat1["questions"]):
        make_answer(
            session,
            initiative=initiative,
            assessment=assessment,
            question_id=question["id"],
            category_id="cat-1",
            score=4 if i < 3 else 3,
        )

    scores = compute_dimension_scores(session, assessment.id, config)
    by_id = {s["category_id"]: s["score"] for s in scores}
    assert by_id["cat-1"] == 3.33


def test_incomplete_assessment_raises_422(session):
    """SCOR-04: leaving exactly one config question unanswered still
    raises HTTPException(422) with the shared generic detail message."""
    config = _config()
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative)
    first_question_id = config["categories"][0]["questions"][0]["id"]
    _answer_all_questions(session, initiative, assessment, config, skip=first_question_id)

    with pytest.raises(HTTPException) as exc_info:
        assert_assessment_complete(session, initiative.id, config)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Questionnaire not fully answered"


def test_no_draft_assessment_raises_422(session):
    """SCOR-04: an initiative with no draft assessment at all (no answers
    ever written) raises HTTPException(422)."""
    config = _config()
    user = make_user(session)
    initiative = make_initiative(session, user=user)

    assert get_current_assessment(session, initiative.id) is None

    with pytest.raises(HTTPException) as exc_info:
        assert_assessment_complete(session, initiative.id, config)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Questionnaire not fully answered"


def test_complete_assessment_returns_assessment(session):
    """A fully-answered assessment passes the gate and returns the same
    Assessment row (no re-query needed by callers)."""
    config = _config()
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative)
    _answer_all_questions(session, initiative, assessment, config)

    result = assert_assessment_complete(session, initiative.id, config)

    assert result.id == assessment.id
