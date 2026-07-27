"""Admin cross-initiative aggregation service (ADMN-01).

Rebuilds the org-wide admin view for the new 6-category dimension-score
model: one org-wide averaged radar chart plus a per-initiative breakdown,
each initiative contributing only its latest SUBMITTED assessment (D-08).
Initiatives with zero submitted assessments are excluded from the org
average but still appear in the per-initiative list with `has_data=False`.

Reuses `generate_radar_svg` verbatim (D-01) — no second radar
implementation exists anywhere in this module.
"""

from sqlalchemy import text
from sqlmodel import Session

from app.services.report_generator import generate_radar_svg

# Adapts admin.py's list_initiatives session.execute(text(...)) + .mappings()
# raw-SQL idiom (enum-safe join pattern already used elsewhere in this repo),
# per RESEARCH Pattern 3: LEFT JOIN LATERAL a subquery selecting the
# highest-version SUBMITTED assessment per initiative, so every initiative
# appears exactly once — including those with zero submitted assessments
# (dimension_scores/assessment_id come back NULL for those, D-08).
_LATEST_SUBMITTED_PER_INITIATIVE_SQL = """
    SELECT
        i.id            AS initiative_id,
        i.name          AS initiative_name,
        latest.id       AS assessment_id,
        latest.dimension_scores AS dimension_scores
    FROM initiative i
    LEFT JOIN LATERAL (
        SELECT a.id, a.dimension_scores
        FROM assessment a
        WHERE a.initiative_id = i.id AND a.status = 'submitted'
        ORDER BY a.version DESC
        LIMIT 1
    ) latest ON true
    ORDER BY i.created_at DESC
"""


def build_admin_aggregate(session: Session, config: dict) -> dict:
    """Returns {org_average_scores, org_radar_chart_svg, initiatives}.

    - `initiatives`: one row per initiative — `has_data=False` (null
      `dimension_scores`/`overall_average`/`report_assessment_id`) for
      initiatives with zero submitted assessments (draft-only or brand new).
    - Org average is computed ONLY over rows with `has_data=True` (RESEARCH
      Pitfall 5) — a no-data initiative's scores are never coerced to zero
      before averaging (the plan's prohibition). If the included set is
      empty, `org_radar_chart_svg` is None and `org_average_scores` is []
      (never a zeroed degenerate hexagon).
    - Rows are sorted by (has_data, overall_average, name) so equal
      averages sort stably (ADMN-01 ordering) — Python's `sorted()` stable
      sort preserves the SQL's `ORDER BY i.created_at DESC` relative order
      for genuine ties.
    """
    bands = config["maturity_bands"]
    categories = config["categories"]

    result = session.execute(text(_LATEST_SUBMITTED_PER_INITIATIVE_SQL))

    initiative_rows = []
    for row in result.mappings():
        dimension_scores = row["dimension_scores"]
        has_data = dimension_scores is not None
        overall_average = (
            round(sum(s["score"] for s in dimension_scores) / len(dimension_scores), 2)
            if has_data
            else None
        )
        initiative_rows.append(
            {
                "id": row["initiative_id"],
                "name": row["initiative_name"],
                "report_assessment_id": row["assessment_id"],
                "dimension_scores": dimension_scores,
                "overall_average": overall_average,
                "has_data": has_data,
            }
        )

    initiative_rows.sort(
        key=lambda r: (
            not r["has_data"],
            r["overall_average"] if r["overall_average"] is not None else 0.0,
            r["name"],
        )
    )

    included = [r for r in initiative_rows if r["has_data"]]

    if not included:
        org_average_scores: list[dict] = []
        org_radar_chart_svg = None
    else:
        org_average_scores = [
            {
                "category_id": cat["id"],
                "name": cat["name"],
                "score": round(
                    sum(
                        next(
                            s["score"]
                            for s in r["dimension_scores"]
                            if s["category_id"] == cat["id"]
                        )
                        for r in included
                    )
                    / len(included),
                    2,
                ),
            }
            for cat in categories
        ]
        org_radar_chart_svg = generate_radar_svg(org_average_scores, bands)

    return {
        "org_average_scores": org_average_scores,
        "org_radar_chart_svg": org_radar_chart_svg,
        "initiatives": initiative_rows,
    }
