"""Integration tests for the report endpoints (/report GET+POST, /report/data
GET+POST, /report/pdf, /report/mail) — backend/app/api/v1/reports.py +
backend/app/services/report_generator.py + dimension_scoring.py's
resolve_report_assessment.

Phase 16 (D-03/D-04, RESEARCH Pitfall 1): every fixture here builds a
SUBMITTED assessment with a frozen `dimension_scores` snapshot (mirroring
what `POST /initiatives/{id}/submit` does at submission time) — the old
draft-only fixtures masked the exact bug this phase fixes: every report
endpoint 422ing unconditionally once an assessment was actually submitted.
All 6 report route functions now resolve their assessment via
`resolve_report_assessment` and accept an optional `assessment_id` query
param (D-04, per-version viewing); `ComplianceReport` persistence is gone
(RESEARCH Pitfall 2) so every read recomputes the shared report contract
fresh.

WeasyPrint is imported lazily *inside* `_send_report_email` and
`download_report_pdf` (deferred import) — tests patch `weasyprint.HTML`
directly (the module-level target the lazy import resolves against), never
`app.api.v1.reports.WeasyHTML` (that alias doesn't exist until the function
body runs — patching it would silently no-op, per RESEARCH.md Pitfall 4).
"""

from app.models.assessment import AssessmentStatus
from app.services.dimension_scoring import compute_dimension_scores
from app.services.mami_config import load_dssc_questionnaire_config
from tests.factories import make_answer, make_assessment, make_initiative, make_user

VALID_PASSWORD = "Str0ngPassw0rd!123"


def _login(client, email, password):
    """Authenticate the shared `client` fixture as a specific user.

    Report endpoints check ownership (or admin bypass), so tests need a
    client bound to the SAME user that owns the initiative — the plain
    `client` fixture from conftest.py is otherwise anonymous.
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
    skipping one question id."""
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


def _submit(session, initiative, assessment, config):
    """Flip `assessment` to SUBMITTED and freeze its dimension_scores
    snapshot — mirrors exactly what `POST /initiatives/{id}/submit` does at
    submission time (D-03), without needing a second HTTP round-trip per
    fixture."""
    assessment.dimension_scores = compute_dimension_scores(session, assessment.id, config)
    assessment.status = AssessmentStatus.submitted
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


def _fully_answered_submitted_initiative(session):
    """Build a user + owned initiative + a fully-answered, frozen-snapshot
    SUBMITTED Assessment — the shape every report endpoint now requires
    (RESEARCH Pitfall 1: a draft assessment must never satisfy the report
    endpoints' post-submission resolver)."""
    config = load_dssc_questionnaire_config()
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative, status=AssessmentStatus.draft)
    _answer_all_questions(session, initiative, assessment, config)
    _submit(session, initiative, assessment, config)
    return user, initiative, assessment, config


# ---------------------------------------------------------------------------
# mail_report / download_report_pdf / generate_report (POST /report)
# ---------------------------------------------------------------------------


def test_mail_report_generates_pdf_and_sends_email(client, session, monkeypatch, mocker):
    from app.api.v1 import reports as reports_module

    # RESEND_API_KEY must be non-empty, else _send_report_email takes the
    # dev-mode skip path and never calls the mocked resend.Emails.send.
    monkeypatch.setattr(reports_module.settings, "RESEND_API_KEY", "test-resend-api-key")
    mock_html_cls = mocker.patch("weasyprint.HTML")
    mock_html_cls.return_value.write_pdf.return_value = b"%PDF-FAKE-BYTES"
    mock_send = mocker.patch("resend.Emails.send")

    user, initiative, _assessment, _config = _fully_answered_submitted_initiative(session)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report/mail")
    assert response.status_code == 202

    # TestClient runs BackgroundTasks synchronously before the response
    # context exits — these assertions catch a silently-broken background
    # task that the bare 202 would miss.
    mock_html_cls.return_value.write_pdf.assert_called_once()
    mock_send.assert_called_once()

    sent_params = mock_send.call_args[0][0]
    assert sent_params["attachments"][0]["filename"] == "MAMI-Interoperability-Report.pdf"


def test_mail_report_dev_mode_skips_resend_send(client, session, monkeypatch, mocker):
    from app.api.v1 import reports as reports_module

    # Empty RESEND_API_KEY is the current, intentional dev-mode behavior —
    # the endpoint still returns 202 but must NOT call resend.Emails.send.
    monkeypatch.setattr(reports_module.settings, "RESEND_API_KEY", "")
    mock_html_cls = mocker.patch("weasyprint.HTML")
    mock_html_cls.return_value.write_pdf.return_value = b"%PDF-FAKE-BYTES"
    mock_send = mocker.patch("resend.Emails.send")

    user, initiative, _assessment, _config = _fully_answered_submitted_initiative(session)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report/mail")
    assert response.status_code == 202
    mock_send.assert_not_called()


