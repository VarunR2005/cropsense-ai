import pytest

from app.ml import crop_recommender
from app.routes import recommendations as rec_routes

BODY = {"nitrogen": 90, "phosphorus": 42, "potassium": 43, "temperature": 21,
        "humidity": 82, "ph": 6.5, "rainfall": 200}


def test_requires_login(client):
    assert client.post("/api/recommendations/crops", json=BODY).status_code == 401


def test_validation(client, auth_headers):
    r = client.post("/api/recommendations/crops", json={**BODY, "ph": 20}, headers=auth_headers)
    assert r.status_code == 422


def test_route_saves_and_returns(client, auth_headers, monkeypatch):
    """Route test only: the ML call is stubbed inside this unit test."""
    def fake(**kw):
        return {"recommendations": [{"crop": "rice", "suitability_score": 0.9, "growing_requirements": {}}],
                "warnings": [], "model_info": {}}
    monkeypatch.setattr(rec_routes, "recommend_crops", fake)
    r = client.post("/api/recommendations/crops", json=BODY, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["recommendations"][0]["crop"] == "rice"
    hist = client.get("/api/recommendations/history", headers=auth_headers).json()
    assert len(hist) == 1 and hist[0]["top_crop"] == "rice"


@pytest.mark.skipif(not crop_recommender.MODEL_PATH.exists(), reason="recommender not trained yet")
def test_real_model():
    out = crop_recommender.recommend_crops(nitrogen=90, phosphorus=42, potassium=43, temperature=21,
                                           humidity=82, ph=6.5, rainfall=200)
    recs = out["recommendations"]
    assert len(recs) == 3
    assert recs[0]["suitability_score"] >= recs[1]["suitability_score"] >= recs[2]["suitability_score"]
    far = crop_recommender.recommend_crops(nitrogen=90, phosphorus=42, potassium=43, temperature=21,
                                           humidity=82, ph=6.5, rainfall=9000)
    assert far["warnings"]
