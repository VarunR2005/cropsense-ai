from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WeatherRecord(Base):
    """Cached weather per city, so we do not call the API on every request."""
    __tablename__ = "weather_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
