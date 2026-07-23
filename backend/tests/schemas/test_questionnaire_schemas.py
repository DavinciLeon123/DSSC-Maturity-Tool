"""Unit tests for the reshaped questionnaire answer schema and its new
supporting models (Phase 13, D-01/D-02/D-06/D-07).

AnswerCreate/AnswerRead now key off assessment_id/category_id/score (1-5),
not the old initiative_id/mami_code/answer_value shape — security V5 (score
range) is enforced at the Pydantic layer here. These are pure schema/model
unit tests — no DB/HTTP dependency, mirroring
tests/services/test_report_generator.py's style.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.assessment import Assessment, AssessmentStatus
from app.models.questionnaire import QuestionnaireAnswer
from app.models.questionnaire_answer_archive import QuestionnaireAnswerV1Archive
from app.schemas.questionnaire import AnswerCreate, AnswerRead


@pytest.mark.parametrize("score", [1, 2, 3, 4, 5])
def test_answer_create_accepts_in_range_scores(score):
    answer = AnswerCreate(question_id="q-1-1", category_id="cat-1", score=score)
    assert answer.score == score


@pytest.mark.parametrize("score", [0, -1, 6, 100])
def test_answer_create_rejects_out_of_range_scores(score):
    # Security V5 — reject an out-of-range score at the Pydantic layer,
    # not just leave it to an (also present, 13-04) DB-level CHECK.
    with pytest.raises(ValidationError):
        AnswerCreate(question_id="q-1-1", category_id="cat-1", score=score)


def test_answer_create_requires_category_id():
    with pytest.raises(ValidationError):
        AnswerCreate(question_id="q-1-1", score=3)  # type: ignore[call-arg]


def test_answer_read_from_attributes_reflects_new_shape():
    """AnswerRead.from_attributes must round-trip a real QuestionnaireAnswer
    ORM instance's new columns (assessment_id/category_id/score) — not the
    old initiative_id/mami_code/answer_value shape (D-02)."""
    row = QuestionnaireAnswer(
        id=1,
        assessment_id=7,
        question_id="q-1-1",
        category_id="cat-1",
        score=4,
        answered_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )
    read = AnswerRead.model_validate(row)
    assert read.assessment_id == 7
    assert read.category_id == "cat-1"
    assert read.score == 4


def test_questionnaire_answer_table_has_new_shape():
    """D-02/D-06: the live answer table is keyed by assessment_id/
    category_id/score — no mami_code/initiative_id column remains, and the
    unique constraint is renamed to the v2 name."""
    cols = set(QuestionnaireAnswer.__table__.columns.keys())
    assert {"assessment_id", "category_id", "score"} <= cols
    assert "mami_code" not in cols
    assert "initiative_id" not in cols

    constraint_names = {c.name for c in QuestionnaireAnswer.__table__.constraints}
    assert "uq_answer_per_question_v2" in constraint_names


def test_assessment_defaults_to_draft_status_and_version_one():
    """D-06/D-07: Assessment defaults to draft status with version 1 — a row
    is created lazily on the first answer write, not deferred to
    submission."""
    assessment = Assessment(initiative_id=1)
    assert assessment.status == AssessmentStatus.draft
    assert assessment.version == 1
    assert assessment.submitted_at is None


def test_assessment_status_constrained_to_draft_or_submitted():
    assert {s.value for s in AssessmentStatus} == {"draft", "submitted"}


def test_archive_table_has_no_initiative_fk():
    """RESEARCH Anti-Pattern / Assumption A2: the archive table must survive
    an admin hard-delete of a legacy initiative, so it deliberately carries
    NO foreign key to initiative.id (MIGR-01 preservation)."""
    table = QuestionnaireAnswerV1Archive.__table__
    assert len(table.foreign_keys) == 0
    assert "initiative_id" in table.columns.keys()


def test_archive_answer_value_is_explicit_string_column_not_enum():
    """RESEARCH Pitfall 1: answer_value must be an explicit String column,
    not a bare (str, Enum) annotation, so SQLModel.metadata.create_all()
    -built test schema and the 13-04 migration's hand-written sa.String()
    column never diverge into a native Postgres ENUM."""
    column_type = QuestionnaireAnswerV1Archive.__table__.columns["answer_value"].type
    assert type(column_type).__name__ == "String"
