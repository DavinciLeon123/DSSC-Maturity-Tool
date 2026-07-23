"""Pure-function unit tests for backend/app/services/report_generator.py.

These functions have no HTTP/DB dependency (no TestClient, no Postgres
session) — they are plain transforms over dict inputs, so tests call them
directly rather than going through the FastAPI app. Per D-04, assertions
pin the CURRENT output contract shape; this contract is deliberately
reshaped in Phase 16, so a future update there is expected, not a
regression against this suite.
"""

from app.services.report_generator import (
    _build_topic_structure,
    generate_html_report,
    generate_report_data,
)


def _mami_config() -> dict:
    """Small, hand-authored mami_config mirroring the real
    config/mami-framework.json "codes" shape (category/dimension/topic),
    per RESEARCH.md/PATTERNS.md guidance — no need to load the real file
    for a pure-transform unit test."""
    return {
        "version": "1.0",
        "codes": [
            {
                "id": "S-HRA-1.1",
                "category": "scheme",
                "category_label": "Scheme Management",
                "dimension": "human_readable",
                "dimension_label": "Human Readable/Actionable",
                "topic": "scheme_pub",
                "topic_label": "Scheme publication",
                "moscow_level": "MUST",
                "critical_override": None,
                "description": "desc HRA 1.1",
            },
            {
                "id": "S-MRA-1.1",
                "category": "scheme",
                "category_label": "Scheme Management",
                "dimension": "machine_readable",
                "dimension_label": "Machine Readable",
                "topic": "scheme_pub",
                "topic_label": "Scheme publication",
                "moscow_level": "MUST",
                "critical_override": None,
                "description": "desc MRA 1.1",
            },
            {
                "id": "P-HRA-2.1",
                "category": "participants",
                "category_label": "Participants Management",
                "dimension": "human_readable",
                "dimension_label": "Human Readable/Actionable",
                "topic": "onboarding",
                "topic_label": "Onboarding",
                "moscow_level": "SHOULD",
                "critical_override": None,
                "description": "desc participants onboarding",
            },
        ],
    }


def test_build_topic_structure_groups_codes_by_category_and_topic():
    structure = _build_topic_structure(_mami_config())

    assert set(structure.keys()) == {"scheme", "participants"}

    scheme_topics = structure["scheme"]
    assert len(scheme_topics) == 1
    assert scheme_topics[0]["topic_id"] == "scheme_pub"
    assert scheme_topics[0]["topic_label"] == "Scheme publication"
    assert scheme_topics[0]["codes"] == ["S-HRA-1.1", "S-MRA-1.1"]

    participants_topics = structure["participants"]
    assert len(participants_topics) == 1
    assert participants_topics[0]["codes"] == ["P-HRA-2.1"]


def test_generate_report_data_returns_expected_contract_shape():
    config = _mami_config()
    initiative = {"id": 42, "name": "Test Initiative"}
    answers = [
        {
            "mami_code": "S-HRA-1.1",
            "answer_value": "NOT_THERE_YET",
            "followup_selections": [],
            "followup_other": "",
        },
        {
            "mami_code": "S-MRA-1.1",
            "answer_value": "YES",
            "followup_selections": [],
            "followup_other": "",
        },
    ]
    findings = [{"mami_code": "S-HRA-1.1", "severity": "CRITICAL", "status": "FINDING"}]

    data = generate_report_data(
        initiative=initiative,
        answers=answers,
        findings=findings,
        mami_config=config,
    )

    # Top-level contract keys (frozen this milestone, reshaped in Phase 16).
    assert set(data.keys()) == {"initiative", "matrix", "topic_structure", "answers"}

    assert data["initiative"]["id"] == "42"
    assert data["initiative"]["name"] == "Test Initiative"
    assert "generated_at" in data["initiative"]

    # Per-category/dimension aggregation from _build_matrix.
    assert data["matrix"]["scheme"]["human_readable"]["S-HRA-1.1"] == "not_yet"
    assert data["matrix"]["scheme"]["machine_readable"]["S-MRA-1.1"] == "yes"

    # Per-answer counts/shape.
    assert len(data["answers"]) == 2
    hra_answer = next(a for a in data["answers"] if a["mami_code"] == "S-HRA-1.1")
    assert hra_answer["answer_label"] == "Not yet"
    assert hra_answer["description"] == "desc HRA 1.1"


def test_generate_html_report_renders_non_empty_html_with_initiative_name():
    config = _mami_config()
    initiative = {
        "name": "Acme Dataspace",
        "organization": "Acme Corp",
        "contact_name": "Jane Doe",
        "participant_type": "DSI",
    }
    answers = [
        {
            "mami_code": "S-HRA-1.1",
            "answer_value": "NOT_THERE_YET",
            "followup_selections": [],
            "followup_other": "",
        },
    ]
    findings = [{"mami_code": "S-HRA-1.1", "severity": "CRITICAL", "status": "FINDING"}]

    html = generate_html_report(
        initiative=initiative,
        answers=answers,
        findings=findings,
        mami_config=config,
    )

    # Proves Jinja2 rendering actually ran (non-empty, contains the
    # initiative name from the template context).
    assert isinstance(html, str)
    assert len(html) > 0
    assert "Acme Dataspace" in html
