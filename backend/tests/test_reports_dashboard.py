from datetime import datetime, timezone

import pandas as pd
import pytest

from app.database import SessionLocal
from app.models.prediction import CropPrediction
from app.models.irrigation import IrrigationRecommendation
from app.models.recommendation import CropRecommendation
from app.models.weather import WeatherRecord
from app.routes import reports as reports_routes
from app.services import reports as rp

SOURCE = {"name": "Test dataset", "data_as_of": "2019-11-12", "covers_years": [2010, 2013], "cleaning": "n/a"}


def sample_df():
    rows = []
    for year in (2010, 2011, 2012, 2013):
        rows += [
            ["Karnataka", "MYSORE", year, "Kharif", "Rice", 100.0, 300.0 + year - 2010],
            ["Karnataka", "HASSAN", year, "Kharif", "Rice", 200.0, 500.0],
            ["Karnataka", "MYSORE", year, "Rabi", "Wheat", 50.0, 100.0],
            ["Kerala", "IDUKKI", year, "Kharif", "Rice", 80.0, 240.0],
        ]
    return pd.DataFrame(rows, columns=["State_Name", "District_Name", "Crop_Year", "Season", "Crop", "Area", "Production"])


def test_regional_report_numbers_and_filters_case_insensitive():
    r = rp.build_regional_report(sample_df(), SOURCE, state="karnataka", crop="RICE")
    f = sample_df()
    f = f[(f.State_Name == "Karnataka") & (f.Crop == "Rice")]
    assert r["summary"]["records"] == len(f)
    assert r["summary"]["weighted_yield_t_per_ha"] == pytest.approx(f.Production.sum() / f.Area.sum(), abs=0.001)
    by_year = r["tables"][0]
    assert by_year["columns"][0] == "year" and [row[0] for row in by_year["rows"]] == [2010, 2011, 2012, 2013]
    names = [t["name"] for t in r["tables"]]
    assert "Top districts by production" in names and "By season" in names
    assert "Top crops by production" not in names  # crop filtered
    assert r["source"]["name"] == "Test dataset" and r["generated_at"]


def test_no_matching_records():
    with pytest.raises(rp.NoRecordsError):
        rp.build_regional_report(sample_df(), SOURCE, state="Atlantis")


def test_csv_and_pdf_exports():
    r = rp.build_regional_report(sample_df(), SOURCE, crop="Rice")
    csv_text = rp.report_to_csv(r)
    header = csv_text.splitlines()[0]
    assert header.startswith("year,area_ha") and "source" in header and "data_as_of" in header
    assert "Test dataset" in csv_text and "2019-11-12" in csv_text
    pdf = rp.report_to_pdf(r)
    assert pdf[:4] == b"%PDF" and len(pdf) > 2000


def test_regional_route_formats(client, auth_headers, monkeypatch):
    """Route logic only: the dataset loader is replaced inside this unit test."""
    monkeypatch.setattr(reports_routes, "load_dataset", lambda: (sample_df(), SOURCE))
    j = client.get("/api/reports/yield", params={"state": "Karnataka"}, headers=auth_headers)
    assert j.status_code == 200 and j.json()["summary"]["records"] == 12
    c = client.get("/api/reports/yield", params={"crop": "Rice", "format": "csv"}, headers=auth_headers)
    assert c.status_code == 200 and c.headers["content-type"].startswith("text/csv")
    assert "attachment" in c.headers["content-disposition"]
    p = client.get("/api/reports/yield", params={"crop": "Rice", "format": "pdf"}, headers=auth_headers)
    assert p.status_code == 200 and p.content[:4] == b"%PDF"
    assert client.get("/api/reports/yield", params={"state": "Atlantis"}, headers=auth_headers).status_code == 404
    assert client.get("/api/reports/yield", params={"format": "xml"}, headers=auth_headers).status_code == 422


def test_regional_route_dataset_missing_and_login(client, auth_headers, monkeypatch):
    def missing():
        raise rp.ReportDataError("Dataset not found")
    monkeypatch.setattr(reports_routes, "load_dataset", missing)
    assert client.get("/api/reports/yield", headers=auth_headers).status_code == 503
    assert client.get("/api/reports/yield").status_code == 401
    assert client.get("/api/reports/farm").status_code == 401


def _user_id(client, headers):
    return client.get("/api/auth/me", headers=headers).json()["id"]


