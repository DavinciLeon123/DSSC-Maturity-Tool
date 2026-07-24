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
