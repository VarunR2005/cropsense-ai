from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.irrigation import IrrigationRecommendation
from app.models.user import User
from app.routes.weather import load_weather
from app.schemas.irrigation import IrrigationHistoryOut, IrrigationRequest, IrrigationResponse
from app.services.irrigation import plan_irrigation, supported_crops
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/irrigation", tags=["irrigation"])

ACRE_TO_HECTARE = 0.404686


@router.get("/crops")
def irrigation_crops(_: User = Depends(get_current_user)):
    return {"crops": supported_crops()}


@router.post("/recommend", response_model=IrrigationResponse)
def recommend(
    payload: IrrigationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    area_ha = None
    if payload.area:
        area_ha = payload.area * ACRE_TO_HECTARE if payload.area_unit == "acres" else payload.area

    weather, cached, stale = load_weather(db, payload.city)  # raises 404/502/503 as appropriate
    try:
        result = plan_irrigation(
            weather=weather, crop=payload.crop, growth_stage=payload.growth_stage,
            soil_type=payload.soil_type, soil_moisture=payload.soil_moisture, area_ha=area_ha,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))

    record = IrrigationRecommendation(
        user_id=user.id, city=payload.city.strip(), crop=result["crop"], growth_stage=payload.growth_stage,
        soil_type=payload.soil_type, soil_moisture=payload.soil_moisture, area_ha=area_ha, result=result,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return IrrigationResponse(
        id=record.id,
        weather_source={"provider": "OpenWeatherMap", "location": weather["location"].get("name"),
                        "fetched_at": weather["fetched_at"], "cached": cached, "stale": stale},
        disclaimer=("ESTIMATE based on a simplified FAO-56 water balance and a weather forecast. It is not "
                    "guaranteed agricultural advice: check soil moisture in your field and consult local experts."),
        **result,
    )


@router.get("/history", response_model=list[IrrigationHistoryOut])
def irrigation_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = (select(IrrigationRecommendation).where(IrrigationRecommendation.user_id == user.id)
            .order_by(IrrigationRecommendation.created_at.desc(), IrrigationRecommendation.id.desc()).limit(100))
    return list(db.scalars(stmt))
