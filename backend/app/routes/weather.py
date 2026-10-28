from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.weather import WeatherRecord
from app.schemas.weather import WeatherResponse
from app.services.weather import WeatherError, build_weather
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/weather", tags=["weather"])

NOTES = [
    "Source: OpenWeatherMap free API (current weather + 5-day forecast in 3-hour steps, combined into days).",
    "The first and last days can be partial (see partial_day). Rain fields the API omits are treated as 0 mm.",
    "Alerts are general rules of thumb, not official warnings. Follow India Meteorological Department (IMD) advisories.",
]


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def load_weather(db: Session, city: str) -> tuple[dict, bool, bool]:
    """Return (payload, cached, stale). Uses the DB cache; raises HTTPException on failure.
    Shared by the weather and irrigation routes."""
    key = city.strip().lower()
    record = db.scalar(select(WeatherRecord).where(WeatherRecord.city_key == key))
    ttl = timedelta(minutes=settings.weather_cache_minutes)
    now = datetime.now(timezone.utc)

    if record and now - _aware(record.fetched_at) < ttl:
        return record.payload, True, False

    try:
        payload = build_weather(city.strip(), settings.openweather_api_key)
    except WeatherError as e:
        # If the service is down but we have older data, serve it clearly marked as stale.
        if record and e.status_code == 502:
            return record.payload, True, True
        raise HTTPException(e.status_code, e.message)

    if record:
        record.payload, record.fetched_at = payload, now
    else:
        db.add(WeatherRecord(city_key=key, payload=payload, fetched_at=now))
    db.commit()
    return payload, False, False


def _response(payload: dict, *, cached: bool, stale: bool = False) -> WeatherResponse:
    notes = list(NOTES)
    if stale:
        notes.insert(0, "The weather service is unavailable, so this is the last saved result (see fetched_at).")
    return WeatherResponse(
        location=payload["location"], current=payload["current"],
        daily_forecast=payload["daily_forecast"], alerts=payload["alerts"],
        irrigation_hints=payload["irrigation_hints"],
        source={"provider": "OpenWeatherMap", "fetched_at": payload["fetched_at"],
                "cached": cached, "stale": stale},
        notes=notes,
    )


@router.get("/forecast", response_model=WeatherResponse)
def forecast(
    city: str = Query(min_length=2, max_length=100, description="City or district, e.g. 'Mysuru' or 'Mysuru,IN'"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    payload, cached, stale = load_weather(db, city)
    return _response(payload, cached=cached, stale=stale)
