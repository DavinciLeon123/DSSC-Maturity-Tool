"""Dedicated perf gate (pytest -m perf), run as its own CI job, separate from the main test job.

Starter threshold only — tune once real production answer-set sizes and SLOs are known.
"""

import asyncio

import pytest

from app.services.scoring_engine import create_scoring_engine, score_all_answers

pytestmark = pytest.mark.perf

ANSWER_COUNT = 50
P95_BUDGET_SECONDS = 1.0


def test_score_all_answers_p95(benchmark, make_answers):
    engine = create_scoring_engine()
    answers = make_answers(ANSWER_COUNT)

    def run():
        return asyncio.run(score_all_answers(engine, answers))

    benchmark(run)

    sorted_runs = benchmark.stats.stats.sorted_data
    p95_index = min(len(sorted_runs) - 1, int(len(sorted_runs) * 0.95))
    p95 = sorted_runs[p95_index]
    assert p95 < P95_BUDGET_SECONDS, (
        f"scoring {ANSWER_COUNT} answers: p95 {p95:.3f}s exceeds budget {P95_BUDGET_SECONDS}s"
    )
