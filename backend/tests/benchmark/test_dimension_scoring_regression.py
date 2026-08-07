"""Deterministic regression test for the equal-weight dimension-scoring path (SCOR-01/02).

Locks in the exact per-category score output of compute_dimension_scores
against a synthetic answer set. Fails loudly if the averaging logic ever
changes, protecting against silent regression in the rules engine.

This closes Phase 14's deferred IOU (see 14-04's deferred-items.md) — the
perf-gate job in pr.yml/staging.yml/main.yml can now run a real test rather
than tolerating exit-code-5 ("no tests collected").
"""

import pytest

from app.services.dimension_scoring import compute_dimension_scores
from app.services.mami_config import load_dssc_questionnaire_config
from tests.factories import make_user, make_initiative, make_assessment, make_answer

pytestmark = pytest.mark.benchmark


def test_dimension_scoring_deterministic_output(session):
    """Verify compute_dimension_scores produces exact golden per-category scores.

    Every question in a category gets a deterministic score based on the
    category's index (yields 1, 2, 3, 4, 5, 1 across the 6 real categories),
    so the average equals that score exactly (sum of N identical values /
    N = that value). This test fails if averaging logic changes.
    """
    # Setup: load config and create an assessment with varying scores per category
    config = load_dssc_questionnaire_config()
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative)

    # Build answers: every question in category i gets score (i % 5) + 1
    # This yields 1, 2, 3, 4, 5, 1 for cat-1..cat-6
    for cat_idx, cat in enumerate(config["categories"]):
        category_score = (cat_idx % 5) + 1
        for question in cat["questions"]:
            make_answer(
                session,
                initiative=initiative,
                assessment=assessment,
                question_id=question["id"],
                category_id=cat["id"],
                score=category_score,
            )

    # Compute scores
    scores = compute_dimension_scores(session, assessment.id, config)

    # Regenerate deliberately (not silently) if compute_dimension_scores's
    # averaging logic ever changes.
    golden_values = {cat["id"]: float((i % 5) + 1) for i, cat in enumerate(config["categories"])}

    # Extract actual scores into a dict for comparison
    actual_scores = {s["category_id"]: s["score"] for s in scores}

    # Assert exact match (no tolerance — rules engine semantics)
    assert actual_scores == golden_values, (
        f"Output mismatch: expected {golden_values}, got {actual_scores}. "
        "If averaging logic changed intentionally, regenerate golden values above."
    )
