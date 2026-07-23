"""Report API endpoints — generate and retrieve MAMI compliance reports."""

import logging
from datetime import datetime

import resend
import zen
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, select

from app.core.config import settings
from app.core.deps import get_current_user, get_mami_config, get_zen_engine
from app.db.session import get_session
from app.models.initiative import Initiative
from app.models.questionnaire import QuestionnaireAnswer
from app.models.report import ComplianceReport
from app.models.user import User
from app.services.report_generator import generate_html_report, generate_report_data
from app.services.scoring_engine import score_all_answers

router = APIRouter(tags=["reports"])


logger = logging.getLogger(__name__)


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
async def generate_report(
    initiative_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    engine: zen.ZenEngine = Depends(get_zen_engine),
    mami_config: dict = Depends(get_mami_config),
):
    """Generate a compliance report for an initiative.

    Scores all saved answers, renders a full HTML report via Jinja2, and
    upserts the result into the compliance_report table. Returns the
    rendered HTML directly.
    """
    initiative = session.get(Initiative, initiative_id)
    if not initiative or initiative.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Initiative not found")

    # Load saved answers
    answers = session.exec(
        select(QuestionnaireAnswer).where(QuestionnaireAnswer.initiative_id == initiative_id)
    ).all()

    # Build code metadata lookup for scoring
    code_lookup = {c["id"]: c for c in mami_config.get("codes", [])}

    answers_for_scoring = [
        {
            "mami_code": a.mami_code,
            "moscow_level": code_lookup.get(a.mami_code, {}).get("moscow_level", "SHOULD"),
            "answer_value": a.answer_value,
            "critical_override": code_lookup.get(a.mami_code, {}).get("critical_override"),
        }
        for a in answers
    ]

    # Score answers — returns only FINDING-status entries
    findings_raw = await score_all_answers(engine, answers_for_scoring)

    # Prepare plain-dict versions for the generator
    answers_dict = [
        {
            "mami_code": a.mami_code,
            "answer_value": a.answer_value,
            "followup_selections": a.followup_selections or [],
            "followup_other": a.followup_other or "",
        }
        for a in answers
    ]
    initiative_dict = {
        "name": initiative.name,
        "organization": initiative.organization,
        "contact_name": initiative.contact_name,
        "participant_type": initiative.participant_type.value,
    }

    # Render the HTML report
    html_content = generate_html_report(
        initiative=initiative_dict,
        answers=answers_dict,
        findings=findings_raw,
        mami_config=mami_config,
    )

    # Compute counts
    critical_count = sum(1 for f in findings_raw if f.get("severity") == "CRITICAL")
    non_critical_count = sum(1 for f in findings_raw if f.get("severity") == "NON_CRITICAL")
    compliant_count = len(answers) - sum(1 for f in findings_raw if f.get("status") == "FINDING")

    # Upsert: one report per initiative — regeneration replaces previous report
    stmt = (
        pg_insert(ComplianceReport)
        .values(
            initiative_id=initiative_id,
            html_content=html_content,
            generated_at=datetime.utcnow(),
            questionnaire_version="2.0",
            total_answers=len(answers),
            critical_count=critical_count,
            non_critical_count=non_critical_count,
            compliant_count=compliant_count,
        )
        .on_conflict_do_update(
            index_elements=["initiative_id"],
            set_={
                "html_content": pg_insert(ComplianceReport).excluded.html_content,
                "generated_at": pg_insert(ComplianceReport).excluded.generated_at,
                "questionnaire_version": pg_insert(ComplianceReport).excluded.questionnaire_version,
                "total_answers": pg_insert(ComplianceReport).excluded.total_answers,
                "critical_count": pg_insert(ComplianceReport).excluded.critical_count,
                "non_critical_count": pg_insert(ComplianceReport).excluded.non_critical_count,
                "compliant_count": pg_insert(ComplianceReport).excluded.compliant_count,
            },
        )
    )
    session.exec(stmt)
    session.commit()

    return HTMLResponse(content=html_content, status_code=200)


