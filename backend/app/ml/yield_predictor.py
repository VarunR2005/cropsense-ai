"""Loads the trained yield model and exposes predict_yield()."""
import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

TRAINED_DIR = Path(__file__).resolve().parents[2] / "trained_models"
MODEL_PATH = TRAINED_DIR / "yield_model.joblib"
META_PATH = TRAINED_DIR / "yield_metadata.json"


class ModelNotTrainedError(RuntimeError):
    pass


_NOT_TRAINED = (
    "Yield model not found. Download the dataset to backend/datasets/crop_production.csv "
    "and run: python -m app.ml.train_yield"
)


@lru_cache(maxsize=1)
def _load_meta():
    """Metadata only (fast). Used by dashboards and reports so they never load the big model file."""
    if not META_PATH.exists():
        raise ModelNotTrainedError(_NOT_TRAINED)
    return json.loads(META_PATH.read_text())


@lru_cache(maxsize=1)
def _load():
    if not MODEL_PATH.exists() or not META_PATH.exists():
        raise ModelNotTrainedError(_NOT_TRAINED)
    return joblib.load(MODEL_PATH), _load_meta()


def historical_mean(crop: str, state: str):
    """Mean historical yield (t/ha) for a crop in a state from the training years, or None."""
    try:
        meta = _load_meta()
    except ModelNotTrainedError:
        return None
    entry = meta["history"]["by_crop_state"].get(f"{crop}|{state}")
    return entry["mean"] if entry else None


def model_summary():
    """Short description of the trained model for report footers, or None."""
    try:
        meta = _load_meta()
    except ModelNotTrainedError:
        return None
    return {"model": meta["model_name"], "dataset": meta["dataset"], "trained_at": meta["trained_at"],
            "metrics": meta["metrics"]}


def get_options() -> dict:
    _, meta = _load()
    return {
        "districts_by_state": meta["districts_by_state"],
        "crops": meta["crops"],
        "seasons": meta["seasons"],
        "dataset": meta["dataset"],
        "metrics": meta["metrics"],
        "test_years": meta["test_years"],
    }


def _canon(value: str, options, label: str) -> str:
    lookup = {o.lower(): o for o in options}
    found = lookup.get(value.strip().lower())
    if found is None:
        raise ValueError(f"Unknown {label} '{value}'. See GET /api/predictions/options for valid values.")
    return found


def predict_yield(*, state: str, district: str, crop: str, season: str, year: int, area_ha: float) -> dict:
    model, meta = _load()
    state_c = _canon(state, meta["districts_by_state"].keys(), "state")
    district_c = _canon(district, meta["districts_by_state"][state_c], f"district for {state_c}")
    crop_c = _canon(crop, meta["crops"], "crop")
    season_c = _canon(season, meta["seasons"], "season")

    row = pd.DataFrame([{
        "State_Name": state_c, "District_Name": district_c, "Crop": crop_c,
        "Season": season_c, "Crop_Year": year, "Area": area_ha,
    }])[meta["features_used"]]
    yield_t_ha = max(float(model.predict(row)[0]), 0.0)

    hist = meta["history"]
    cs = hist["by_crop_state"].get(f"{crop_c}|{state_c}")
    national = hist["by_crop"].get(crop_c)
    comparison = {
        "historical_years": hist["years"],
        "crop_state_mean_t_per_ha": cs["mean"] if cs else None,
        "crop_state_records": cs["n"] if cs else 0,
        "crop_national_mean_t_per_ha": national["mean"] if national else None,
        "difference_vs_state_mean_pct": (
            round((yield_t_ha - cs["mean"]) / cs["mean"] * 100, 1) if cs and cs["mean"] > 0 else None
        ),
    }
    return {
        "state": state_c, "district": district_c, "crop": crop_c, "season": season_c,
        "predicted_yield_t_per_ha": round(yield_t_ha, 3),
        "estimated_total_production_tonnes": round(yield_t_ha * area_ha, 3),
        "historical_comparison": comparison,
        "model_info": {
            "model": meta["model_name"], "dataset": meta["dataset"],
            "trained_at": meta["trained_at"], "features_used": meta["features_used"],
            "test_years": meta["test_years"], "metrics": meta["metrics"],
        },
    }