def test_mail_report_no_submitted_assessment_returns_404(client, session):
    """RESEARCH Pitfall 1 — the primary bug this phase fixes: no submitted
    assessment at all (never submitted) now correctly 404s, never 422."""
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report/mail")
    assert response.status_code == 404
    assert response.json()["detail"] == "Report not found"


def test_download_report_pdf_returns_pdf_content_type(client, session, mocker):
    mock_html_cls = mocker.patch("weasyprint.HTML")
    mock_html_cls.return_value.write_pdf.return_value = b"%PDF-FAKE-BYTES"

    user, initiative, _assessment, _config = _fully_answered_submitted_initiative(session)
    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    mock_html_cls.return_value.write_pdf.assert_called_once()


def test_download_report_pdf_no_submitted_assessment_returns_404(client, session):
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report/pdf")
    assert response.status_code == 404
    assert response.json()["detail"] == "Report not found"


def test_generate_report_returns_html_with_no_persistence(client, session):
    """Renders fresh HTML every time — no `compliance_report` row is ever
    written (RESEARCH Pitfall 2, decision A1: compute-on-read, not
    persisted)."""
    user, initiative, _assessment, _config = _fully_answered_submitted_initiative(session)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert len(response.text) > 0
    assert "<svg" in response.text

    # Regenerating renders fresh again — no upsert/unique-constraint state to
    # collide on now that ComplianceReport is gone from this path.
    second = client.post(f"/api/v1/initiatives/{initiative.id}/report")
    assert second.status_code == 200
    assert second.text == response.text


def test_generate_report_no_submitted_assessment_returns_404(client, session):
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report")
    assert response.status_code == 404
    assert response.json()["detail"] == "Report not found"


def test_get_report_renders_fresh_html_without_prior_post(client, session):
    """GET /report no longer requires a prior POST /report — it renders
    fresh from the resolved assessment's contract, identically to POST
    (RESEARCH Pitfall 2, decision A1)."""
    user, initiative, _assessment, _config = _fully_answered_submitted_initiative(session)
    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report")
    assert response.status_code == 200
    assert "<svg" in response.text


# ---------------------------------------------------------------------------
# /report/data (GET+POST) — the shared ReportContract (RPRT-01/02/04)
# ---------------------------------------------------------------------------


def test_post_report_data_returns_report_contract(client, session):
    user, initiative, _assessment, _config = _fully_answered_submitted_initiative(session)
    _login(client, user.email, VALID_PASSWORD)

    response = client.post(f"/api/v1/initiatives/{initiative.id}/report/data")
    assert response.status_code == 200
    body = response.json()

    assert body["radar_chart_svg"].startswith("<svg")
    assert len(body["priority_list"]) == 6
    assert len(body["dimension_scores"]) == 6
    assert len(body["maturity_bands"]) == 3
    assert "initiative" in body

    # Old MAMI-matrix contract keys must be gone entirely — not
    # present-but-empty.
    assert "matrix" not in body
    assert "topic_structure" not in body
    assert "answers" not in body


def test_get_report_data_returns_report_contract(client, session):
    """RPRT-01/02: report/data returns 200 with a radar_chart_svg and a
    6-item priority_list for a submitted assessment — the core
    post-submission behavior this phase's rebuild fixes."""
    user, initiative, _assessment, _config = _fully_answered_submitted_initiative(session)
    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report/data")
    assert response.status_code == 200
    body = response.json()

    assert body["radar_chart_svg"].startswith("<svg")
    assert len(body["priority_list"]) == 6
    assert "matrix" not in body
    assert "topic_structure" not in body


def test_get_report_data_no_submitted_assessment_returns_404_not_422(client, session):
    """RESEARCH Pitfall 1: an initiative with no submitted assessment at all
    (nothing ever created) 404s — never 422."""
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report/data")
    assert response.status_code == 404
    assert response.json()["detail"] == "Report not found"


