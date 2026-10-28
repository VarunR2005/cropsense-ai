from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IrrigationRequest(BaseModel):
    city: str = Field(min_length=2, max_length=100, description="City/district for the weather, e.g. 'Mysuru,IN'")
    crop: str = Field(min_length=1, max_length=100)
    growth_stage: Literal["initial", "development", "mid", "late"]
    soil_type: Literal["loamy_sand", "silt", "silty_clay"]
    soil_moisture: Literal["dry", "moderate", "wet"] = "moderate"
    area: float | None = Field(default=None, gt=0, le=1_000_000)
    area_unit: Literal["hectares", "acres"] = "hectares"


class IrrigationResponse(BaseModel):
    id: int
    crop: str
    growth_stage: str
    soil_type: str
    soil_moisture_start: str
    summary: str
    irrigation_events: list[dict]
    daily: list[dict]
    totals: dict
    assumptions: dict
    notes: list[str]
    weather_source: dict
    disclaimer: str


class IrrigationHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city: str
    crop: str
    growth_stage: str
    created_at: datetime
