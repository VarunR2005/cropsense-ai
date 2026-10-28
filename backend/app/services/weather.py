"""
Weather service using the OpenWeatherMap FREE endpoints:
  /data/2.5/weather   (current)
  /data/2.5/forecast  (5 days, 3-hour steps; we aggregate into days)
"""
from collections import Counter
from datetime import datetime, timezone

import httpx

BASE_URL = "https://api.openweathermap.org/data/2.5"


class WeatherError(Exception):
    status_code = 500

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class LocationNotFound(WeatherError):
    status_code = 404


class WeatherNotConfigured(WeatherError):
    status_code = 503


class WeatherUnavailable(WeatherError):
    status_code = 502


def _get(client: httpx.Client, path: str, params: dict) -> dict:
    try:
        r = client.get(f"{BASE_URL}{path}", params=params, timeout=10)
    except httpx.HTTPError as e:
        raise WeatherUnavailable("Could not reach the weather service. Try again later.") from e
    if r.status_code == 404:
        raise LocationNotFound(
            f"Location '{params['q']}' was not found. Try 'City' or 'City,IN' (country code)."
        )
    if r.status_code == 401:
        raise WeatherNotConfigured(
            "The weather API key was rejected. Check OPENWEATHER_API_KEY in .env "
            "(newly created keys can take a while to activate)."
        )
    if r.status_code == 429:
        raise WeatherUnavailable("Weather service rate limit reached. Try again in a minute.")
    if r.status_code != 200:
        raise WeatherUnavailable(f"Weather service error (HTTP {r.status_code}).")
    try:
        return r.json()
    except ValueError as e:
        raise WeatherUnavailable("Weather service returned an unreadable response.") from e


def _iso(ts) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def parse_location(raw: dict) -> dict:
    coord = raw.get("coord") or {}
    return {
        "name": raw.get("name"),
        "country": (raw.get("sys") or {}).get("country"),
        "latitude": coord.get("lat"),
        "longitude": coord.get("lon"),
    }


def parse_current(raw: dict) -> dict:
    main = raw.get("main") or {}
    wind = raw.get("wind") or {}
    w = (raw.get("weather") or [{}])[0]
    rain = raw.get("rain") or {}
    return {
        "temperature_c": main.get("temp"),
        "feels_like_c": main.get("feels_like"),
        "humidity_pct": main.get("humidity"),
        "condition": w.get("main"),
        "description": w.get("description"),
        "wind_speed_ms": wind.get("speed"),
        # None means "not reported" (the API omits it when there is no rain)
        "rain_last_1h_mm": rain.get("1h"),
        "observed_at_utc": _iso(raw.get("dt")),
    }


def aggregate_daily(forecast_raw: dict) -> list[dict]:
    """Combine 3-hourly entries into one summary per local calendar day."""
    tz_shift = (forecast_raw.get("city") or {}).get("timezone", 0)
    days: dict[str, dict] = {}
    for e in forecast_raw.get("list") or []:
        if "dt" not in e:
            continue
        day = datetime.fromtimestamp(e["dt"] + tz_shift, tz=timezone.utc).date().isoformat()
        b = days.setdefault(day, {"temps": [], "hum": [], "rain": 0.0, "pop": 0.0,
                                  "wind": 0.0, "conds": Counter(), "n": 0})
        main = e.get("main") or {}
        if main.get("temp") is not None:
            b["temps"].append(main["temp"])
        if main.get("humidity") is not None:
            b["hum"].append(main["humidity"])
        b["rain"] += (e.get("rain") or {}).get("3h", 0.0)
        b["pop"] = max(b["pop"], e.get("pop") or 0.0)
        b["wind"] = max(b["wind"], (e.get("wind") or {}).get("speed") or 0.0)
        w = (e.get("weather") or [{}])[0]
        if w.get("main"):
            b["conds"][w["main"]] += 1
        b["n"] += 1

    out = []
    for day in sorted(days):
        b = days[day]
        out.append({
            "date": day,
            "temp_min_c": round(min(b["temps"]), 1) if b["temps"] else None,
            "temp_max_c": round(max(b["temps"]), 1) if b["temps"] else None,
            "humidity_avg_pct": round(sum(b["hum"]) / len(b["hum"])) if b["hum"] else None,
            "rain_mm": round(b["rain"], 1),
            "rain_probability_pct": round(b["pop"] * 100),
            "wind_max_ms": round(b["wind"], 1),
            "condition": b["conds"].most_common(1)[0][0] if b["conds"] else None,
            "partial_day": b["n"] < 8,
            "slots": b["n"],
        })
    return out


