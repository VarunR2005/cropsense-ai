from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CropPrediction(Base):
    __tablename__ = "crop_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Inputs the model actually uses
    state: Mapped[str] = mapped_column(String(100))
    district: Mapped[str] = mapped_column(String(100))
    crop: Mapped[str] = mapped_column(String(100))
    season: Mapped[str] = mapped_column(String(50))
    year: Mapped[int] = mapped_column(Integer)
    area_ha: Mapped[float] = mapped_column(Float)

    # Optional inputs stored for the farmer's records (not used by the v1 model)
    soil_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    soil_ph: Mapped[float | None] = mapped_column(Float, nullable=True)
    nitrogen: Mapped[float | None] = mapped_column(Float, nullable=True)
    phosphorus: Mapped[float | None] = mapped_column(Float, nullable=True)
    potassium: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Outputs
    predicted_yield_t_per_ha: Mapped[float] = mapped_column(Float)
    predicted_production_tonnes: Mapped[float] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User", back_populates="predictions")
