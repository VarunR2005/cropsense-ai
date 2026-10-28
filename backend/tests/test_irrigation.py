import pytest

from app.routes import irrigation as irr_routes
from app.services import irrigation as irr

BODY = {"city": "Mysuru,IN", "crop": "maize", "growth_stage": "mid", "soil_type": "silt", "soil_moisture": "dry"}


def make_weather(rain=0.0, tmin=20.0, tmax=32.0, days=5, lat=12.3):
    return {
        "location": {"name": "Mysore", "latitude": lat, "longitude": 76.6},
        "daily_forecast": [{"date": f"2026-10-{15 + i}", "temp_min_c": tmin, "temp_max_c": tmax,
                            "rain_mm": rain, "slots": 8} for i in range(days)],
        "fetched_at": "2026-10-14T00:00:00+00:00",
    }


def test_formulas_match_fao_examples():
    # FAO-56 Example 36: maize on loamy sand: TAW 108 mm, RAW 59 mm (Zr 1.2 m, p 0.55, 90 mm/m)
    taw, raw = irr.taw_raw(90, 1.2, 0.55)
    assert taw == pytest.approx(108) and raw == pytest.approx(59.4, abs=0.1)
    # Silt, tomato example numbers: 170 mm/m x 0.8 m = 136
    assert irr.taw_raw(170, 0.8, 0.40)[0] == pytest.approx(136)


def test_radiation_and_et0_are_plausible():
    ra = irr.extraterrestrial_radiation_mm(12.3, 289)  # mid-October, ~12 N
    assert 12 < ra < 17
    et0 = irr.hargreaves_et0(20, 32, ra)
    assert 3 < et0 < 8


def test_dry_start_no_rain_irrigates_immediately():
    out = irr.plan_irrigation(weather=make_weather(), crop="maize", growth_stage="mid",
                              soil_type="silt", soil_moisture="dry", area_ha=2)
    assert out["irrigation_events"], "dry soil and no rain should trigger irrigation"
    first = out["irrigation_events"][0]
    assert first["date"] == "2026-10-15"
    assert first["m3_per_ha"] == pytest.approx(first["net_mm"] * 10)
    assert first["m3_for_your_area"] == pytest.approx(first["m3_per_ha"] * 2, abs=0.2)


def test_wet_soil_and_heavy_rain_needs_no_irrigation():
    out = irr.plan_irrigation(weather=make_weather(rain=30.0), crop="maize", growth_stage="mid",
                              soil_type="silt", soil_moisture="wet")
    assert out["irrigation_events"] == []
    assert out["totals"]["effective_rain_mm"] > 0
    assert "No irrigation" in out["summary"]


def test_light_soil_needs_more_frequent_smaller_irrigations_than_heavy_soil():
    w = make_weather(days=5)
    sandy = irr.plan_irrigation(weather=w, crop="wheat", growth_stage="mid", soil_type="loamy_sand", soil_moisture="dry")
    clay = irr.plan_irrigation(weather=w, crop="wheat", growth_stage="mid", soil_type="silt", soil_moisture="dry")
    assert len(sandy["irrigation_events"]) >= len(clay["irrigation_events"])
    assert sandy["irrigation_events"][0]["net_mm"] < clay["irrigation_events"][0]["net_mm"]


def test_paddy_rice_has_no_depletion_schedule():
    out = irr.plan_irrigation(weather=make_weather(), crop="rice", growth_stage="mid",
                              soil_type="silty_clay", soil_moisture="moderate")
    assert out["irrigation_events"] == []
    assert all("net_requirement_mm" in r for r in out["daily"])
    assert "percolation" in out["summary"].lower()


def test_partial_day_scales_et():
    w = make_weather(days=1)
    full = irr.plan_irrigation(weather=w, crop="maize", growth_stage="mid", soil_type="silt")["daily"][0]["etc_mm"]
    w["daily_forecast"][0]["slots"] = 4
    half = irr.plan_irrigation(weather=w, crop="maize", growth_stage="mid", soil_type="silt")["daily"][0]["etc_mm"]
    assert half == pytest.approx(full / 2, abs=0.02)


def test_validation_errors():
    with pytest.raises(ValueError):
        irr.plan_irrigation(weather=make_weather(), crop="dragonfruit", growth_stage="mid", soil_type="silt")
    with pytest.raises(ValueError):
        irr.plan_irrigation(weather=make_weather(lat=None), crop="maize", growth_stage="mid", soil_type="silt")


def test_route_requires_login(client):
    assert client.post("/api/irrigation/recommend", json=BODY).status_code == 401


def test_route_without_weather_key_gives_503(client, auth_headers):
    assert client.post("/api/irrigation/recommend", json=BODY, headers=auth_headers).status_code == 503


def test_route_works_with_stubbed_weather(client, auth_headers, monkeypatch):
    """Route logic only: the weather loader is stubbed inside this unit test."""
    monkeypatch.setattr(irr_routes, "load_weather", lambda db, city: (make_weather(), False, False))
    r = client.post("/api/irrigation/recommend", json={**BODY, "area": 2, "area_unit": "acres"}, headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "ESTIMATE" in body["disclaimer"] and body["assumptions"]["kc"] > 0
    assert body["weather_source"]["location"] == "Mysore"
    assert len(client.get("/api/irrigation/history", headers=auth_headers).json()) == 1


def test_route_bad_input(client, auth_headers, monkeypatch):
    monkeypatch.setattr(irr_routes, "load_weather", lambda db, city: (make_weather(), False, False))
    assert client.post("/api/irrigation/recommend", json={**BODY, "crop": "xyz"}, headers=auth_headers).status_code == 422
    assert client.post("/api/irrigation/recommend", json={**BODY, "soil_type": "rock"}, headers=auth_headers).status_code == 422
