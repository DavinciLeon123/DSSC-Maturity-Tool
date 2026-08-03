"""Jinja2-based HTML report generator for DSSC maturity reports.

Phase 14 (D-01a/D-05): all MAMI-matrix/heatmap/recommendation builders were
deleted outright — the ZEN/MoSCoW subsystem this module rendered is gone.

Phase 16 (RPRT-01..04, D-02/D-03): `generate_html_report` now renders the
rebuilt 6-dimension `report.html` template from the same
`dimension_scores`/`priority_list`/`radar_chart_svg`/`maturity_bands` keys
that `build_report_contract` returns for the JSON response — one shared
contract, two renderings (RPRT-04). The old `generate_report_data` helper
(initiative-info-only JSON assembly) is removed outright: it is fully
superseded by `build_report_contract`, which callers (reports.py) now call
directly.
"""

import math
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlmodel import Session, select

from app.models.questionnaire import QuestionnaireAnswer

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def generate_html_report(
    *,
    initiative: dict,
    generated_at: str,
    dimension_scores: list[dict],
    priority_list: list[dict],
    radar_chart_svg: str,
    maturity_bands: list[dict],
    answers_by_category: list[dict],
) -> str:
    """Render the 6-dimension compliance report HTML (RPRT-01/02/04) from the
    rebuilt `report.html` template.

    Args:
        initiative: dict with name, organization, contact_name.
        generated_at: pre-formatted generated-at string for the template.
        dimension_scores, priority_list, radar_chart_svg, maturity_bands:
            the same 4 keys `build_report_contract()` returns for the JSON
            response — passed through unmodified so the in-app view and the
            mailed PDF render from one shared payload (RPRT-04), never a
            second independently-built context.
        answers_by_category: list of dicts with category_id, name, and answers
            (the new submitted-answers section per RPRT-05).
    """
    env = _get_jinja_env()
    template = env.get_template("report.html")

    context = {
        "initiative": initiative,
        "generated_at": generated_at,
        "dimension_scores": dimension_scores,
        "priority_list": priority_list,
        "radar_chart_svg": radar_chart_svg,
        "maturity_bands": maturity_bands,
        "answers_by_category": answers_by_category,
    }
    return template.render(**context)


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


