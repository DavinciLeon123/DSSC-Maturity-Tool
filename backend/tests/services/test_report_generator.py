"""Pure-function unit tests for backend/app/services/report_generator.py.

Phase 14 (D-01a/D-05): all MAMI-matrix/heatmap/recommendation builders are
deleted from report_generator.py along with the ZEN/MoSCoW subsystem they
served.

Phase 16 (RPRT-01/02/03/04, Plan 16-02 Task 2): `generate_html_report` is
rewritten to take the shared report-contract keys
(`dimension_scores`/`priority_list`/`radar_chart_svg`/`maturity_bands`)
directly — the same 4 keys `build_report_contract` returns for the JSON
response (RPRT-04, one payload two renderings). The old
`generate_report_data` helper (initiative-info-only JSON assembly) is
removed outright — fully superseded by `build_report_contract`, which
callers (reports.py) now call directly — so its tests are removed too.

Phase 16 (RPRT-01/02/03): adds the Wave-0 smoke net for the new pure
functions — `get_maturity_band`, `build_priority_list`, `generate_radar_svg`
— driven from the real `config/dssc-questionnaire.json` (never a hardcoded
question id or band threshold literal beyond the boundary values under
test), mirroring `test_dimension_scoring.py`'s config-comprehension style.
Broader coverage is Phase 17 (TEST-01/02)'s job.
"""

from app.services.mami_config import load_dssc_questionnaire_config
from app.services.report_generator import (
    build_priority_list,
    generate_html_report,
    generate_radar_svg,
    get_maturity_band,
)


def _config() -> dict:
    return load_dssc_questionnaire_config()


def _bands() -> list[dict]:
    return _config()["maturity_bands"]


def _six_scores(
    *, value: float | None = None, values: dict[str, float] | None = None
) -> list[dict]:
    """Build a 6-entry scores list ({category_id, name, score}) from the
    real config, either a fixed value for every category or a per-category
    override dict keyed by category_id."""
    config = _config()
    values = values or {}
    return [
        {
            "category_id": cat["id"],
            "name": cat["name"],
            "score": values.get(cat["id"], value if value is not None else 3.0),
        }
        for cat in config["categories"]
    ]


def test_generate_html_report_renders_non_empty_html_with_initiative_name():
    """Proves Jinja2 rendering runs end-to-end with the new contract-shaped
    context (dimension_scores/priority_list/radar_chart_svg/maturity_bands)
    without raising UndefinedError. The template itself is rebuilt in this
    plan's Task 3 to actually render `radar_chart_svg`/`priority_list` — see
    test_reports.py's contract-parity test for that stronger assertion."""
    initiative = {
        "name": "Acme Dataspace",
        "organization": "Acme Corp",
        "contact_name": "Jane Doe",
        "participant_type": "DSI",
    }
    bands = _bands()
    scores = _six_scores(value=3.0)
    priority_list = build_priority_list(scores, bands)
    radar_chart_svg = generate_radar_svg(scores, bands)

    html = generate_html_report(
        initiative=initiative,
        generated_at="24 July 2026, 12:00 UTC",
        dimension_scores=scores,
        priority_list=priority_list,
        radar_chart_svg=radar_chart_svg,
        maturity_bands=bands,
    )

    assert isinstance(html, str)
    assert len(html) > 0
    assert "Acme Dataspace" in html
    assert "24 July 2026, 12:00 UTC" in html


def test_maturity_band_boundaries():
    """RPRT-02/03 boundary table: a score exactly on a shared boundary
    belongs to the HIGHER band (2.0 -> orange, 3.5 -> green); the top band
    is inclusive of its own max (5.0 -> green)."""
    bands = _bands()

    assert get_maturity_band(1.0, bands)["id"] == "red"
    assert get_maturity_band(1.99, bands)["id"] == "red"
    assert get_maturity_band(2.0, bands)["id"] == "orange"
    assert get_maturity_band(3.49, bands)["id"] == "orange"
    assert get_maturity_band(3.5, bands)["id"] == "green"
    assert get_maturity_band(5.0, bands)["id"] == "green"


def test_maturity_band_same_for_both_callers():
    """RPRT-03: the band returned for a given score is identical whether
    obtained directly via get_maturity_band or via a build_priority_list
    row for that same score — proves the single source of truth."""
    bands = _bands()
    scores = _six_scores(values={"cat-1": 2.0, "cat-2": 3.5, "cat-3": 1.5})

    priority_list = build_priority_list(scores, bands)
    by_category = {row["category_id"]: row for row in priority_list}

    for category_id, score in (("cat-1", 2.0), ("cat-2", 3.5), ("cat-3", 1.5)):
        direct_band = get_maturity_band(score, bands)
        row = by_category[category_id]
        assert row["band_id"] == direct_band["id"]
        assert row["band_label"] == direct_band["label"]
        assert row["band_color"] == direct_band["color"]


def test_priority_list_six_rows_sorted():
    """RPRT-02/D-06: always exactly 6 rows (never filtered to only
    red/orange), sorted ascending by score."""
    config = _config()
    bands = _bands()
    category_ids = [cat["id"] for cat in config["categories"]]
    assert len(category_ids) == 6

    values = {cat_id: round(5.0 - i * 0.7, 2) for i, cat_id in enumerate(category_ids)}
    scores = _six_scores(values=values)

    priority_list = build_priority_list(scores, bands)

    assert len(priority_list) == 6
    result_scores = [row["score"] for row in priority_list]
    assert result_scores == sorted(result_scores)
    for row in priority_list:
        assert {"category_id", "name", "score", "band_id", "band_label", "band_color"} <= set(
            row.keys()
        )


def test_priority_list_tie_stable():
    """RPRT-02 ordering: two dimensions with equal scores retain config
    category order (stable sort)."""
    config = _config()
    bands = _bands()
    category_ids = [cat["id"] for cat in config["categories"]]

    # Every dimension tied at the same score -> output order must equal
    # config category order exactly (stable sort proof).
    scores = _six_scores(value=3.0)

    priority_list = build_priority_list(scores, bands)

    assert [row["category_id"] for row in priority_list] == category_ids


def test_radar_svg_structure():
    """RPRT-01: output has viewBox, one polygon, and all 6 category names,
    with explicit font presentation attributes on every <text> (Pitfall 3)."""
    config = _config()
    bands = _bands()
    scores = _six_scores(value=3.0)

    svg = generate_radar_svg(scores, bands)

    assert svg.startswith("<svg")
    assert "viewBox" in svg
    assert svg.count("<polygon") == 1
    for cat in config["categories"]:
        assert cat["name"] in svg
    assert svg.count("font-family") == len(config["categories"])
    assert svg.count("font-size") == len(config["categories"])
