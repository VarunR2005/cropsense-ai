"""Dashboard summary: every number is computed from the logged-in user's saved records."""
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ml.yield_predictor import historical_mean
from app.models.fertilizer import FertilizerRecommendation
from app.models.irrigation import IrrigationRecommendation
from app.models.prediction import CropPrediction
from app.models.recommendation import CropRecommendation
from app.models.user import User
from app.models.weather import WeatherRecord


def _count(db: Session, model, user_id: int) -> int:
    return db.scalar(select(func.count()).select_from(model).where(model.user_id == user_id)) or 0


def _weather_summary(db: Session, user_id: int, city: str | None):
    if not city:
        city = db.scalar(select(IrrigationRecommendation.city).where(IrrigationRecommendation.user_id == user_id)
                         .order_by(IrrigationRecommendation.created_at.desc(), IrrigationRecommendation.id.desc()).limit(1))
    if not city:
        return None, "No city yet. Pass ?city=... or request an irrigation plan or weather forecast first."
    rec = db.scalar(select(WeatherRecord).where(WeatherRecord.city_key == city.strip().lower()))
    if not rec:
        return None, f"No saved weather for '{city}'. Call GET /api/weather/forecast?city={city} first."
    p = rec.payload
    today = (p.get("daily_forecast") or [{}])[0]
    alerts = p.get("alerts") or []
    return {
        "city": city, "fetched_at": p.get("fetched_at"),
        "temperature_c": p["current"].get("temperature_c"), "humidity_pct": p["current"].get("humidity_pct"),
        "condition": p["current"].get("condition"), "forecast_today_rain_mm": today.get("rain_mm"),
        "alerts": len(alerts), "first_alert": alerts[0]["message"] if alerts else None,
    }, None


def build_summary(db: Session, user: User, city: str | None = None) -> dict:
    uid = user.id
    preds = list(db.scalars(select(CropPrediction).where(CropPrediction.user_id == uid)
                            .order_by(CropPrediction.created_at.desc(), CropPrediction.id.desc()).limit(1000)))

    def recent_pred(p):
        hm = historical_mean(p.crop, p.state)
        return {"id": p.id, "crop": p.crop, "state": p.state, "district": p.district, "season": p.season,
                "year": p.year, "area_ha": round(p.area_ha, 2),
                "predicted_yield_t_per_ha": p.predicted_yield_t_per_ha,
                "predicted_production_t": p.predicted_production_tonnes,
                "historical_mean_t_per_ha": round(hm, 3) if hm else None,
                "difference_vs_history_pct": round((p.predicted_yield_t_per_ha - hm) / hm * 100, 1) if hm else None,
                "created_at": p.created_at.isoformat()}

    recent = [recent_pred(p) for p in preds[:5]]
    chart_rows = [recent_pred(p) for p in preds[:8]][::-1]

    monthly: dict[str, dict] = defaultdict(lambda: {"predictions": 0, "total_production_t": 0.0})
    seasonal: dict[str, dict] = defaultdict(lambda: {"predictions": 0, "total_production_t": 0.0, "yield_sum": 0.0})
    for p in preds:
        m = monthly[p.created_at.strftime("%Y-%m")]
        m["predictions"] += 1
        m["total_production_t"] += p.predicted_production_tonnes
        s = seasonal[p.season]
        s["predictions"] += 1
        s["total_production_t"] += p.predicted_production_tonnes
        s["yield_sum"] += p.predicted_yield_t_per_ha

    recs = list(db.scalars(select(CropRecommendation).where(CropRecommendation.user_id == uid)
                           .order_by(CropRecommendation.created_at.desc(), CropRecommendation.id.desc()).limit(5)))
    weather, weather_note = _weather_summary(db, uid, city)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "totals": {
            "yield_predictions": _count(db, CropPrediction, uid),
            "crop_recommendations": _count(db, CropRecommendation, uid),
            "fertilizer_recommendations": _count(db, FertilizerRecommendation, uid),
            "irrigation_plans": _count(db, IrrigationRecommendation, uid),
            "disease_detections": None,
        },
        "recent_predictions": recent,
        "recent_crop_recommendations": [
            {"id": r.id, "top_crop": r.top_crop, "top_3": [x["crop"] for x in r.results],
             "created_at": r.created_at.isoformat()} for r in recs],
        "disease_history": {"available": False, "items": [],
                            "note": "Plant disease detection is not built yet, so there is no history to show."},
        "weather_summary": weather, "weather_note": weather_note,
        "yield_comparison_chart": {
            "labels": [f"{r['crop']} / {r['state']} ({r['year']})" for r in chart_rows],
            "predicted_t_per_ha": [r["predicted_yield_t_per_ha"] for r in chart_rows],
            "historical_mean_t_per_ha": [r["historical_mean_t_per_ha"] for r in chart_rows],
        },
        "monthly_trend": [{"month": k, "predictions": v["predictions"],
                           "total_production_t": round(v["total_production_t"], 1)}
                          for k, v in sorted(monthly.items())[-12:]],
        "seasonal_trend": [{"season": k, "predictions": v["predictions"],
                            "total_production_t": round(v["total_production_t"], 1),
                            "avg_predicted_yield_t_per_ha": round(v["yield_sum"] / v["predictions"], 3)}
                           for k, v in sorted(seasonal.items())],
        "farms": {"available": False, "items": [],
                  "note": "Saved farm details are not built yet (planned with the profile page)."},
        "notes": ["Trends use your latest 1000 saved predictions. All figures are model estimates, not guarantees."],
    }
