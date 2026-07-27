"""Unit tests for backend/app/services/admin_aggregation.py (ADMN-01).

Driven against a real Postgres session fixture (this module's raw SQL uses
Postgres-native LATERAL joins, same rationale as test_admin.py's D-01 note).
Covers `build_admin_aggregate`'s own behavior directly, separate from the
HTTP-level `/admin/heatmap` endpoint tests in tests/api/test_admin.py
(Task 2 of this plan).
"""

from app.models.assessment import AssessmentStatus
from app.services.admin_aggregation import build_admin_aggregate
from app.services.mami_config import load_dssc_questionnaire_config
from app.services.report_generator import generate_radar_svg
from tests.factories import make_assessment, make_initiative, make_user


def _config() -> dict:
    return load_dssc_questionnaire_config()


def _six_scores(value: float) -> list[dict]:
    return [
        {"category_id": cat["id"], "name": cat["name"], "score": value}
        for cat in _config()["categories"]
    ]


def _make_submitted_assessment_with_scores(session, *, initiative, scores: list[dict]):
    assessment = make_assessment(session, initiative=initiative, status=AssessmentStatus.submitted)
    assessment.dimension_scores = scores
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


def test_build_admin_aggregate_returns_expected_top_level_keys(session):
    result = build_admin_aggregate(session, _config())
    assert set(result.keys()) == {"org_average_scores", "org_radar_chart_svg", "initiatives"}


def test_latest_submitted_query_includes_draft_only_initiative_with_null_latest(session):
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    make_assessment(session, initiative=initiative, status=AssessmentStatus.draft)

    result = build_admin_aggregate(session, _config())
    row = next(r for r in result["initiatives"] if r["id"] == initiative.id)

    assert row["has_data"] is False
    assert row["dimension_scores"] is None
    assert row["overall_average"] is None
    assert row["report_assessment_id"] is None


def test_org_average_is_mean_across_two_submitted_initiatives(session):
    user_a = make_user(session)
    initiative_a = make_initiative(session, user=user_a)
    _make_submitted_assessment_with_scores(
        session, initiative=initiative_a, scores=_six_scores(2.0)
    )

    user_b = make_user(session)
    initiative_b = make_initiative(session, user=user_b)
    _make_submitted_assessment_with_scores(
        session, initiative=initiative_b, scores=_six_scores(4.0)
    )

    result = build_admin_aggregate(session, _config())

    assert result["org_average_scores"] != []
    for entry in result["org_average_scores"]:
        assert entry["score"] == 3.0
    assert result["org_radar_chart_svg"] is not None


def test_org_average_excludes_draft_only_initiative_no_zero_coercion(session):
    user_a = make_user(session)
    initiative_a = make_initiative(session, user=user_a)
    _make_submitted_assessment_with_scores(
        session, initiative=initiative_a, scores=_six_scores(4.0)
    )

    # A draft-only initiative must NOT drag the average toward 0.
    user_b = make_user(session)
    initiative_b = make_initiative(session, user=user_b)
    make_assessment(session, initiative=initiative_b, status=AssessmentStatus.draft)

    result = build_admin_aggregate(session, _config())

    for entry in result["org_average_scores"]:
        assert entry["score"] == 4.0


def test_zero_submitted_org_wide_suppresses_radar_and_average(session):
    user = make_user(session)
    initiative = make_initiative(session, user=user)
    make_assessment(session, initiative=initiative, status=AssessmentStatus.draft)

    result = build_admin_aggregate(session, _config())

    assert result["org_radar_chart_svg"] is None
    assert result["org_average_scores"] == []


def test_build_admin_aggregate_reuses_generate_radar_svg_not_reimplemented(session):
    # RPRT-01/D-01: same SVG-generating function used by individual reports —
    # confirmed by module-level import, not a second implementation.
    import app.services.admin_aggregation as admin_aggregation_module

    assert admin_aggregation_module.generate_radar_svg is generate_radar_svg