def _add_predictions(uid):
    with SessionLocal() as db:
        db.add_all([
            CropPrediction(user_id=uid, state="Karnataka", district="MYSORE", crop="Rice", season="Kharif", year=2015,
                           area_ha=2.0, predicted_yield_t_per_ha=3.0, predicted_production_tonnes=6.0),
            CropPrediction(user_id=uid, state="Karnataka", district="HASSAN", crop="Wheat", season="Rabi", year=2015,
                           area_ha=1.0, predicted_yield_t_per_ha=2.0, predicted_production_tonnes=2.0),
        ])
        db.commit()


def test_farm_report_is_scoped_to_user_and_exports(client, auth_headers):
    _add_predictions(_user_id(client, auth_headers))
    # another user's data must never appear
    client.post("/api/auth/register", json={"full_name": "Other", "email": "other@example.com", "password": "password123"})
    tok = client.post("/api/auth/login", data={"username": "other@example.com", "password": "password123"}).json()["access_token"]
    other = {"Authorization": f"Bearer {tok}"}
    assert client.get("/api/reports/farm", headers=other).status_code == 404

    j = client.get("/api/reports/farm", params={"crop": "rice"}, headers=auth_headers)
    assert j.status_code == 200
    body = j.json()
    assert body["summary"]["predictions"] == 1 and body["summary"]["total_predicted_production_t"] == 6.0
    assert body["tables"][0]["rows"][0][3] == "Rice"
    c = client.get("/api/reports/farm", params={"format": "csv"}, headers=auth_headers)
    assert len(c.text.strip().splitlines()) == 3  # header + 2 rows
    p = client.get("/api/reports/farm", params={"format": "pdf"}, headers=auth_headers)
    assert p.content[:4] == b"%PDF"


def test_dashboard_empty_state_is_honest(client, auth_headers):
    d = client.get("/api/dashboard/summary", headers=auth_headers).json()
    assert d["totals"]["yield_predictions"] == 0 and d["recent_predictions"] == []
    assert d["totals"]["disease_detections"] is None and d["disease_history"]["available"] is False
    assert d["weather_summary"] is None and d["weather_note"]
    assert d["farms"]["available"] is False


def test_dashboard_with_data(client, auth_headers):
    uid = _user_id(client, auth_headers)
    _add_predictions(uid)
    with SessionLocal() as db:
        db.add(CropRecommendation(user_id=uid, nitrogen=1, phosphorus=1, potassium=1, temperature=20, humidity=50,
                                  ph=6, rainfall=100, top_crop="rice",
                                  results=[{"crop": "rice"}, {"crop": "jute"}, {"crop": "maize"}]))
        db.add(IrrigationRecommendation(user_id=uid, city="Mysuru,IN", crop="maize", growth_stage="mid",
                                        soil_type="silt", soil_moisture="dry", result={}))
        db.add(WeatherRecord(city_key="mysuru,in", fetched_at=datetime.now(timezone.utc), payload={
            "fetched_at": "2026-10-14T00:00:00+00:00",
            "current": {"temperature_c": 27.0, "humidity_pct": 70, "condition": "Clouds"},
            "daily_forecast": [{"rain_mm": 12.5}], "alerts": [{"message": "Heavy rain"}]}))
        db.commit()
    d = client.get("/api/dashboard/summary", headers=auth_headers).json()
    assert d["totals"]["yield_predictions"] == 2 and d["totals"]["crop_recommendations"] == 1
    assert d["totals"]["irrigation_plans"] == 1 and d["totals"]["fertilizer_recommendations"] == 0
    assert len(d["recent_predictions"]) == 2
    assert d["recent_crop_recommendations"][0]["top_3"] == ["rice", "jute", "maize"]
    assert {s["season"] for s in d["seasonal_trend"]} == {"Kharif", "Rabi"}
    assert d["monthly_trend"][0]["predictions"] == 2 and d["monthly_trend"][0]["total_production_t"] == 8.0
    assert d["weather_summary"]["city"] == "Mysuru,IN" and d["weather_summary"]["alerts"] == 1
    assert d["weather_summary"]["forecast_today_rain_mm"] == 12.5
    assert len(d["yield_comparison_chart"]["labels"]) == 2


def test_dashboard_is_per_user(client, auth_headers):
    _add_predictions(_user_id(client, auth_headers))
    client.post("/api/auth/register", json={"full_name": "Other", "email": "other@example.com", "password": "password123"})
    tok = client.post("/api/auth/login", data={"username": "other@example.com", "password": "password123"}).json()["access_token"]
    d = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {tok}"}).json()
    assert d["totals"]["yield_predictions"] == 0
