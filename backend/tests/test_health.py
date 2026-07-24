from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        # Proves the lifespan-aware TestClient context manager actually fired
        # app.main.py's lifespan() — a bare TestClient(app) never populates
        # app.state, and every questionnaire/scoring/report endpoint would
        # raise AttributeError on first use if this silently regressed.
        assert client.app.state.dssc_questionnaire_config is not None
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
