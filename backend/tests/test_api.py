import pytest

from app.ml import yield_predictor
from app.routes import predictions as pred_routes

BODY = {"state": "Karnataka", "district": "MYSORE", "crop": "Rice", "season": "Kharif",
        "year": 2020, "area": 10, "area_unit": "acres"}


def test_register_login_me(client, auth_headers):
    r = client.get("/api/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "farmer@example.com"
    assert "hashed_password" not in r.json()


def test_duplicate_register_rejected(client, auth_headers):
    r = client.post("/api/auth/register", json={
        "full_name": "X", "email": "farmer@example.com", "password": "password123"})
    assert r.status_code == 409


def test_wrong_password(client, auth_headers):
    r = client.post("/api/auth/login", data={"username": "farmer@example.com", "password": "nope-nope"})
    assert r.status_code == 401


def test_protected_routes_need_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/predictions/yield", json=BODY).status_code == 401


def test_acres_converted_and_saved(client, auth_headers, monkeypatch):
    """Route logic test. The ML call is replaced with a stub ONLY inside this unit test."""
    captured = {}

    def fake_predict(**kw):
        captured.update(kw)
        return {"state": "Karnataka", "district": "MYSORE", "crop": "Rice", "season": "Kharif",
                "predicted_yield_t_per_ha": 3.0, "estimated_total_production_tonnes": 3.0 * kw["area_ha"],
                "historical_comparison": {}, "model_info": {}}

    monkeypatch.setattr(pred_routes, "predict_yield", fake_predict)
    r = client.post("/api/predictions/yield", json=BODY, headers=auth_headers)
    assert r.status_code == 200
    assert captured["area_ha"] == pytest.approx(4.04686)
    assert len(client.get("/api/predictions/history", headers=auth_headers).json()) == 1


def test_validation_error(client, auth_headers):
    r = client.post("/api/predictions/yield", json={**BODY, "area": -5}, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.skipif(not yield_predictor.MODEL_PATH.exists(), reason="model not trained yet")
def test_real_model_prediction():
    meta_opts = yield_predictor.get_options()
    state = next(iter(meta_opts["districts_by_state"]))
    district = meta_opts["districts_by_state"][state][0]
    out = yield_predictor.predict_yield(state=state, district=district, crop=meta_opts["crops"][0],
                                        season=meta_opts["seasons"][0], year=2012, area_ha=2.0)
    assert out["predicted_yield_t_per_ha"] >= 0
    assert out["estimated_total_production_tonnes"] == pytest.approx(out["predicted_yield_t_per_ha"] * 2.0, abs=0.01)
