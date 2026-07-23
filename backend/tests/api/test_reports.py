"""Characterization tests for report generation/PDF/email delivery
(backend/app/api/v1/reports.py + backend/app/services/report_generator.py).

Phase 13 (D-02/D-06) reshaped the answer table to assessment_id/category_id/
score, removing mami_code/answer_value entirely. The legacy MAMI-code-keyed
ZEN/MoSCoW scoring path (`score_all_answers`) has no valid input shape for
new-schema answers, so reports.py deliberately degrades to zero
findings/recommendations for them rather than raising (RESEARCH Pitfall 3 /
Assumption A3 — documented inline in reports.py). Per D-04, this newly
pinned degraded behavior is what's characterized below (total_answers still
reflects the real row count; findings/critical/non-critical counts are all
zero) — a full per-assessment scoring rebuild against the new DSSC config is
explicitly Phase 14/16's job, not this plan's.

WeasyPrint is imported lazily *inside* `_send_report_email` and
`download_report_pdf` (deferred import) — tests patch `weasyprint.HTML`
directly (the module-level target the lazy import resolves against), never
`app.api.v1.reports.WeasyHTML` (that alias doesn't exist until the function
body runs — patching it would silently no-op, per RESEARCH.md Pitfall 2).
"""

from sqlmodel import select

from app.models.report import ComplianceReport
from tests.factories import make_answer, make_initiative, make_user

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


def _initiative_with_answers(session, *, n=5):
    """Build a user + owned initiative + `n` new-schema QuestionnaireAnswer
    rows (assessment_id/category_id/score, D-02/D-06) — enough to exercise
    the "has answers" 422-guard and the total_answers counting path.
    Scoring itself degrades to zero findings for these (see module
    docstring) — this fixture is not meant to produce real findings."""
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    for i in range(n):
        make_answer(
            session,
            initiative=initiative,
            question_id=f"q_{i}",
            category_id=f"cat-{(i % 6) + 1}",
            score=(i % 5) + 1,
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