def build_alerts(daily: list[dict]) -> list[dict]:
    """General rules of thumb on the forecast. NOT official warnings."""
    alerts = []
    for d in daily:
        date = d["date"]
        if d["rain_mm"] >= 64.5:
            alerts.append({"type": "heavy_rain", "severity": "high", "date": date,
                           "message": f"About {d['rain_mm']} mm of rain forecast (64.5 mm/day is the "
                                      "start of IMD's 'heavy rain' class). Check drainage; avoid spraying and fertilizing."})
        if d["temp_max_c"] is not None and d["temp_max_c"] >= 40:
            alerts.append({"type": "heat", "severity": "high", "date": date,
                           "message": f"High of {d['temp_max_c']} C: heat stress risk. Irrigate early morning or evening."})
        if d["temp_min_c"] is not None and d["temp_min_c"] <= 4:
            alerts.append({"type": "cold", "severity": "medium", "date": date,
                           "message": f"Low of {d['temp_min_c']} C: possible ground frost for sensitive crops."})
        if d["wind_max_ms"] >= 10.8:
            alerts.append({"type": "wind", "severity": "medium", "date": date,
                           "message": f"Winds up to {d['wind_max_ms']} m/s (strong breeze or more): "
                                      "avoid spraying; tall crops may lodge."})
        if (d["humidity_avg_pct"] is not None and d["temp_min_c"] is not None
                and d["humidity_avg_pct"] >= 85 and 15 <= d["temp_max_c"] <= 30):
            alerts.append({"type": "disease_risk", "severity": "low", "date": date,
                           "message": "Humid, mild weather favours fungal diseases. Scout your fields."})
    return alerts


def irrigation_hints(daily: list[dict]) -> list[str]:
    """Very simple hints from the next 3 forecast days. Crop-specific planning comes later."""
    window = daily[:3]
    if not window:
        return []
    rain = sum(d["rain_mm"] for d in window)
    hot = any(d["temp_max_c"] is not None and d["temp_max_c"] >= 35 for d in window)
    if rain >= 10:
        hint = f"About {rain:.1f} mm of rain is forecast over the next {len(window)} days: consider delaying irrigation."
    elif hot:
        hint = (f"Only {rain:.1f} mm of rain forecast and temperatures reach 35 C or more: "
                "check soil moisture; irrigation is likely needed.")
    else:
        hint = f"Little rain forecast ({rain:.1f} mm over {len(window)} days): irrigate based on soil moisture."
    return [hint + " This is a general hint, not a crop-specific schedule."]


def build_weather(city: str, api_key: str | None, client: httpx.Client | None = None) -> dict:
    if not api_key:
        raise WeatherNotConfigured(
            "Weather is not configured. Set OPENWEATHER_API_KEY in backend/.env and restart the server."
        )
    own = client is None
    client = client or httpx.Client()
    try:
        params = {"q": city, "appid": api_key, "units": "metric"}
        current_raw = _get(client, "/weather", params)
        forecast_raw = _get(client, "/forecast", params)
    finally:
        if own:
            client.close()

    daily = aggregate_daily(forecast_raw)
    return {
        "location": parse_location(current_raw),
        "current": parse_current(current_raw),
        "daily_forecast": daily,
        "alerts": build_alerts(daily),
        "irrigation_hints": irrigation_hints(daily),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
