from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FertilizerRecommendation(Base):
    __tablename__ = "fertilizer_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    crop: Mapped[str] = mapped_column(String(100))
    nitrogen: Mapped[float] = mapped_column(Float)
    phosphorus: Mapped[float] = mapped_column(Float)
    potassium: Mapped[float] = mapped_column(Float)
    area_ha: Mapped[float | None] = mapped_column(Float, nullable=True)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
