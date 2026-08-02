"""Report API endpoints — generate and retrieve DSSC maturity reports.

Phase 16 (D-03/D-04, RESEARCH Pitfall 1): every endpoint now resolves its
assessment via the submitted-scoped `resolve_report_assessment` (never a
draft-scoped lookup) — this is what makes a real post-submission report
reachable at all; previously every endpoint 422'd unconditionally the
moment an assessment was actually submitted. An optional `assessment_id`
query param lets any endpoint target a specific past submitted version
(D-04).

Phase 16 (RESEARCH Pitfall 2, decision A1 — see 16-RESEARCH.md Open
Question 1, and this plan's SUMMARY for the removed-storage decision):
every read recomputes the report contract fresh from the frozen
`Assessment.dimension_scores` snapshot (falling back to a live recompute
only for legacy submitted rows whose snapshot is null, D-03) — there is no
correctness or performance reason to persist a second copy of a rendered
report.
"""

import logging
from datetime import datetime

import resend
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_dssc_questionnaire_config
from app.db.session import get_session
from app.models.assessment import Assessment
from app.models.initiative import Initiative
from app.models.user import User
from app.schemas.report import ReportContract
from app.services.dimension_scoring import compute_dimension_scores, resolve_report_assessment
from app.services.report_generator import (
    build_answers_by_category,
    build_report_contract,
    generate_html_report,
)

router = APIRouter(tags=["reports"])


logger = logging.getLogger(__name__)


def _get_authorized_initiative(
    session: Session, initiative_id: int, current_user: User
) -> Initiative:
    """Ownership check extended for the D-07 admin bypass: an ADMIN may view
    any initiative's report; a non-admin non-owner (or a nonexistent
    initiative) gets 404 — never 403, matching every other ownership check
    in this file (no existence leak). The owner-scoped check itself is not
    weakened for non-admins — admin access is granted only via the extra
    `current_user.role == "ADMIN"` branch (T-16-03)."""
    initiative = session.get(Initiative, initiative_id)
    if not initiative or (initiative.user_id != current_user.id and current_user.role != "ADMIN"):
        raise HTTPException(status_code=404, detail="Initiative not found")
    return initiative


def _resolve_scores(session: Session, assessment: Assessment, config: dict) -> list[dict]:
    """Prefer the frozen `Assessment.dimension_scores` snapshot (D-03); fall
    back to a live recompute only for legacy submitted rows whose snapshot
    is null — mirrors initiatives.py's `_to_summary` idiom exactly."""
    assert assessment.id is not None  # always a persisted, submitted row
    return (
        assessment.dimension_scores
        if assessment.dimension_scores is not None
        else compute_dimension_scores(session, assessment.id, config)
    )


def _initiative_dict(initiative: Initiative) -> dict:
    return {
        "name": initiative.name,
        "organization": initiative.organization,
        "contact_name": initiative.contact_name,
        # D-12/Pitfall 5: participant_type is nullable now — guard .value.
        "participant_type": (
            initiative.participant_type.value if initiative.participant_type else None
        ),
    }


def _generated_at_str() -> str:
    now = datetime.utcnow()
    return f"{now.day} {now.strftime('%B %Y, %H:%M')} UTC"


def _render_html_for(
    session: Session, initiative: Initiative, assessment: Assessment, config: dict
) -> str:
    """RPRT-04: builds the shared contract once, then feeds its keys into
    the Jinja2 template — the same contract dict `/report/data` returns
    verbatim as JSON (one payload, two renderings). RPRT-05: also builds
    answers_by_category for the new submitted-answers section."""
    scores = _resolve_scores(session, assessment, config)
    contract = build_report_contract(scores, initiative, assessment, config)
    answers_by_category = build_answers_by_category(session, assessment.id, config)
    return generate_html_report(
        initiative=_initiative_dict(initiative),
        generated_at=_generated_at_str(),
        dimension_scores=contract["dimension_scores"],
        priority_list=contract["priority_list"],
        radar_chart_svg=contract["radar_chart_svg"],
        maturity_bands=contract["maturity_bands"],
        answers_by_category=answers_by_category,
    )


