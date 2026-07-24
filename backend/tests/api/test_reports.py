"""Integration tests for the four report endpoints (/report, /report/data
GET+POST, /report/pdf, /report/mail) — backend/app/api/v1/reports.py +
backend/app/services/report_generator.py.

Phase 14 (D-01a/D-05/D-05a, SCOR-04): the old ZEN/MoSCoW degraded-scoring
path (`_degraded_scoring_inputs`/`_inject_degraded_banner`) is deleted
outright. All four endpoints now enforce the shared
`assert_assessment_complete` completion gate (422 "Questionnaire not fully
answered") ownership-first (T-14-01), and `/report/data` returns a new
`dimension_scores` field computed by the dimension-scoring service instead
of the old matrix/topic_structure/answers shape.

WeasyPrint is imported lazily *inside* `_send_report_email` and
`download_report_pdf` (deferred import) — tests patch `weasyprint.HTML`
directly (the module-level target the lazy import resolves against), never
`app.api.v1.reports.WeasyHTML` (that alias doesn't exist until the function
body runs — patching it would silently no-op, per RESEARCH.md Pitfall 2).
"""

from sqlmodel import select

from app.models.report import ComplianceReport
from app.services.mami_config import load_dssc_questionnaire_config
from tests.factories import make_answer, make_assessment, make_initiative, make_user

VALID_PASSWORD = "Str0ngPassw0rd!123"


def _login(client, email, password):
    """Authenticate the shared `client` fixture as a specific user.

    Report endpoints check `initiative.user_id == current_user.id`, so tests
    need a client bound to the SAME user that owns the initiative — the
    plain `client` fixture from conftest.py is otherwise anonymous.
    """
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _answer_all_questions(session, initiative, assessment, config, *, skip=None):
    """Answer every question in `config` for `assessment`, optionally
    skipping one question id (for the incomplete-assessment tests)."""
    for cat in config["categories"]:
        for question in cat["questions"]:
            if skip is not None and question["id"] == skip:
                continue
            make_answer(
                session,
                initiative=initiative,
                assessment=assessment,
                question_id=question["id"],
                category_id=cat["id"],
                score=3,
            )


def _fully_answered_initiative(session):
    """Build a user + owned initiative + a fully-answered draft Assessment
    (every question in the real config answered) — the shape all four
    report endpoints now require to return 200 (SCOR-04)."""
    config = load_dssc_questionnaire_config()
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative)
    _answer_all_questions(session, initiative, assessment, config)
    return user, initiative, config


# ---------------------------------------------------------------------------
# Task 1: mail_report / download_report_pdf / generate_report
# ---------------------------------------------------------------------------


def test_mail_report_generates_pdf_and_sends_email(client, session, monkeypatch, mocker):
    from app.api.v1 import reports as reports_module

    # RESEND_API_KEY must be non-empty, else _send_report_email takes the
    # dev-mode skip path and never calls the mocked resend.Emails.send
    # (RESEARCH.md Open Question 2).
    monkeypatch.setattr(reports_module.settings, "RESEND_API_KEY", "test-resend-api-key")
    mock_html_cls = mocker.patch("weasyprint.HTML")
    mock_html_cls.return_value.write_pdf.return_value = b"%PDF-FAKE-BYTES"
    mock_send = mocker.patch("resend.Emails.send")

    user, initiative, _config = _fully_answered_initiative(session)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report/mail")
    assert response.status_code == 202

    # TestClient runs BackgroundTasks synchronously before the response
    # context exits — these assertions catch a silently-broken background
    # task that the bare 202 would miss (Pitfall 3 / T-12-04-SILENT).
    mock_html_cls.return_value.write_pdf.assert_called_once()
    mock_send.assert_called_once()

    sent_params = mock_send.call_args[0][0]
    assert sent_params["attachments"][0]["filename"] == "MAMI-Interoperability-Report.pdf"


def test_mail_report_dev_mode_skips_resend_send(client, session, monkeypatch, mocker):
    from app.api.v1 import reports as reports_module

    # Empty RESEND_API_KEY is the current, intentional dev-mode behavior
    # (D-04 characterization, not a bug) — the endpoint still returns 202
    # but must NOT call resend.Emails.send.
    monkeypatch.setattr(reports_module.settings, "RESEND_API_KEY", "")
    mock_html_cls = mocker.patch("weasyprint.HTML")
    mock_html_cls.return_value.write_pdf.return_value = b"%PDF-FAKE-BYTES"
    mock_send = mocker.patch("resend.Emails.send")

    user, initiative, _config = _fully_answered_initiative(session)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report/mail")
    assert response.status_code == 202
    mock_send.assert_not_called()


def test_mail_report_incomplete_assessment_returns_422(client, session):
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report/mail")
    assert response.status_code == 422
    assert response.json()["detail"] == "Questionnaire not fully answered"


