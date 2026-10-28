import pytest

from app.ml.fertilizer_recommender import recommend_fertilizer

BODY = {"crop": "rice", "nitrogen": 300, "phosphorus": 15, "potassium": 150}


def test_medium_soil_uses_standard_dose():
    r = recommend_fertilizer(crop="rice", nitrogen=300, phosphorus=15, potassium=150)
    assert r["soil_test_ratings"] == {"N": "medium", "P": "medium", "K": "medium"}
    assert r["nutrient_target_kg_per_ha"] == {"N": 100.0, "P2O5": 50.0, "K2O": 50.0}
    by = {f["fertilizer"].split()[0]: f["kg_per_ha"] for f in r["fertilizers"]}
    assert by["DAP"] == pytest.approx(50 / 0.46, abs=0.1)
    assert by["Urea"] == pytest.approx((100 - 50 / 0.46 * 0.18) / 0.46, abs=0.1)
    assert by["MOP"] == pytest.approx(50 / 0.60, abs=0.1)


def test_low_soil_raises_and_high_soil_lowers_dose():
    low = recommend_fertilizer(crop="rice", nitrogen=100, phosphorus=5, potassium=50)
    high = recommend_fertilizer(crop="rice", nitrogen=700, phosphorus=40, potassium=400)
    assert low["nutrient_target_kg_per_ha"]["N"] == 125.0
    assert high["nutrient_target_kg_per_ha"]["N"] == 75.0


def test_area_scaling():
    r = recommend_fertilizer(crop="wheat", nitrogen=300, phosphorus=15, potassium=150, area_ha=2)
    for f in r["fertilizers"]:
        assert f["kg_for_your_area"] == pytest.approx(f["kg_per_ha"] * 2, abs=0.2)


def test_unsupported_crop():
    with pytest.raises(ValueError):
        recommend_fertilizer(crop="dragonfruit", nitrogen=1, phosphorus=1, potassium=1)


def test_route_requires_login(client):
    assert client.post("/api/recommendations/fertilizer", json=BODY).status_code == 401


def test_route_works_and_unit_conversion(client, auth_headers):
    r = client.post("/api/recommendations/fertilizer", json={**BODY, "area": 10, "area_unit": "acres"},
                    headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "ESTIMATES" in body["disclaimer"]
    assert all("reason" in f for f in body["fertilizers"])
    assert body["fertilizers"][0]["kg_for_your_area"] == pytest.approx(
        body["fertilizers"][0]["kg_per_ha"] * 4.04686, abs=0.3)


def test_route_unknown_crop_and_bad_input(client, auth_headers):
    assert client.post("/api/recommendations/fertilizer", json={**BODY, "crop": "xyz"},
                       headers=auth_headers).status_code == 422
    assert client.post("/api/recommendations/fertilizer", json={**BODY, "nitrogen": -1},
                       headers=auth_headers).status_code == 422
