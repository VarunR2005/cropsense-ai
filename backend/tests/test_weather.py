from datetime import datetime, timezone

import httpx
import pytest

from app.routes import weather as weather_routes
from app.services import weather as ws

BASE = int(datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc).timestamp())


def slot(i, temp=25, hum=70, rain=None, pop=0.1, wind=3.0):
    e = {"dt": BASE + i * 3 * 3600, "main": {"temp": temp, "humidity": hum},
         "pop": pop, "wind": {"speed": wind}, "weather": [{"main": "Clouds"}]}
    if rain is not None:
        e["rain"] = {"3h": rain}
    return e


def fake_client(current_status=200, forecast_status=200, forecast=None, raise_error=False):
    current = {"name": "Mysore", "sys": {"country": "IN"}, "coord": {"lat": 12.3, "lon": 76.6},
               "main": {"temp": 28.0, "feels_like": 29.0, "humidity": 60},
               "weather": [{"main": "Clear", "description": "clear sky"}], "wind": {"speed": 2.0}, "dt": BASE}
    forecast = forecast if forecast is not None else {"city": {"timezone": 0}, "list": [slot(i) for i in range(8)]}

    def handler(request: httpx.Request):
        if raise_error:
            raise httpx.ConnectTimeout("boom")
        if request.url.path.endswith("/weather"):
            return httpx.Response(current_status, json=current)
        return httpx.Response(forecast_status, json=forecast)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_daily_aggregation_and_missing_rain():
    out = ws.build_weather("Mysore", "key", client=fake_client())
    day = out["daily_forecast"][0]
    assert day["rain_mm"] == 0.0 and day["partial_day"] is False
    assert out["current"]["rain_last_1h_mm"] is None  # not reported, not faked as 0
    assert out["location"]["name"] == "Mysore"


def test_heavy_rain_alert_and_irrigation_hint():
    fc = {"city": {"timezone": 0}, "list": [slot(i, rain=10.0) for i in range(8)]}  # 80 mm in a day
    out = ws.build_weather("Mysore", "key", client=fake_client(forecast=fc))
    assert out["daily_forecast"][0]["rain_mm"] == 80.0
    assert any(a["type"] == "heavy_rain" for a in out["alerts"])
    assert "delaying irrigation" in out["irrigation_hints"][0]


def test_heat_and_dry_hint():
    fc = {"city": {"timezone": 0}, "list": [slot(i, temp=41) for i in range(8)]}
    out = ws.build_weather("X", "key", client=fake_client(forecast=fc))
    assert any(a["type"] == "heat" for a in out["alerts"])
    assert "irrigation is likely needed" in out["irrigation_hints"][0]


def test_errors_are_mapped():
    with pytest.raises(ws.LocationNotFound):
        ws.build_weather("Nowhere", "key", client=fake_client(current_status=404))
    with pytest.raises(ws.WeatherNotConfigured):
        ws.build_weather("X", "key", client=fake_client(current_status=401))
    with pytest.raises(ws.WeatherUnavailable):
        ws.build_weather("X", "key", client=fake_client(current_status=500))
    with pytest.raises(ws.WeatherUnavailable):
        ws.build_weather("X", "key", client=fake_client(raise_error=True))
    with pytest.raises(ws.WeatherNotConfigured):
        ws.build_weather("X", "")


def test_route_requires_login(client):
    assert client.get("/api/weather/forecast", params={"city": "Mysuru"}).status_code == 401


def test_route_without_api_key_gives_503(client, auth_headers):
    r = client.get("/api/weather/forecast", params={"city": "Mysuru"}, headers=auth_headers)
    assert r.status_code == 503
    assert "OPENWEATHER_API_KEY" in r.json()["detail"]


def test_route_caches_and_serves_stale(client, auth_headers, monkeypatch):
    """Route logic only: the service call is stubbed inside this unit test."""
    calls = []

    def fake_build(city, api_key, client=None):
        calls.append(city)
        return ws.build_weather(city, "key", client=fake_client())

    monkeypatch.setattr(weather_routes, "build_weather", fake_build)
    a = client.get("/api/weather/forecast", params={"city": "Mysuru"}, headers=auth_headers)
    b = client.get("/api/weather/forecast", params={"city": "mysuru "}, headers=auth_headers)
    assert a.status_code == b.status_code == 200
    assert a.json()["source"]["cached"] is False and b.json()["source"]["cached"] is True
    assert len(calls) == 1

    # cache expires -> API down -> stale copy served and labelled
    monkeypatch.setattr(weather_routes.settings, "weather_cache_minutes", 0)

    def down(city, api_key, client=None):
        raise ws.WeatherUnavailable("down")

    monkeypatch.setattr(weather_routes, "build_weather", down)
    c = client.get("/api/weather/forecast", params={"city": "Mysuru"}, headers=auth_headers)
    assert c.status_code == 200 and c.json()["source"]["stale"] is True


def test_route_unknown_city_404(client, auth_headers, monkeypatch):
    def nf(city, api_key, client=None):
        raise ws.LocationNotFound("nope")

    monkeypatch.setattr(weather_routes, "build_weather", nf)
    r = client.get("/api/weather/forecast", params={"city": "Zzzz"}, headers=auth_headers)
    assert r.status_code == 404
