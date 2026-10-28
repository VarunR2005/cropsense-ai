from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.dashboard import build_summary
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(
    city: str | None = Query(None, max_length=100, description="City for the weather card (uses saved weather only)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return build_summary(db, user, city)
