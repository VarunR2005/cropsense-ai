# Import every model here so Alembic and create_all can see them.
from app.models.fertilizer import FertilizerRecommendation  # noqa: F401
from app.models.irrigation import IrrigationRecommendation  # noqa: F401
from app.models.prediction import CropPrediction  # noqa: F401
from app.models.recommendation import CropRecommendation  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.weather import WeatherRecord  # noqa: F401