def build_answers_by_category(session: Session, assessment_id: int, config: dict) -> list[dict]:
    """RPRT-05: return per-question answers grouped by category in config order,
    with empty-state handling for unanswered categories and silent exclusion of
    stale question_ids (not present in current config).

    Args:
        session: SQLModel session for querying QuestionnaireAnswer rows.
        assessment_id: the assessment_id to filter answers by.
        config: the dssc_questionnaire_config dict (must contain "categories").

    Returns:
        A list with one dict per config category (in config order), shaped:
        {
            "category_id": str,
            "name": str,
            "answers": [
                {
                    "question_id": str,
                    "text": str,
                    "answer_label": str,
                    "score": int,
                    "band_color": str,
                },
                ...
            ]
        }
        Each category's "answers" list is ordered by config question order
        (not answered_at/insertion order), and is empty [] if no answers exist.
    """
    # Query all answers for this assessment
    answers = session.exec(
        select(QuestionnaireAnswer).where(QuestionnaireAnswer.assessment_id == assessment_id)
    ).all()

    # Build a {question_id: answer_row} lookup dict for fast retrieval
    answer_lookup = {a.question_id: a for a in answers}

    bands = config["maturity_bands"]
    result = []

    for category in config["categories"]:
        category_answers = []

        # Iterate this category's questions in config order
        for question in category["questions"]:
            question_id = question["id"]

            # Skip if this question_id is not in our answer lookup
            # (stale/orphaned answer handling)
            if question_id not in answer_lookup:
                continue

            answer_row = answer_lookup[question_id]

            # Look up the answer_label from the question's options
            answer_label = f"Score {answer_row.score}"  # fallback
            for option in question["options"]:
                if option["score"] == answer_row.score:
                    answer_label = option["label"]
                    break

            # Get the band color for this score
            band = get_maturity_band(answer_row.score, bands)

            category_answers.append(
                {
                    "question_id": question_id,
                    "text": question["text"],
                    "answer_label": answer_label,
                    "score": answer_row.score,
                    "band_color": band["color"],
                }
            )

        # Append category entry regardless of whether answers list is empty
        result.append(
            {
                "category_id": category["id"],
                "name": category["name"],
                "answers": category_answers,
            }
        )

    return result


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

    Phase 16 gap-closure (G-16-1, 16-05): `text-anchor` is no longer a
    uniform "middle" for every label — a centered anchor point close to the
    viewBox's left edge clips long left-side labels (e.g. "Control over
    Data & Trust"). Each label's anchor is now derived from the horizontal
    component (cos) of its own axis angle: top/bottom axes (cos ~ 0) stay
    "middle", right-side axes (cos > 0) become "start" so the label grows
    rightward away from the chart, and left-side axes (cos < 0) become
    "end" so the label grows leftward into the widened viewBox margin
    instead of overflowing it. The viewBox itself is widened horizontally
    (negative min-x, width > height) to give those outward-growing labels
    room, sized from the longest category name rather than a hardcoded
    axis-count assumption.
    """
    n = len(scores)
    cx = cy = size / 2
    radius = size * 0.38  # leave room for axis labels outside the chart

    def point(i: int, value_fraction: float) -> tuple[float, float]:
        angle = (2 * math.pi * i / n) - (math.pi / 2)
        r = radius * value_fraction
        return (cx + r * math.cos(angle), cy + r * math.sin(angle))

    def anchor_for(i: int) -> str:
        angle = (2 * math.pi * i / n) - (math.pi / 2)
        cos_angle = math.cos(angle)
        epsilon = 1e-6
        if abs(cos_angle) < epsilon:
            return "middle"
        return "start" if cos_angle > 0 else "end"

    # Data polygon
    data_points = " ".join(
        f"{x:.1f},{y:.1f}"
        for i, s in enumerate(scores)
        for x, y in [point(i, min(s["score"], max_score) / max_score)]
    )

    # Axis spokes (full-radius lines) + labels
    spokes = []
    labels = []
    label_font_size = 11
    longest_name_len = max((len(s["name"]) for s in scores), default=0)
    for i, s in enumerate(scores):
        x, y = point(i, 1.0)
        spokes.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="#d9d9d9" stroke-width="1"/>'
        )
        lx, ly = point(i, 1.18)  # push labels outside the polygon
        # WR-05: XML-escape the category name before interpolating into SVG
        # text content. Today this is only defense-in-depth (config category
        # names are server-controlled, never end-user free-text — see this
        # function's own docstring), but it's cheap insurance against the
        # invariant being broken by a future feature (e.g. an admin-editable
        # questionnaire builder), since this string is later marked `| safe`
        # in report.html and rendered via dangerouslySetInnerHTML on both
        # React pages.
        labels.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="{label_font_size}" '
            f'font-family="Jost, sans-serif" fill="#008ecf" '
            f'text-anchor="{anchor_for(i)}">{xml_escape(s["name"])}</text>'
        )

    overall_average = sum(s["score"] for s in scores) / n
    band = get_maturity_band(overall_average, bands)

    # Widen the viewBox horizontally so end/start-anchored labels growing
    # outward from the polygon aren't clipped at x=0 or x=size. The margin
    # is sized from the longest category name at the label font size
    # (rough average-character-width estimate), not from a fixed axis
    # count, so it scales with real config content.
    avg_char_width_factor = 0.6
    horizontal_margin = (longest_name_len * label_font_size * avg_char_width_factor) + 10
    view_min_x = -horizontal_margin
    view_width = size + 2 * horizontal_margin

    return (
        f'<svg viewBox="{view_min_x:.1f} 0 {view_width:.1f} {size}" '
        f'xmlns="http://www.w3.org/2000/svg">'
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

    # ORM-or-dict flexibility idiom
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
