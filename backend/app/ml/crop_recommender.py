"""Loads the trained recommender and exposes recommend_crops()."""
import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

TRAINED_DIR = Path(__file__).resolve().parents[2] / "trained_models"
MODEL_PATH = TRAINED_DIR / "crop_recommender.joblib"
META_PATH = TRAINED_DIR / "crop_recommender_metadata.json"

LABELS = {"N": "nitrogen", "P": "phosphorus", "K": "potassium", "temperature": "temperature",
          "humidity": "humidity", "ph": "ph", "rainfall": "rainfall"}


class RecommenderNotTrainedError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load():
    if not MODEL_PATH.exists() or not META_PATH.exists():
        raise RecommenderNotTrainedError(
            "Crop recommender not found. Download the dataset to "
            "backend/datasets/crop_recommendation.csv and run: python -m app.ml.train_crop_recommender"
        )
    return joblib.load(MODEL_PATH), json.loads(META_PATH.read_text())


def recommend_crops(*, nitrogen, phosphorus, potassium, temperature, humidity, ph, rainfall, top_k=3) -> dict:
    model, meta = _load()
    values = {"N": nitrogen, "P": phosphorus, "K": potassium, "temperature": temperature,
              "humidity": humidity, "ph": ph, "rainfall": rainfall}
    row = pd.DataFrame([[values[f] for f in meta["features"]]], columns=meta["features"])

    proba = model.predict_proba(row)[0]
    order = np.argsort(proba)[::-1][:top_k]
    recs = []
    for i in order:
        crop = str(model.classes_[i])
        recs.append({
            "crop": crop,
            "suitability_score": round(float(proba[i]), 4),
            "growing_requirements": meta["crop_ranges"][crop],
        })

    warnings = []
    for f, v in values.items():
        lo, hi = meta["training_range"][f]["min"], meta["training_range"][f]["max"]
        if v < lo or v > hi:
            warnings.append(
                f"{LABELS[f]}={v} is outside the range seen in training ({lo:g} to {hi:g}); "
                "results are less reliable."
            )

    return {
        "recommendations": recs,
        "warnings": warnings,
        "model_info": {
            "model": meta["model_name"], "dataset": meta["dataset"],
            "trained_at": meta["trained_at"], "metrics": meta["metrics"],
        },
    }
