from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.ml.yield_predictor import historical_mean, model_summary
from app.models.prediction import CropPrediction
from app.models.user import User
from app.services.reports import (
    NoRecordsError,
    ReportDataError,
    build_farm_report,
    build_regional_report,
    load_dataset,
    report_to_csv,
    report_to_pdf,
)
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _deliver(report: dict, fmt: str, basename: str):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    if fmt == "csv":
        return Response(report_to_csv(report), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{basename}_{stamp}.csv"'})
    if fmt == "pdf":
        return Response(report_to_pdf(report), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{basename}_{stamp}.pdf"'})
    return report


@router.get("/yield")
def regional_yield_report(
    state: str | None = Query(None, max_length=100),
    district: str | None = Query(None, max_length=100),
    crop: str | None = Query(None, max_length=100),
    season: str | None = Query(None, max_length=50),
    fmt: Literal["json", "csv", "pdf"] = Query("json", alias="format"),
    _: User = Depends(get_current_user),
):
    """Regional report from the historical district-level dataset. Filters are case-insensitive."""
    try:
        df, source = load_dataset()
        report = build_regional_report(df, source, state=state, district=district, crop=crop, season=season)
    except ReportDataError as e:
        raise HTTPException(503, str(e))
    except NoRecordsError as e:
        raise HTTPException(404, str(e))
    return _deliver(report, fmt, "regional_yield_report")


@router.get("/farm")
def farm_yield_report(
    state: str | None = Query(None, max_length=100),
    district: str | None = Query(None, max_length=100),
    crop: str | None = Query(None, max_length=100),
    season: str | None = Query(None, max_length=50),
    fmt: Literal["json", "csv", "pdf"] = Query("json", alias="format"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Farm-level report from the logged-in user's own saved predictions (newest first, max 1000)."""
    stmt = (select(CropPrediction).where(CropPrediction.user_id == user.id)
            .order_by(CropPrediction.created_at.desc(), CropPrediction.id.desc()).limit(1000))
    preds = [{
        "created_at": p.created_at.isoformat(), "state": p.state, "district": p.district, "crop": p.crop,
        "season": p.season, "year": p.year, "area_ha": p.area_ha,
        "predicted_yield_t_per_ha": p.predicted_yield_t_per_ha,
        "predicted_production_tonnes": p.predicted_production_tonnes,
        "historical_mean_t_per_ha": historical_mean(p.crop, p.state),
    } for p in db.scalars(stmt)]
    try:
        report = build_farm_report(preds, model_summary(), state=state, district=district, crop=crop, season=season)
    except NoRecordsError as e:
        raise HTTPException(404, str(e))
    return _deliver(report, fmt, "farm_yield_report")
