"""Jinja2-based HTML report generator for MAMI compliance reports.

Phase 14 (D-01a/D-05): all MAMI-matrix/heatmap/recommendation builders are
deleted outright — the ZEN/MoSCoW subsystem this module rendered is gone.
`generate_html_report` still renders the unchanged `report.html` template
(Phase 16's job to redesign), passing literal-empty `heatmap_rows`/
`not_yet_recommendations` so Jinja2 doesn't raise `UndefinedError` on the
template's existing `.get(...)`/`{% for %}` references. `generate_report_data`
returns initiative info only — callers (reports.py) add `dimension_scores`
on top from the new dimension-scoring service.
"""

import math
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def generate_html_report(initiative: dict, generated_at: str) -> str:
    """Render the compliance report HTML from the unchanged Jinja2 template.

    Args:
        initiative: dict with name, organization, contact_name
        generated_at: pre-formatted generated-at string for the template

    Returns:
        Rendered HTML string. `heatmap_rows`/`not_yet_recommendations` are
        passed as literal empties (D-05, RESEARCH Pitfall 1) — no builder
        function computes them anymore.
    """
    env = _get_jinja_env()
    template = env.get_template("report.html")

    context = {
        "initiative": initiative,
        "generated_at": generated_at,
        "heatmap_rows": {},
        "not_yet_recommendations": [],
    }
    return template.render(**context)


def generate_report_data(initiative) -> dict:
    """Return structured JSON-serialisable report data for the React /report page.

    Args:
        initiative: Initiative ORM object (or dict) with id, name attributes

    Returns:
        Dict with only an `initiative` key (D-01a/D-05) — the caller adds
        `dimension_scores` on top via the new dimension-scoring service.
    """
    # Resolve initiative id and name (supports ORM object or dict)
    if hasattr(initiative, "id"):
        initiative_id = str(initiative.id)
        initiative_name = initiative.name
    else:
        initiative_id = str(initiative.get("id", ""))
        initiative_name = initiative.get("name", "")

    return {
        "initiative": {
            "id": initiative_id,
            "name": initiative_name,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
    }


def get_maturity_band(score: float, bands: list[dict]) -> dict:
    """Phase 16 (RPRT-03): the SOLE band-classification function in this
    codebase. Both `build_priority_list` and `generate_radar_svg` call this —
    no second inequality chain may exist anywhere else, on any surface.

    Bands are checked in ascending `min` order (config order — see
    `maturity_bands` in `config/dssc-questionnaire.json`, D-05); a score
    exactly on a shared boundary (e.g. 2.0, which is both the red band's
    max and the orange band's min) belongs to the HIGHER band — i.e.
    `min <= score < max` is the rule, except the top (last) band is also
    inclusive of its own `max` (so 5.0 still resolves to green, not
    uncovered).
    """
    for band in bands:
        is_last = band is bands[-1]
        if band["min"] <= score < band["max"] or (is_last and score == band["max"]):
            return band
    raise ValueError(f"score {score} not covered by any maturity_bands entry")


def build_priority_list(scores: list[dict], bands: list[dict]) -> list[dict]:
    """RPRT-02/D-06: always returns all 6 dimensions (never filtered to only
    red/orange), sorted ascending by score. `sorted()` is a stable sort, so
    dimensions with equal scores retain config category order (RPRT-02
    ordering). Each row's band fields are sourced only from
    `get_maturity_band` — never re-derived.

    Args:
        scores: [{category_id, name, score}, ...] — already 2dp-rounded by
            `compute_dimension_scores`'s existing precedent.
        bands: config["maturity_bands"].
    """
    return [
        {
            "category_id": s["category_id"],
            "name": s["name"],
            "score": s["score"],
            "band_id": (band := get_maturity_band(s["score"], bands))["id"],
            "band_label": band["label"],
            "band_color": band["color"],
        }
        for s in sorted(scores, key=lambda s: s["score"])
    ]


def generate_radar_svg(
    scores: list[dict],
    bands: list[dict],
    *,
    size: int = 320,
    max_score: float = 5.0,
) -> str:
    """RPRT-01/D-01/D-02: one server-side SVG string, reused verbatim for
    both the in-app report and the admin org-average chart — the browser
    and WeasyPrint only ever render this markup, never recompute geometry.

    `viewBox` (not fixed pixel width/height) is used so the SVG scales in
    both the responsive in-app card and the fixed-width PDF page (D-02
    overflow). Axis 0 points straight up (angle offset by -pi/2), and axes
    are placed in config category order (deterministic, RPRT-01 ordering).

    Per RESEARCH Pitfall 3 (WeasyPrint SVG `<text>` parity), every `<text>`
    element carries explicit `font-size`/`font-family`/`fill` presentation
    attributes rather than relying on external CSS.

    Only server-controlled config category names and computed numeric
    scores flow into this string — never end-user free-text (e.g.
    initiative.name) is ever interpolated here (threat T-16-02).
    """
    n = len(scores)
    cx = cy = size / 2
    radius = size * 0.38  # leave room for axis labels outside the chart

    def point(i: int, value_fraction: float) -> tuple[float, float]:
        angle = (2 * math.pi * i / n) - (math.pi / 2)
        r = radius * value_fraction
        return (cx + r * math.cos(angle), cy + r * math.sin(angle))

    # Data polygon
    data_points = " ".join(
        f"{x:.1f},{y:.1f}"
        for i, s in enumerate(scores)
        for x, y in [point(i, min(s["score"], max_score) / max_score)]
    )

    # Axis spokes (full-radius lines) + labels
    spokes = []
    labels = []
    for i, s in enumerate(scores):
        x, y = point(i, 1.0)
        spokes.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="#d9d9d9" stroke-width="1"/>'
        )
        lx, ly = point(i, 1.18)  # push labels outside the polygon
        labels.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11" '
            f'font-family="Rubik, sans-serif" fill="#06004f" '
            f'text-anchor="middle">{s["name"]}</text>'
        )

    overall_average = sum(s["score"] for s in scores) / n
    band = get_maturity_band(overall_average, bands)

    return (
        f'<svg viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">'
        + "".join(spokes)
        + f'<polygon points="{data_points}" fill="{band["color"]}" '
        f'fill-opacity="0.25" stroke="{band["color"]}" stroke-width="2"/>'
        + "".join(labels)
        + "</svg>"
    )


