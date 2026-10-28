from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CropRecommendationRequest(BaseModel):
    nitrogen: float = Field(ge=0, le=500, description="N in kg/ha (soil test value)")
    phosphorus: float = Field(ge=0, le=500, description="P in kg/ha")
    potassium: float = Field(ge=0, le=500, description="K in kg/ha")
    temperature: float = Field(ge=-10, le=60, description="Average temperature, degrees C")
    humidity: float = Field(ge=0, le=100, description="Relative humidity, %")
    ph: float = Field(ge=0, le=14, description="Soil pH")
    rainfall: float = Field(ge=0, le=10000, description="Rainfall in mm")


class CropRecommendationResponse(BaseModel):
    id: int
    recommendations: list[dict]
    warnings: list[str]
    model_info: dict
    notes: list[str]


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    top_crop: str
    results: list
    created_at: datetime