@router.get("/initiatives/{initiative_id}/report", response_class=HTMLResponse)
def get_report(
    initiative_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the stored compliance report HTML for an initiative."""
    initiative = session.get(Initiative, initiative_id)
    if not initiative or initiative.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Initiative not found")

    report = session.exec(
        select(ComplianceReport).where(ComplianceReport.initiative_id == initiative_id)
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="No report generated yet")

    return HTMLResponse(content=report.html_content, status_code=200)


@router.post("/initiatives/{initiative_id}/report/data")
async def generate_report_data_endpoint(
    initiative_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    engine: zen.ZenEngine = Depends(get_zen_engine),
    mami_config: dict = Depends(get_mami_config),
):
    """Generate and return structured JSON report data for the React /report page."""
    initiative = session.get(Initiative, initiative_id)
    if not initiative or initiative.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Initiative not found")

    # Load saved answers
    answers = session.exec(
        select(QuestionnaireAnswer).where(QuestionnaireAnswer.initiative_id == initiative_id)
    ).all()

    # Build code metadata lookup for scoring
    code_lookup = {c["id"]: c for c in mami_config.get("codes", [])}

    answers_for_scoring = [
        {
            "mami_code": a.mami_code,
            "moscow_level": code_lookup.get(a.mami_code, {}).get("moscow_level", "SHOULD"),
            "answer_value": a.answer_value,
            "critical_override": code_lookup.get(a.mami_code, {}).get("critical_override"),
        }
        for a in answers
    ]

    # Score answers — returns only FINDING-status entries
    findings_raw = await score_all_answers(engine, answers_for_scoring)

    # Prepare plain-dict versions for the generator
    answers_dict = [
        {
            "mami_code": a.mami_code,
            "answer_value": a.answer_value,
            "followup_selections": a.followup_selections or [],
            "followup_other": a.followup_other or "",
        }
        for a in answers
    ]

    return generate_report_data(
        initiative=initiative,
        answers=answers_dict,
        findings=findings_raw,
        mami_config=mami_config,
    )


@router.get("/initiatives/{initiative_id}/report/data")
async def get_report_data_endpoint(
    initiative_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    engine: zen.ZenEngine = Depends(get_zen_engine),
    mami_config: dict = Depends(get_mami_config),
):
    """Retrieve structured JSON report data for an initiative.

    Re-runs scoring on the fly from stored answers to avoid storing JSON separately.
    Returns 404 if no report has been generated yet.
    """
    initiative = session.get(Initiative, initiative_id)
    if not initiative or initiative.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Initiative not found")

    # Check a report exists (i.e. the user has generated one before)
    report = session.exec(
        select(ComplianceReport).where(ComplianceReport.initiative_id == initiative_id)
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="No report generated yet")

    # Regenerate from current answers (avoids schema change for JSON storage)
    answers = session.exec(
        select(QuestionnaireAnswer).where(QuestionnaireAnswer.initiative_id == initiative_id)
    ).all()

    code_lookup = {c["id"]: c for c in mami_config.get("codes", [])}

    answers_for_scoring = [
        {
            "mami_code": a.mami_code,
            "moscow_level": code_lookup.get(a.mami_code, {}).get("moscow_level", "SHOULD"),
            "answer_value": a.answer_value,
            "critical_override": code_lookup.get(a.mami_code, {}).get("critical_override"),
        }
        for a in answers
    ]

    findings_raw = await score_all_answers(engine, answers_for_scoring)

    answers_dict = [
        {
            "mami_code": a.mami_code,
            "answer_value": a.answer_value,
            "followup_selections": a.followup_selections or [],
            "followup_other": a.followup_other or "",
        }
        for a in answers
    ]

    return generate_report_data(
        initiative=initiative,
        answers=answers_dict,
        findings=findings_raw,
        mami_config=mami_config,
    )


@router.get("/initiatives/{initiative_id}/report/pdf")
async def download_report_pdf(
    initiative_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    engine: zen.ZenEngine = Depends(get_zen_engine),
    mami_config: dict = Depends(get_mami_config),
):
    """Generate the compliance report as a PDF and return it as a file download."""
    from fastapi.responses import Response
    from weasyprint import HTML as WeasyHTML

    initiative = session.get(Initiative, initiative_id)
    if not initiative or initiative.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Initiative not found")

    answers = session.exec(
        select(QuestionnaireAnswer).where(QuestionnaireAnswer.initiative_id == initiative_id)
    ).all()
    if not answers:
        raise HTTPException(
            status_code=422, detail="No answers found. Please complete the questionnaire first."
        )

    code_lookup = {c["id"]: c for c in mami_config.get("codes", [])}
    answers_for_scoring = [
        {
            "mami_code": a.mami_code,
            "moscow_level": code_lookup.get(a.mami_code, {}).get("moscow_level", "SHOULD"),
            "answer_value": a.answer_value,
            "critical_override": code_lookup.get(a.mami_code, {}).get("critical_override"),
        }
        for a in answers
    ]
    findings_raw = await score_all_answers(engine, answers_for_scoring)

    answers_dict = [
        {
            "mami_code": a.mami_code,
            "answer_value": a.answer_value,
            "followup_selections": a.followup_selections or [],
            "followup_other": a.followup_other or "",
        }
        for a in answers
    ]
    initiative_dict = {
        "name": initiative.name,
        "organization": initiative.organization,
        "contact_name": initiative.contact_name,
        "participant_type": initiative.participant_type.value,
    }
    html_content = generate_html_report(
        initiative=initiative_dict,
        answers=answers_dict,
        findings=findings_raw,
        mami_config=mami_config,
    )
    pdf_bytes: bytes = WeasyHTML(string=html_content).write_pdf()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=MAMI-Interoperability-Report.pdf"},
    )


@router.post("/initiatives/{initiative_id}/report/mail", status_code=202)
async def mail_report(
    initiative_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    engine: zen.ZenEngine = Depends(get_zen_engine),
    mami_config: dict = Depends(get_mami_config),
):
    """Email the compliance report as a PDF attachment to the authenticated user.

    Generates HTML on the fly from current answers so it always works,
    regardless of whether the old /report endpoint has been called.
    """
    initiative = session.get(Initiative, initiative_id)
    if not initiative or initiative.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Initiative not found")

    answers = session.exec(
        select(QuestionnaireAnswer).where(QuestionnaireAnswer.initiative_id == initiative_id)
    ).all()
    if not answers:
        raise HTTPException(
            status_code=422, detail="No answers found. Please complete the questionnaire first."
        )

    code_lookup = {c["id"]: c for c in mami_config.get("codes", [])}
    answers_for_scoring = [
        {
            "mami_code": a.mami_code,
            "moscow_level": code_lookup.get(a.mami_code, {}).get("moscow_level", "SHOULD"),
            "answer_value": a.answer_value,
            "critical_override": code_lookup.get(a.mami_code, {}).get("critical_override"),
        }
        for a in answers
    ]
    findings_raw = await score_all_answers(engine, answers_for_scoring)

    answers_dict = [
        {
            "mami_code": a.mami_code,
            "answer_value": a.answer_value,
            "followup_selections": a.followup_selections or [],
            "followup_other": a.followup_other or "",
        }
        for a in answers
    ]
    initiative_dict = {
        "name": initiative.name,
        "organization": initiative.organization,
        "contact_name": initiative.contact_name,
        "participant_type": initiative.participant_type.value,
    }
    html_content = generate_html_report(
        initiative=initiative_dict,
        answers=answers_dict,
        findings=findings_raw,
        mami_config=mami_config,
    )

    background_tasks.add_task(
        _send_report_email,
        current_user.email,
        html_content,
        settings.RESEND_API_KEY,
    )
    return {"message": "Your report is being emailed to your address. This may take a moment."}
