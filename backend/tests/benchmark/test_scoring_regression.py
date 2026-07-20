"""Heavier regression gate — included in staging/main CI, excluded from the PR gate to keep
PR feedback fast (see pytest.mark.benchmark in pyproject.toml).

Locks in the scoring engine's output distribution over a larger synthetic answer set, so an
unintended change to config/scoring/mami-scoring.json's decision rules gets caught before it
reaches staging or main.
"""

import asyncio
from collections import Counter

import pytest

from app.services.scoring_engine import create_scoring_engine, score_all_answers

pytestmark = pytest.mark.benchmark

ANSWER_COUNT = 500


def test_score_all_answers_output_distribution(make_answers):
    engine = create_scoring_engine()
    answers = make_answers(ANSWER_COUNT)

    findings = asyncio.run(score_all_answers(engine, answers))

    severities = Counter(f["severity"] for f in findings)

    # Golden counts for this synthetic answer set — regenerate deliberately (not silently)
    # if config/scoring/mami-scoring.json's decision rules intentionally change.
    assert severities == Counter({"CRITICAL": 83, "NON_CRITICAL": 84})
