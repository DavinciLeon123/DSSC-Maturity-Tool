"""Characterization tests for the auth subsystem (backend/app/api/v1/auth.py).

Per D-04 (.planning/phases/12-test-retrofit-stabilize-existing-flows/12-CONTEXT.md),
these tests pin the CURRENT behavior as the regression baseline for Phases
13-18, which do not touch auth. Anti-enumeration (identical 401 for
wrong-password vs non-existent-email, 202 for known/unknown forgot-password
emails), account-lockout, and one-time-use reset-token behavior are all
intentional, existing controls being characterized — not bugs to fix here.
"""

from datetime import datetime, timedelta

from app.api.v1 import auth as auth_module
from tests.factories import make_user

VALID_PASSWORD = "Str0ngPassw0rd!123"


# ---------------------------------------------------------------------------
# Task 1: Registration + login
# ---------------------------------------------------------------------------


def test_register_returns_201_with_user_read_shape(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": VALID_PASSWORD,
            "participant_type": "DSI",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "newuser@example.com"
    assert body["role"] == "USER"
    assert body["participant_type"] == "DSI"
    assert "id" in body
    assert "created_at" in body


def test_register_duplicate_email_returns_409(client):
    email = "dupe@example.com"
    first = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "participant_type": "DSI"},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "participant_type": "DSI"},
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "Email already registered"


def test_login_success_returns_bearer_token(client, session):
    user = make_user(session, password=VALID_PASSWORD)

    response = client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": VALID_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_returns_401(client, session):
    user = make_user(session, password=VALID_PASSWORD)

    response = client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": "TotallyWrongPassword1"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_nonexistent_email_returns_same_401_as_wrong_password(client):
    # Characterizes auth.py's timing-equalization/anti-enumeration branch
    # (the `_DUMMY_HASH` path): a login attempt for an email that was never
    # registered must be structurally indistinguishable from a wrong-password
    # attempt for a real account — same status code AND same detail string.
    # Deliberately NOT a wall-clock timing assertion (those are flaky in CI,
    # per RESEARCH.md's Security Domain note) — structural equivalence only.
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "nobody-at-all@example.com", "password": "DoesNotMatter123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


# ---------------------------------------------------------------------------
# Task 2: Account lockout + forgot/reset password
# ---------------------------------------------------------------------------


def test_login_lockout_after_five_failed_attempts_returns_423(client, session):
    # Characterizes auth.py's _MAX_FAILED_ATTEMPTS = 5 / _LOCKOUT_MINUTES = 15
    # behavior. All 6 attempts are kept in one test (per RESEARCH.md Pitfall 4 /
    # the plan's note) — the rate limiter is disabled session-wide by
    # conftest.py's autouse fixture, but this documents the intent that a
    # lockout test's attempt count should stay well under any rate-limit window
    # regardless.
    user = make_user(session, password=VALID_PASSWORD)

    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": user.email, "password": "WrongPassword123!"},
        )
        assert response.status_code == 401

    sixth = client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": "WrongPassword123!"},
    )
    assert sixth.status_code == 423
    assert "locked" in sixth.json()["detail"].lower()


def test_login_success_after_partial_failed_streak_resets_failed_attempts(client, session):
    # Characterizes auth.py's success-path reset (failed_login_attempts = 0,
    # lockout_until = None) — a partial (<5) failure streak must not persist
    # once a login succeeds.
    user = make_user(session, password=VALID_PASSWORD)

    for _ in range(3):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": user.email, "password": "WrongPassword123!"},
        )
        assert response.status_code == 401

    success = client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": VALID_PASSWORD},
    )
    assert success.status_code == 200

    session.refresh(user)
    assert user.failed_login_attempts == 0
    assert user.lockout_until is None


def test_forgot_password_dev_mode_skips_resend_send(client, session, monkeypatch, mocker):
    # Characterizes the dev-mode fallback (_send_reset_email): with an empty
    # RESEND_API_KEY, the endpoint must still return 202 but must NOT call
    # resend.Emails.send (it logs the reset link instead).
    monkeypatch.setattr(auth_module.settings, "RESEND_API_KEY", "")
    mock_send = mocker.patch("resend.Emails.send")

    user = make_user(session, password=VALID_PASSWORD)
    response = client.post("/api/v1/auth/forgot-password", json={"email": user.email})

    assert response.status_code == 202
    mock_send.assert_not_called()


def test_forgot_password_with_api_key_set_calls_resend_send(client, session, monkeypatch, mocker):
    # Characterizes the "real" email path (Open Question 2, part b): with a
    # non-empty RESEND_API_KEY, the endpoint calls resend.Emails.send exactly
    # once (mocked here — never hits the real Resend API from tests).
    monkeypatch.setattr(auth_module.settings, "RESEND_API_KEY", "test-resend-api-key")
    mock_send = mocker.patch("resend.Emails.send")

    user = make_user(session, password=VALID_PASSWORD)
    response = client.post("/api/v1/auth/forgot-password", json={"email": user.email})

    assert response.status_code == 202
    mock_send.assert_called_once()


def test_forgot_password_unknown_email_also_returns_202(client):
    # Anti-enumeration (D-04, intentional): forgot-password must never reveal
    # whether an email is registered — same 202 for a real vs. unknown email.
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "totally-unregistered@example.com"},
    )
    assert response.status_code == 202


def test_forgot_password_cooldown_returns_429_on_immediate_second_request(client, session):
    # Characterizes the 60-second cooldown: a second forgot-password request
    # for the same user, issued immediately after the first, must return 429.
    user = make_user(session, password=VALID_PASSWORD)

    first = client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    assert first.status_code == 202

    second = client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    assert second.status_code == 429


def test_reset_password_valid_token_returns_200_and_allows_login_with_new_password(client, session):
    # Drives a real token through forgot-password (rather than fabricating
    # one), then reads it back off the test session per the plan's guidance.
    user = make_user(session, password=VALID_PASSWORD)
    client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    session.refresh(user)
    token = user.password_reset_token
    assert token is not None

    new_password = "NewStr0ngPassw0rd!456"
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )
    assert response.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": new_password},
    )
    assert login.status_code == 200


def test_reset_password_token_reuse_returns_400(client, session):
    # One-time-use characterization: the token is cleared after first use, so
    # a second reset-password call with the same token must fail with 400.
    user = make_user(session, password=VALID_PASSWORD)
    client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    session.refresh(user)
    token = user.password_reset_token

    first = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "AnotherStr0ngPassw0rd!789"},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "YetAnotherStr0ngPassw0rd!012"},
    )
    assert second.status_code == 400


def test_reset_password_expired_token_returns_400(client, session):
    # Manually expires the token (set password_reset_expires in the past via
    # the test session) and asserts the endpoint rejects it with 400.
    user = make_user(session, password=VALID_PASSWORD)
    client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    session.refresh(user)
    token = user.password_reset_token

    user.password_reset_expires = datetime.utcnow() - timedelta(minutes=1)
    session.add(user)
    session.commit()

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "ExpiredFlowStr0ngPassw0rd!345"},
    )
    assert response.status_code == 400


def test_reset_password_unknown_token_returns_400(client):
    # Characterizes the "no matching user for this token" branch — read_first
    # flags this as part of reset_password's 400 paths alongside expiry/reuse.
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "not-a-real-token-at-all", "new_password": "SomeStr0ngPassw0rd!678"},
    )
    assert response.status_code == 400