def test_download_report_pdf_returns_pdf_content_type(client, session, mocker):
    mock_html_cls = mocker.patch("weasyprint.HTML")
    mock_html_cls.return_value.write_pdf.return_value = b"%PDF-FAKE-BYTES"

    user, initiative, _config = _fully_answered_initiative(session)
    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    mock_html_cls.return_value.write_pdf.assert_called_once()


def test_download_report_pdf_incomplete_assessment_returns_422(client, session):
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report/pdf")
    assert response.status_code == 422
    assert response.json()["detail"] == "Questionnaire not fully answered"


def test_generate_report_returns_html_and_upserts_compliance_report(client, session):
    # Exercises the simplified render path (no ZEN/MoSCoW findings, D-05a)
    # plus the pg_insert().on_conflict_do_update() upsert path — this only
    # works if the full SQLModel.metadata schema (with the unique constraint
    # on ComplianceReport.initiative_id) was built (Pitfall 5).
    user, initiative, config = _fully_answered_initiative(session)
    total_questions = sum(len(cat["questions"]) for cat in config["categories"])
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert len(response.text) > 0

    report = session.exec(
        select(ComplianceReport).where(ComplianceReport.initiative_id == initiative.id)
    ).first()
    assert report is not None
    assert report.total_answers == total_questions

    # Regenerating hits the ON CONFLICT branch — must replace the existing
    # row, not create a duplicate (unique constraint on initiative_id).
    second = client.post(f"/api/v1/initiatives/{initiative.id}/report")
    assert second.status_code == 200
    reports = session.exec(
        select(ComplianceReport).where(ComplianceReport.initiative_id == initiative.id)
    ).all()
    assert len(reports) == 1


def test_generate_report_incomplete_assessment_returns_422(client, session):
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report")
    assert response.status_code == 422
    assert response.json()["detail"] == "Questionnaire not fully answered"


# ---------------------------------------------------------------------------
# Task 2/3: /report/data (GET+POST) — dimension_scores field, SCOR-04 gate
# ---------------------------------------------------------------------------


def test_post_report_data_returns_dimension_scores(client, session):
    user, initiative, _config = _fully_answered_initiative(session)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report/data")
    assert response.status_code == 200
    body = response.json()

    assert "dimension_scores" in body
    assert len(body["dimension_scores"]) == 6
    assert all(1.0 <= d["score"] <= 5.0 for d in body["dimension_scores"])
    assert all({"category_id", "name", "score"} == set(d.keys()) for d in body["dimension_scores"])
    assert "initiative" in body

    # Old MAMI-matrix contract keys must be gone entirely (D-01a/D-05) — not
    # present-but-empty.
    assert "matrix" not in body
    assert "topic_structure" not in body
    assert "answers" not in body


def test_post_report_data_incomplete_assessment_returns_422(client, session):
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report/data")
    assert response.status_code == 422
    assert response.json()["detail"] == "Questionnaire not fully answered"


def test_get_report_data_returns_dimension_scores(client, session):
    user, initiative, _config = _fully_answered_initiative(session)
    _login(client, user.email, VALID_PASSWORD)

    # A report must already exist for the GET endpoint (404 otherwise).
    post_response = client.post(f"/api/v1/initiatives/{initiative.id}/report")
    assert post_response.status_code == 200

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report/data")
    assert response.status_code == 200
    body = response.json()

    assert "dimension_scores" in body
    assert len(body["dimension_scores"]) == 6
    assert "matrix" not in body
    assert "topic_structure" not in body
    assert "answers" not in body


def test_get_report_data_incomplete_assessment_returns_422(client, session):
    """SCOR-04: the completion gate fires before the report-existence 404,
    so an incomplete assessment gets 422 even with no report ever
    generated."""
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report/data")
    assert response.status_code == 422
    assert response.json()["detail"] == "Questionnaire not fully answered"


def test_get_report_data_no_report_yet_returns_404_when_complete(client, session):
    """A fully-answered assessment with no report ever generated still 404s
    on GET /report/data (report-existence check runs after the completion
    gate, per the ordering guidance)."""
    user, initiative, _config = _fully_answered_initiative(session)
    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report/data")
    assert response.status_code == 404
    assert response.json()["detail"] == "No report generated yet"


# ---------------------------------------------------------------------------
# Ownership-before-completion-gate ordering (T-14-01)
# ---------------------------------------------------------------------------


def test_report_data_ownership_before_completion_gate(client, session):
    """A different user requesting someone else's (incomplete) initiative
    gets 404 for ownership — NOT 422 — proving the ownership check fires
    first (T-14-01)."""
    owner = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=owner)
    # Deliberately leave the initiative's assessment incomplete/nonexistent
    # — if ownership did not fire first, this would otherwise 422.

    other_user = make_user(session, password=VALID_PASSWORD)
    _login(client, other_user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report/data")
    assert response.status_code == 404
    assert response.json()["detail"] == "Initiative not found"