def test_get_report_data_draft_only_still_returns_404(client, session):
    """A fully-answered but still-DRAFT (never submitted) assessment also
    404s — proves the resolver never falls back to a draft (D-03,
    RESEARCH Pitfall 1's exact regression)."""
    config = load_dssc_questionnaire_config()
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)
    assessment = make_assessment(session, initiative=initiative, status=AssessmentStatus.draft)
    _answer_all_questions(session, initiative, assessment, config)
    _login(client, user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report/data")
    assert response.status_code == 404
    assert response.json()["detail"] == "Report not found"


def test_report_data_ownership_before_assessment_resolution(client, session):
    """A different, non-owning user requesting someone else's initiative
    gets 404 for ownership (T-14-01 ordering carried forward)."""
    owner = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=owner)
    # Deliberately no assessment at all — if ownership did not run first,
    # this would otherwise still 404 via resolve_report_assessment, so the
    # distinguishing assertion is the detail message below.

    other_user = make_user(session, password=VALID_PASSWORD)
    _login(client, other_user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report/data")
    assert response.status_code == 404
    assert response.json()["detail"] == "Initiative not found"


# ---------------------------------------------------------------------------
# D-04 per-version viewing + IDOR (V4 — never leak existence via 403)
# ---------------------------------------------------------------------------


def test_report_data_specific_assessment_id_returns_that_version(client, session):
    """`?assessment_id=` targets a specific past submitted version, not just
    the latest (D-04)."""
    config = load_dssc_questionnaire_config()
    user = make_user(session, password=VALID_PASSWORD)
    initiative = make_initiative(session, user=user)

    older = make_assessment(session, initiative=initiative, status=AssessmentStatus.draft)
    _answer_all_questions(session, initiative, older, config)
    _submit(session, initiative, older, config)

    newer = make_assessment(session, initiative=initiative, status=AssessmentStatus.draft)
    _answer_all_questions(session, initiative, newer, config)
    _submit(session, initiative, newer, config)

    _login(client, user.email, VALID_PASSWORD)

    response = client.get(
        f"/api/v1/initiatives/{initiative.id}/report/data",
        params={"assessment_id": older.id},
    )
    assert response.status_code == 200
    assert response.json()["assessment_id"] == older.id
    assert response.json()["version"] == older.version


def test_report_data_foreign_assessment_id_returns_404_idor(client, session):
    """IDOR: an assessment_id belonging to a DIFFERENT initiative/user
    returns 404 — never a 200 leaking another user's data, never a 403
    confirming its existence (V4, no enumeration leak)."""
    _user_a, _initiative_a, assessment_a, _config = _fully_answered_submitted_initiative(session)

    user_b = make_user(session, password=VALID_PASSWORD)
    initiative_b = make_initiative(session, user=user_b)
    _login(client, user_b.email, VALID_PASSWORD)

    response = client.get(
        f"/api/v1/initiatives/{initiative_b.id}/report/data",
        params={"assessment_id": assessment_a.id},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Report not found"


# ---------------------------------------------------------------------------
# D-07 admin bypass (T-16-03)
# ---------------------------------------------------------------------------


def test_admin_can_view_another_users_report(client, session):
    """An ADMIN may view any initiative's report — the owner-scoped check is
    extended, not weakened (D-07)."""
    _user, initiative, _assessment, _config = _fully_answered_submitted_initiative(session)

    admin = make_user(session, role="ADMIN", password=VALID_PASSWORD)
    _login(client, admin.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report/data")
    assert response.status_code == 200
    assert len(response.json()["priority_list"]) == 6


def test_non_admin_non_owner_still_gets_404(client, session):
    """A regular non-owner user (not ADMIN) is still rejected — the admin
    bypass does not weaken the owner check for everyone else."""
    _user, initiative, _assessment, _config = _fully_answered_submitted_initiative(session)

    other_user = make_user(session, password=VALID_PASSWORD)
    _login(client, other_user.email, VALID_PASSWORD)

    response = client.get(f"/api/v1/initiatives/{initiative.id}/report/data")
    assert response.status_code == 404
    assert response.json()["detail"] == "Initiative not found"


# ---------------------------------------------------------------------------
# RPRT-04 contract parity — identical radar_chart_svg/priority_list in the
# JSON contract and the rendered report.html context
# ---------------------------------------------------------------------------


def test_report_data_and_html_share_identical_contract_values(client, session):
    """The exact `radar_chart_svg` string and `priority_list` values in the
    `/report/data` JSON response also appear in the rendered `report.html` —
    proving one shared contract feeds both surfaces (RPRT-04), never two
    independently-built payloads. Neither GET /report/data nor GET /report
    touches WeasyPrint (only /report/pdf and /report/mail do), so this test
    needs no mocking and is not subject to Pitfall 4's local-env gap."""
    user, initiative, _assessment, _config = _fully_answered_submitted_initiative(session)
    _login(client, user.email, VALID_PASSWORD)

    json_response = client.get(f"/api/v1/initiatives/{initiative.id}/report/data")
    assert json_response.status_code == 200
    contract = json_response.json()

    html_response = client.get(f"/api/v1/initiatives/{initiative.id}/report")
    assert html_response.status_code == 200
    html = html_response.text

    # The exact SVG markup from the JSON contract appears verbatim in the
    # rendered HTML (D-02 — one computation, reused verbatim).
    assert contract["radar_chart_svg"] in html

    # Every priority-list row's name/band label/2dp score appears in the HTML.
    for row in contract["priority_list"]:
        assert row["name"] in html
        assert row["band_label"] in html
        assert f"{row['score']:.2f}" in html
