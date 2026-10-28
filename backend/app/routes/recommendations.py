from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.ml.crop_recommender import RecommenderNotTrainedError, recommend_crops
from app.models.recommendation import CropRecommendation
from app.models.user import User
from app.schemas.recommendation import (
    CropRecommendationRequest,
    CropRecommendationResponse,
    RecommendationOut,
)
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.post("/crops", response_model=CropRecommendationResponse)
def recommend(
    payload: CropRecommendationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        result = recommend_crops(**payload.model_dump())
    except RecommenderNotTrainedError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))

    record = CropRecommendation(
        user_id=user.id, **payload.model_dump(),
        top_crop=result["recommendations"][0]["crop"], results=result["recommendations"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return CropRecommendationResponse(
        id=record.id,
        recommendations=result["recommendations"],
        warnings=result["warnings"],
        model_info=result["model_info"],
        notes=[
            "suitability_score is the share of the model's decision trees voting for that crop "
            "(0 to 1). It is a confidence-style score, not a guarantee of success.",
            "growing_requirements show the typical range (5th-95th percentile) of each factor for "
            "that crop in the training data, in the same units you entered.",
            "Verify with soil testing and local agricultural experts before planting.",
        ],
    )


@router.get("/history", response_model=list[RecommendationOut])
def recommendation_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = (select(CropRecommendation).where(CropRecommendation.user_id == user.id)
            .order_by(CropRecommendation.created_at.desc(), CropRecommendation.id.desc()).limit(100))
    return list(db.scalars(stmt))
