from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IrrigationRecommendation(Base):
    __tablename__ = "irrigation_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    city: Mapped[str] = mapped_column(String(100))
    crop: Mapped[str] = mapped_column(String(100))
    growth_stage: Mapped[str] = mapped_column(String(20))
    soil_type: Mapped[str] = mapped_column(String(30))
    soil_moisture: Mapped[str] = mapped_column(String(20))
    area_ha: Mapped[float | None] = mapped_column(Float, nullable=True)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
