"""Performance test for the equal-weight dimension-scoring path (SCOR-01/02).

Measures p95 latency of compute_dimension_scores against a fully-answered
52-question assessment (6 categories). Uses pytest-benchmark to capture
timing across multiple runs and extract statistical percentiles.

This closes Phase 14's deferred IOU (see 14-04's deferred-items.md) — the
perf-gate job in pr.yml/staging.yml/main.yml can now run a real test rather
than tolerating exit-code-5 ("no tests collected").
"""

import pytest

from app.services.dimension_scoring import compute_dimension_scores
from app.services.mami_config import load_dssc_questionnaire_config
from tests.factories import make_user, make_initiative, make_assessment, make_answer

pytestmark = pytest.mark.perf

P95_BUDGET_SECONDS = 1.0


def test_dimension_scoring_p95_latency(benchmark, session):
    """Measure p95 latency of compute_dimension_scores on a fully-answered assessment."""
    # Setup: load config and create a complete assessment
    config = load_dssc_questionnaire_config()
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative)

    # Build one answer per question (52 total, all scored at 3)
    for cat in config["categories"]:
        for question in cat["questions"]:
            make_answer(
                session,
                initiative=initiative,
                assessment=assessment,
                question_id=question["id"],
                category_id=cat["id"],
                score=3,
            )

    # Benchmark the scoring call (setup above is not timed)
    def run_scoring():
        return compute_dimension_scores(session, assessment.id, config)

    result = benchmark(run_scoring)

    # Verify result shape: one entry per category, all with scores
    assert len(result) == 6
    for score_dict in result:
        assert "category_id" in score_dict
        assert "name" in score_dict
        assert "score" in score_dict
        assert 1.0 <= score_dict["score"] <= 5.0

    # Extract p95 from benchmark stats and assert it's within budget
    sorted_runs = benchmark.stats.stats.sorted_data
    p95 = sorted_runs[min(len(sorted_runs) - 1, int(len(sorted_runs) * 0.95))]
    assert p95 < P95_BUDGET_SECONDS, f"p95 latency {p95:.3f}s exceeds budget {P95_BUDGET_SECONDS}s"
