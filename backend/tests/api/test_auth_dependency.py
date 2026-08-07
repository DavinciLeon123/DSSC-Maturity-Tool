"""Tests for the shared get_current_user dependency rejection paths.

No prior test file exercises the missing/invalid/expired/deleted-user token
scenarios against real protected routes (only ownership 403-vs-200 checks
with already-valid tokens existed). This suite closes that gap with 3
representative protected routes spanning questionnaire/scoring/reports and
parametrized over 4 distinct 401 code paths.
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.security import ALGORITHM, create_access_token
from tests.factories import make_initiative, make_user


# Helper to build an expired JWT directly (create_access_token has no custom-expiry param)
def _expired_token(email: str) -> str:
    """Build a JWT with an expired timestamp."""
    return jwt.encode(
        {"sub": email, "exp": datetime.now(UTC) - timedelta(hours=1)},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


# Four scenarios: no header, malformed token, expired token, deleted user
SCENARIOS = [
    {
        "name": "no_authorization_header",
        "get_headers": lambda _: {},
        "expected_detail": "Not authenticated",
    },
    {
        "name": "malformed_bearer_token",
        "get_headers": lambda _: {"Authorization": "Bearer not-a-real-jwt"},
        "expected_detail": "Invalid or expired token",
    },
    {
        "name": "expired_token",
        "get_headers": lambda email: {"Authorization": f"Bearer {_expired_token(email)}"},
        "expected_detail": "Invalid or expired token",
    },
    {
        "name": "deleted_user_token",
        "get_headers": lambda email: {"Authorization": f"Bearer {create_access_token(email)}"},
        "is_deleted_user": True,
        "expected_detail": "User not found",
    },
]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["name"])
def test_questionnaire_answer_put_rejects_invalid_auth(client, session, scenario):
    """PUT /questionnaire/initiatives/{id}/answers/{id} rejects all 4 auth failure modes."""
    # Setup: create a user (to get an email for token scenarios)
    user = make_user(session, email="test@example.com")
    initiative = make_initiative(session, user=user)

    # Get headers first, then delete user if needed (must delete initiative first due to FK)
    headers = scenario["get_headers"](user.email)
    if scenario.get("is_deleted_user"):
        session.delete(initiative)
        session.delete(user)
        session.commit()

    # Make the request with the scenario's headers
    response = client.put(
        f"/api/v1/questionnaire/initiatives/{initiative.id}/answers/q-1-1",
        headers=headers,
        json={"question_id": "q-1-1", "category_id": "cat-1", "score": 3},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == scenario["expected_detail"]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["name"])
def test_score_post_rejects_invalid_auth(client, session, scenario):
    """POST /api/v1/initiatives/{id}/score rejects all 4 auth failure modes with 401."""
    # Setup: create a user
    user = make_user(session, email="test@example.com")
    initiative = make_initiative(session, user=user)

    # Get headers first, then delete user if needed (must delete initiative first due to FK)
    headers = scenario["get_headers"](user.email)
    if scenario.get("is_deleted_user"):
        session.delete(initiative)
        session.delete(user)
        session.commit()

    # Make the request with the scenario's headers
    response = client.post(
        f"/api/v1/initiatives/{initiative.id}/score",
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == scenario["expected_detail"]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["name"])
def test_report_data_get_rejects_invalid_auth(client, session, scenario):
    """GET /api/v1/initiatives/{id}/report/data rejects all 4 auth failure modes with 401."""
    # Setup: create a user
    user = make_user(session, email="test@example.com")
    initiative = make_initiative(session, user=user)

    # Get headers first, then delete user if needed (must delete initiative first due to FK)
    headers = scenario["get_headers"](user.email)
    if scenario.get("is_deleted_user"):
        session.delete(initiative)
        session.delete(user)
        session.commit()

    # Make the request with the scenario's headers
    response = client.get(
        f"/api/v1/initiatives/{initiative.id}/report/data",
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == scenario["expected_detail"]
