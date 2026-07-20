"""Release-gate canary: asserts secret material never leaks into responses.

Doesn't require a live database — validation/404 paths short-circuit before any
query executes, so this stays fast and DB-independent while still exercising the
real request pipeline (see app/core/config.py for the settings being checked).
"""

import json

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_no_secrets_leak_into_responses():
    with TestClient(app) as client:
        validation_error = client.post("/api/v1/auth/register", json={"email": "not-an-email"})
        not_found = client.get("/api/v1/does-not-exist")
        schema_text = json.dumps(client.get("/openapi.json").json())

    for response_text in (validation_error.text, not_found.text, schema_text):
        assert settings.SECRET_KEY not in response_text
        assert settings.DATABASE_URL not in response_text
        assert settings.ADMIN_PASSWORD not in response_text