def build_report_contract(
    dimension_scores: list[dict],
    initiative,
    assessment,
    config: dict,
) -> dict:
    """RPRT-04: the single shared contract dict every downstream surface
    (in-app React report, WeasyPrint PDF, admin aggregate) consumes without
    recomputation — one computation, reused verbatim.

    Args:
        dimension_scores: the frozen `Assessment.dimension_scores` snapshot
            (D-03) — never a live recompute of `compute_dimension_scores`
            for a submitted assessment.
        initiative: Initiative ORM object (or dict) with id, name.
        assessment: Assessment ORM object (or dict) with id, version.
        config: dssc_questionnaire_config dict (must contain
            "maturity_bands").
    """
    bands = config["maturity_bands"]

    # ORM-or-dict flexibility idiom (mirrors generate_report_data above)
    if hasattr(initiative, "id"):
        initiative_id = str(initiative.id)
        initiative_name = initiative.name
    else:
        initiative_id = str(initiative.get("id", ""))
        initiative_name = initiative.get("name", "")

    if hasattr(assessment, "id"):
        assessment_id = assessment.id
        version = assessment.version
    else:
        assessment_id = assessment.get("id")
        version = assessment.get("version")

    return {
        "assessment_id": assessment_id,
        "version": version,
        "initiative": {"id": initiative_id, "name": initiative_name},
        "dimension_scores": dimension_scores,
        "priority_list": build_priority_list(dimension_scores, bands),
        "radar_chart_svg": generate_radar_svg(dimension_scores, bands),
        "maturity_bands": bands,
    }
