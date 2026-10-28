from typing import Literal

from pydantic import BaseModel, Field


class FertilizerRequest(BaseModel):
    crop: str = Field(min_length=1, max_length=100)
    # Soil-test values in kg/ha, as printed on a Soil Health Card
    nitrogen: float = Field(ge=0, le=5000, description="Available N, kg/ha")
    phosphorus: float = Field(ge=0, le=5000, description="Available P, kg/ha")
    potassium: float = Field(ge=0, le=5000, description="Available K, kg/ha")
    area: float | None = Field(default=None, gt=0, le=1_000_000)
    area_unit: Literal["hectares", "acres"] = "hectares"


class FertilizerResponse(BaseModel):
    id: int
    crop: str
    soil_test_ratings: dict
    standard_dose_kg_per_ha: dict
    nutrient_target_kg_per_ha: dict
    fertilizers: list[dict]
    alternatives: list[dict]
    notes: list[str]
    rules_status: str
    rules_source: str
    disclaimer: str
