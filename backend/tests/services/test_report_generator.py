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

import re
from xml.sax.saxutils import escape as xml_escape

from markupsafe import escape as html_escape

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


def test_priority_score_column_css_has_fixed_width_and_right_align():
    """G-16-2: the .priority-score CSS rule carries both a fixed min-width
    and right text-alignment — the flush-right column that makes scores
    align independent of the preceding dimension-name's width, regardless
    of WeasyPrint's justify-content free-space distribution."""
    initiative = {"name": "Acme Dataspace", "organization": "Acme Corp"}
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

    rule_match = re.search(r"\.priority-score\s*\{([^}]*)\}", html)
    assert rule_match is not None, "expected a .priority-score CSS rule in the rendered HTML"
    rule_body = rule_match.group(1)
    assert re.search(r"min-width\s*:\s*\d+px", rule_body)
    assert re.search(r"text-align\s*:\s*right", rule_body)


def test_priority_row_flattened_no_inner_name_wrapper():
    """G-16-2: the priority-row's band dot, name, score, and band label are
    flat siblings — the old inner wrapper span that nested the band-dot
    inside .priority-name is gone (the flatten that fixes WeasyPrint's
    nested-flex justify-content/intrinsic-width bugs), while each
    dimension's name and 2-decimal score still render."""
    initiative = {"name": "Acme Dataspace", "organization": "Acme Corp"}
    bands = _bands()
    scores = _six_scores(
        values={cat["id"]: round(1.0 + i * 0.6, 2) for i, cat in enumerate(_config()["categories"])}
    )
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

    name_span_matches = re.findall(r'<span class="priority-name">(.*?)</span>', html, re.DOTALL)
    assert len(name_span_matches) == len(priority_list)
    for inner in name_span_matches:
        # The old wrapper nested a <span class="band-dot"> here — flattened
        # now, so .priority-name's own content must contain no nested span.
        assert "<span" not in inner

    for row in priority_list:
        assert str(html_escape(row["name"])) in html
        assert f"{row['score']:.2f}" in html


def test_legend_renders_one_entry_per_band_with_labels():
    """G-16-2: the legend still renders exactly one entry per maturity
    band, with each band's label text present, after flattening
    .legend-item out of the nested-flex structure."""
    initiative = {"name": "Acme Dataspace", "organization": "Acme Corp"}
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

    assert html.count('class="legend-item"') == len(bands)
    for band in bands:
        assert band["label"] in html


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
        # WR-05: category names are XML-escaped before interpolation (real
        # config content includes "Control over Data & Trust", proving this
        # isn't just a hypothetical) — assert against the escaped form.
        assert xml_escape(cat["name"]) in svg
    assert svg.count("font-family") == len(config["categories"])
    assert svg.count("font-size") == len(config["categories"])


def test_radar_svg_escapes_special_characters_in_category_name():
    # WR-05 regression: category names must be XML-escaped before being
    # interpolated into SVG <text> content — defense in depth even though
    # today's config category names are server-controlled, never end-user
    # free-text (this function's own docstring).
    bands = _bands()
    scores = [
        {"category_id": "c1", "name": 'A & B <script>"quote"</script>', "score": 3.0},
    ]

    svg = generate_radar_svg(scores, bands)

    assert "<script>" not in svg
    assert "A &amp; B &lt;script&gt;" in svg


def test_radar_svg_labels_use_position_aware_text_anchor():
    """G-16-1: for the real 6-category config (axes evenly spaced starting
    straight up), exactly 2 labels are text-anchor="middle" (top/bottom,
    cos ~ 0), exactly 2 are "start" (right side, cos > 0), and exactly 2
    are "end" (left side, cos < 0) — no more uniform "middle" anchor that
    clips long left-side labels at the viewBox's left edge."""
    config = _config()
    bands = _bands()
    scores = _six_scores(value=3.0)
    assert len(config["categories"]) == 6

    svg = generate_radar_svg(scores, bands)

    assert svg.count('text-anchor="middle"') == 2
    assert svg.count('text-anchor="start"') == 2
    assert svg.count('text-anchor="end"') == 2


def test_radar_svg_viewbox_widened_horizontally():
    """G-16-1: the viewBox is widened horizontally (negative min-x, width
    greater than height) so outward-growing start/end-anchored labels have
    room — including the longest real category name, "Control over Data &
    Trust" — without being clipped at either horizontal edge."""
    bands = _bands()
    scores = _six_scores(value=3.0)

    svg = generate_radar_svg(scores, bands)

    view_box_str = svg.split('viewBox="')[1].split('"')[0]
    min_x, min_y, width, height = (float(v) for v in view_box_str.split())

    assert min_x < 0
    assert width > height
