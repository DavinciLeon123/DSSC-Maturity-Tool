"""Characterization tests for report generation/PDF/email delivery
(backend/app/api/v1/reports.py + backend/app/services/report_generator.py).

Per D-04, the real (current) ZEN/MoSCoW scoring path (`score_all_answers`)
runs UNMOCKED end-to-end in every test below — only the external boundaries
(WeasyPrint's PDF byte-rendering, Resend's HTTP send) are mocked. Any bug
discovered while writing these tests is logged in the SUMMARY as a backlog
item, not fixed inline (D-04).

WeasyPrint is imported lazily *inside* `_send_report_email` and
`download_report_pdf` (deferred import) — tests patch `weasyprint.HTML`
directly (the module-level target the lazy import resolves against), never
`app.api.v1.reports.WeasyHTML` (that alias doesn't exist until the function
body runs — patching it would silently no-op, per RESEARCH.md Pitfall 2).
"""

from sqlmodel import select

from app.models.questionnaire import AnswerValue
from app.models.report import ComplianceReport
from tests.factories import make_answer, make_initiative, make_user

VALID_PASSWORD = "Str0ngPassw0rd!123"

# Real MAMI codes from config/mami-framework.json — used so the report's
# category/dimension/topic aggregation (which iterates mami_config["codes"])
# actually matches at least some of the fixture answers.
REAL_CODES = ["S-HRA-1.1", "S-MRA-1.1", "S-TA-1.1", "S-HRA-2.1", "S-MRA-2.1"]


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


def _initiative_with_answers(session, *, n=5):
    """Build a user + owned initiative + a set of QuestionnaireAnswer rows
    (real MAMI codes, mixed YES/NOT_THERE_YET) so scoring has real input to
    run against the real ZEN engine (D-04 — never mocked in this file)."""
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    for i in range(n):
        make_answer(
            session,
            initiative=initiative,
            mami_code=REAL_CODES[i % len(REAL_CODES)],
            question_id=f"q_{i}",
            answer_value=AnswerValue.not_there_yet if i % 2 == 0 else AnswerValue.yes,
        )
    return user, initiative


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

    user, initiative = _initiative_with_answers(session)
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

    user, initiative = _initiative_with_answers(session)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report/mail")
    assert response.status_code == 202
    mock_send.assert_not_called()


def test_mail_report_no_answers_returns_422(client, session):
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report/mail")
    assert response.status_code == 422


def test_download_report_pdf_returns_pdf_content_type(client, session, mocker):
    mock_html_cls = mocker.patch("weasyprint.HTML")
    mock_html_cls.return_value.write_pdf.return_value = b"%PDF-FAKE-BYTES"

    user, initiative = _initiative_with_answers(session)
    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    mock_html_cls.return_value.write_pdf.assert_called_once()


def test_download_report_pdf_no_answers_returns_422(client, session):
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report/pdf")
    assert response.status_code == 422


def test_generate_report_returns_html_and_upserts_compliance_report(client, session):
    # Exercises the real ZEN/MoSCoW scoring path end-to-end (unmocked, D-04)
    # plus the pg_insert().on_conflict_do_update() upsert path — this only
    # works if the full SQLModel.metadata schema (with the unique constraint
    # on ComplianceReport.initiative_id) was built (Pitfall 5).
    user, initiative = _initiative_with_answers(session)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert len(response.text) > 0

    report = session.exec(
        select(ComplianceReport).where(ComplianceReport.initiative_id == initiative.id)
    ).first()
    assert report is not None
    assert report.total_answers == 5

    # Regenerating hits the ON CONFLICT branch — must replace the existing
    # row, not create a duplicate (unique constraint on initiative_id).
    second = client.post(f"/api/v1/initiatives/{initiative.id}/report")
    assert second.status_code == 200
    reports = session.exec(
        select(ComplianceReport).where(ComplianceReport.initiative_id == initiative.id)
    ).all()
    assert len(reports) == 1
