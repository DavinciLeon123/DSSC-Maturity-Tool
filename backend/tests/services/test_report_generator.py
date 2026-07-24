"""Pure-function unit tests for backend/app/services/report_generator.py.

Phase 14 (D-01a/D-05): all MAMI-matrix/heatmap/recommendation builders are
deleted from report_generator.py along with the ZEN/MoSCoW subsystem they
served. `generate_report_data`/`generate_html_report` are now trimmed to
initiative-info-only (plus the literal-empty Jinja2 context for the
unchanged report.html template) — these tests assert that simplified
contract, not the old matrix/topic_structure/answers shape.
"""

from app.services.report_generator import generate_html_report, generate_report_data


def test_generate_report_data_returns_initiative_only_shape():
    initiative = {"id": 42, "name": "Test Initiative"}

    data = generate_report_data(initiative=initiative)

    # Top-level contract is initiative-only now (D-01a) — no matrix/
    # topic_structure/answers keys survive.
    assert set(data.keys()) == {"initiative"}
    assert data["initiative"]["id"] == "42"
    assert data["initiative"]["name"] == "Test Initiative"
    assert "generated_at" in data["initiative"]
    assert "matrix" not in data
    assert "topic_structure" not in data
    assert "answers" not in data


def test_generate_report_data_accepts_orm_style_object():
    class FakeInitiative:
        id = 7
        name = "ORM-shaped Initiative"

    data = generate_report_data(initiative=FakeInitiative())

    assert data["initiative"]["id"] == "7"
    assert data["initiative"]["name"] == "ORM-shaped Initiative"


def test_generate_html_report_renders_non_empty_html_with_initiative_name():
    initiative = {
        "name": "Acme Dataspace",
        "organization": "Acme Corp",
        "contact_name": "Jane Doe",
        "participant_type": "DSI",
    }

    html = generate_html_report(initiative=initiative, generated_at="24 July 2026, 12:00 UTC")

    # Proves Jinja2 rendering actually ran (non-empty, contains the
    # initiative name from the template context) without raising
    # UndefinedError even though heatmap_rows/not_yet_recommendations are
    # passed as literal empties (RESEARCH Pitfall 1).
    assert isinstance(html, str)
    assert len(html) > 0
    assert "Acme Dataspace" in html
    assert "24 July 2026, 12:00 UTC" in html
