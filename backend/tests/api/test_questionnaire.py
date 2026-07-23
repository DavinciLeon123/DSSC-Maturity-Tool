"""Characterization test for the universal DSSC questionnaire config
endpoint (backend/app/api/v1/questionnaire.py::get_questionnaire_config_endpoint).

Covers QSTN-04: GET /questionnaire/config must serve the identical config to
every authenticated caller regardless of participant_type, and must return
200 even when the caller owns no Initiative (assumption A1, plan 13-01).
"""

from app.services.mami_config import load_dssc_questionnaire_config


def test_config_endpoint_universal(user_client, admin_client):
    # user_client and admin_client are two independently authenticated,
    # distinct users (conftest._create_authed_user) — neither owns an
    # Initiative. Proves both the "identical across users" and "200 with no
    # Initiative" halves of QSTN-04/A1 in one assertion chain.
    response_a = user_client.get("/api/v1/questionnaire/config")
    response_b = admin_client.get("/api/v1/questionnaire/config")

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    body_a = response_a.json()
    body_b = response_b.json()

    assert body_a == body_b
    assert body_a == load_dssc_questionnaire_config()
