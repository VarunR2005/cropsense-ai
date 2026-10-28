from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.ml.yield_predictor import ModelNotTrainedError, get_options, predict_yield
from app.models.prediction import CropPrediction
from app.models.user import User
from app.schemas.prediction import PredictionOut, YieldRequest, YieldResponse
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

ACRE_TO_HECTARE = 0.404686


@router.get("/options")
def prediction_options(_: User = Depends(get_current_user)):
    """Valid states/districts/crops/seasons (for form dropdowns) plus model metrics."""
    try:
        return get_options()
    except ModelNotTrainedError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))


@router.post("/yield", response_model=YieldResponse)
def create_yield_prediction(
    payload: YieldRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    area_ha = payload.area * ACRE_TO_HECTARE if payload.area_unit == "acres" else payload.area
    try:
        result = predict_yield(
            state=payload.state, district=payload.district, crop=payload.crop,
            season=payload.season, year=payload.year, area_ha=area_ha,
        )
    except ModelNotTrainedError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))

    record = CropPrediction(
        user_id=user.id, state=result["state"], district=result["district"],
        crop=result["crop"], season=result["season"], year=payload.year, area_ha=area_ha,
        soil_type=payload.soil_type, soil_ph=payload.soil_ph, nitrogen=payload.nitrogen,
        phosphorus=payload.phosphorus, potassium=payload.potassium,
        temperature=payload.temperature, rainfall=payload.rainfall, humidity=payload.humidity,
        predicted_yield_t_per_ha=result["predicted_yield_t_per_ha"],
        predicted_production_tonnes=result["estimated_total_production_tonnes"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    notes = [
        "This is a statistical estimate, not guaranteed. Verify with soil testing and local agricultural experts.",
        "Units: yield in tonnes per hectare (t/ha); production in tonnes.",
    ]
    ignored = [f for f in ("soil_type", "soil_ph", "nitrogen", "phosphorus", "potassium",
                           "temperature", "rainfall", "humidity") if getattr(payload, f) is not None]
    if ignored:
        notes.append(
            "Saved but NOT used by this model version (the training dataset has no such columns): "
            + ", ".join(ignored)
        )

    return YieldResponse(
        id=record.id, year=payload.year, area_ha=round(area_ha, 4), notes=notes,
        state=result["state"], district=result["district"], crop=result["crop"],
        season=result["season"],
        predicted_yield_t_per_ha=result["predicted_yield_t_per_ha"],
        estimated_total_production_tonnes=result["estimated_total_production_tonnes"],
        historical_comparison=result["historical_comparison"], model_info=result["model_info"],
    )


@router.get("/history", response_model=list[PredictionOut])
def prediction_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Only the logged-in user's predictions, newest first."""
    stmt = (select(CropPrediction).where(CropPrediction.user_id == user.id)
            .order_by(CropPrediction.created_at.desc(), CropPrediction.id.desc()).limit(100))
    return list(db.scalars(stmt))
