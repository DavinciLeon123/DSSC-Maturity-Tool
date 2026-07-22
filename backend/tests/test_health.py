from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        # Proves the lifespan-aware TestClient context manager actually fired
        # app.main.py's lifespan() — a bare TestClient(app) never populates
        # app.state, and every admin-heatmap/reports endpoint would raise
        # AttributeError on first use if this silently regressed.
        assert client.app.state.mami_config is not None
        assert client.app.state.zen_engine is not None
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
