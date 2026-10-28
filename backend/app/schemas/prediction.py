from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class YieldRequest(BaseModel):
    # --- Used by the v1 model ---
    state: str = Field(min_length=1, max_length=100)
    district: str = Field(min_length=1, max_length=100)
    crop: str = Field(min_length=1, max_length=100)
    season: str = Field(min_length=1, max_length=50)
    year: int = Field(default_factory=lambda: date.today().year, ge=1990, le=2100)
    area: float = Field(gt=0, le=1_000_000)
    area_unit: Literal["hectares", "acres"] = "hectares"

    # --- Saved with the prediction, NOT used by the v1 model ---
    soil_type: str | None = Field(default=None, max_length=50)
    soil_ph: float | None = Field(default=None, ge=0, le=14)
    nitrogen: float | None = Field(default=None, ge=0, le=1000)
    phosphorus: float | None = Field(default=None, ge=0, le=1000)
    potassium: float | None = Field(default=None, ge=0, le=1000)
    temperature: float | None = Field(default=None, ge=-10, le=60)
    rainfall: float | None = Field(default=None, ge=0, le=10000)
    humidity: float | None = Field(default=None, ge=0, le=100)


class YieldResponse(BaseModel):
    id: int
    state: str
    district: str
    crop: str
    season: str
    year: int
    area_ha: float
    predicted_yield_t_per_ha: float
    estimated_total_production_tonnes: float
    historical_comparison: dict
    model_info: dict
    notes: list[str]


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    state: str
    district: str
    crop: str
    season: str
    year: int
    area_ha: float
    predicted_yield_t_per_ha: float
    predicted_production_tonnes: float
    created_at: datetime
