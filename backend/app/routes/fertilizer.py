from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.ml.fertilizer_recommender import recommend_fertilizer, supported_crops
from app.models.fertilizer import FertilizerRecommendation
from app.models.user import User
from app.schemas.fertilizer import FertilizerRequest, FertilizerResponse
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/recommendations", tags=["fertilizer"])

ACRE_TO_HECTARE = 0.404686


@router.get("/fertilizer/crops")
def fertilizer_crops(_: User = Depends(get_current_user)):
    return {"crops": supported_crops()}


@router.post("/fertilizer", response_model=FertilizerResponse)
def fertilizer(
    payload: FertilizerRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    area_ha = None
    if payload.area:
        area_ha = payload.area * ACRE_TO_HECTARE if payload.area_unit == "acres" else payload.area
    try:
        result = recommend_fertilizer(
            crop=payload.crop, nitrogen=payload.nitrogen, phosphorus=payload.phosphorus,
            potassium=payload.potassium, area_ha=area_ha,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))

    record = FertilizerRecommendation(
        user_id=user.id, crop=result["crop"], nitrogen=payload.nitrogen,
        phosphorus=payload.phosphorus, potassium=payload.potassium, area_ha=area_ha, result=result,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return FertilizerResponse(
        id=record.id,
        disclaimer=("These are ESTIMATES in kg per hectare from simplified rules. Verify with a proper "
                    "soil test and your local agricultural extension officer before applying."),
        **result,
    )
