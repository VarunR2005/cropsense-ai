from pydantic import BaseModel


class WeatherResponse(BaseModel):
    location: dict
    current: dict
    daily_forecast: list[dict]
    alerts: list[dict]
    irrigation_hints: list[str]
    source: dict
    notes: list[str]