def _send_report_email(email: str, html_content: str, api_key: str) -> None:
    """Generate PDF from HTML and email it as attachment via Resend."""
    try:
        if not api_key:
            logger.warning("[MAIL] RESEND_API_KEY not set — skipping email to %s", email)
            return
        logger.info("[MAIL] Generating PDF for %s", email)
        from weasyprint import HTML as WeasyHTML

        pdf_bytes: bytes = WeasyHTML(string=html_content).write_pdf()
        logger.info("[MAIL] PDF generated (%d bytes), sending via Resend", len(pdf_bytes))
        attachment: resend.Attachment = {
            "content": list(pdf_bytes),
            "filename": "MAMI-Interoperability-Report.pdf",
        }
        resend.api_key = api_key
        params: resend.Emails.SendParams = {
            "from": "MaMi Checker <onboarding@resend.dev>",
            "to": [email],
            "subject": "Your MAMI Interoperability Heatmap",
            "text": (
                "Dear participant,\n\n"
                "Thank you for completing the MAMI Interoperability Assessment. "
                "Please find your personalised Interoperability Heatmap report attached as a PDF.\n\n"
                "Would you like expert guidance on your results? The Centre of Excellence "
                "for Data Sharing and Cloud (CoE-DSC) is available to help you translate "
                "your assessment into a concrete improvement plan. Visit the CoE-DSC website "
                "or contact us directly to schedule a follow-up conversation.\n\n"
                "Kind regards,\n"
                "The MAMI Checker team\n"
                "Centre of Excellence for Data Sharing and Cloud (CoE-DSC)"
            ),
            "attachments": [attachment],
        }
        resend.Emails.send(params)
        logger.info("[MAIL] Report email sent successfully to %s", email)
    except Exception:
        logger.exception("[MAIL] Failed to send report email to %s", email)


@router.post("/initiatives/{initiative_id}/report", response_class=HTMLResponse)
def generate_report(
    initiative_id: int,
    assessment_id: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    config: dict = Depends(get_dssc_questionnaire_config),
):
    """Render the compliance report as HTML on the fly from the shared
    report contract and return it directly — no persistence (RESEARCH
    Pitfall 2, decision A1)."""
    initiative = _get_authorized_initiative(session, initiative_id, current_user)
    assessment = resolve_report_assessment(session, initiative_id, assessment_id)
    html_content = _render_html_for(session, initiative, assessment, config)
    return HTMLResponse(content=html_content, status_code=200)


@router.get("/initiatives/{initiative_id}/report", response_class=HTMLResponse)
def get_report(
    initiative_id: int,
    assessment_id: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    config: dict = Depends(get_dssc_questionnaire_config),
):
    """Identical rendering path to POST /report — there is no stored report
    to look up anymore (RESEARCH Pitfall 2), so this always renders fresh
    from the resolved assessment's frozen contract."""
    initiative = _get_authorized_initiative(session, initiative_id, current_user)
    assessment = resolve_report_assessment(session, initiative_id, assessment_id)
    html_content = _render_html_for(session, initiative, assessment, config)
    return HTMLResponse(content=html_content, status_code=200)


@router.post("/initiatives/{initiative_id}/report/data", response_model=ReportContract)
def generate_report_data_endpoint(
    initiative_id: int,
    assessment_id: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    config: dict = Depends(get_dssc_questionnaire_config),
):
    """Return the shared ReportContract dict (RPRT-04) for a submitted
    assessment — the same payload the in-app report page and the PDF/mail
    paths render from."""
    initiative = _get_authorized_initiative(session, initiative_id, current_user)
    assessment = resolve_report_assessment(session, initiative_id, assessment_id)
    scores = _resolve_scores(session, assessment, config)
    return build_report_contract(scores, initiative, assessment, config)


@router.get("/initiatives/{initiative_id}/report/data", response_model=ReportContract)
def get_report_data_endpoint(
    initiative_id: int,
    assessment_id: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    config: dict = Depends(get_dssc_questionnaire_config),
):
    """Retrieve the shared ReportContract dict for an initiative's submitted
    assessment (default: the latest; or a specific past version via
    `?assessment_id=`, D-04) — the primary read path for the in-app React
    report page."""
    initiative = _get_authorized_initiative(session, initiative_id, current_user)
    assessment = resolve_report_assessment(session, initiative_id, assessment_id)
    scores = _resolve_scores(session, assessment, config)
    return build_report_contract(scores, initiative, assessment, config)


@router.get("/initiatives/{initiative_id}/report/pdf")
def download_report_pdf(
    initiative_id: int,
    assessment_id: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    config: dict = Depends(get_dssc_questionnaire_config),
):
    """Generate the compliance report as a PDF and return it as a file download."""
    from fastapi.responses import Response
    from weasyprint import HTML as WeasyHTML

    initiative = _get_authorized_initiative(session, initiative_id, current_user)
    assessment = resolve_report_assessment(session, initiative_id, assessment_id)
    html_content = _render_html_for(session, initiative, assessment, config)
    pdf_bytes: bytes = WeasyHTML(string=html_content).write_pdf()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=MAMI-Interoperability-Report.pdf"},
    )


@router.post("/initiatives/{initiative_id}/report/mail", status_code=202)
def mail_report(
    initiative_id: int,
    background_tasks: BackgroundTasks,
    assessment_id: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    config: dict = Depends(get_dssc_questionnaire_config),
):
    """Email the compliance report as a PDF attachment to the authenticated user."""
    initiative = _get_authorized_initiative(session, initiative_id, current_user)
    assessment = resolve_report_assessment(session, initiative_id, assessment_id)
    html_content = _render_html_for(session, initiative, assessment, config)

    background_tasks.add_task(
        _send_report_email,
        current_user.email,
        html_content,
        settings.RESEND_API_KEY,
    )
    return {"message": "Your report is being emailed to your address. This may take a moment."}
