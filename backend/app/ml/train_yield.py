"""
Train the crop-yield model.

DATASET (you must download it yourself - it is not included):
  Kaggle: "Crop Production in India" (file: crop_production.csv)
  Save it as: backend/datasets/crop_production.csv
  Expected columns: State_Name, District_Name, Crop_Year, Season, Crop, Area, Production
  Area is in hectares, Production is mostly in tonnes.
  This is district-level government data (approx. 1997-2015). Check the Kaggle page
  for the licence and exact source before using it in a report.

WHAT THE MODEL CAN AND CANNOT DO:
  This dataset has NO soil, NPK, weather or humidity columns, so v1 predicts yield
  from location + crop + season + year + area only.

Run from the backend/ folder:   python -m app.ml.train_yield
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATASET_PATH = BACKEND_DIR / "datasets" / "crop_production.csv"
MODEL_PATH = BACKEND_DIR / "trained_models" / "yield_model.joblib"
META_PATH = BACKEND_DIR / "trained_models" / "yield_metadata.json"

REQUIRED = ["State_Name", "District_Name", "Crop_Year", "Season", "Crop", "Area", "Production"]
CATEGORICAL = ["State_Name", "District_Name", "Crop", "Season"]
NUMERIC = ["Crop_Year", "Area"]
FEATURES = CATEGORICAL + NUMERIC
MAX_PLAUSIBLE_YIELD = 150.0  # t/ha; anything above is treated as a data-entry error


def load_and_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        sys.exit(f"Dataset is missing columns: {missing}. Found: {list(df.columns)}")

    for col in CATEGORICAL:
        df[col] = df[col].astype(str).str.strip()
    for col in ["Crop_Year", "Area", "Production"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Crop_Year", "Area", "Production"])
    df = df[(df["Area"] > 0) & (df["Production"] >= 0)]
    # Coconut production is recorded in nuts, not tonnes, so it is not comparable.
    df = df[df["Crop"].str.lower() != "coconut"]
    df["Crop_Year"] = df["Crop_Year"].astype(int)

    # Target. Production is NOT used as a feature (that would be data leakage).
    df["Yield"] = df["Production"] / df["Area"]
    df = df[df["Yield"] <= MAX_PLAUSIBLE_YIELD]
    return df.reset_index(drop=True)


def time_split(df: pd.DataFrame, n_test_years: int = 3):
    """Train on older years, test on the newest years (simulates real forecasting)."""
    test_years = sorted(df["Crop_Year"].unique())[-n_test_years:]
    test_mask = df["Crop_Year"].isin(test_years)
    return df[~test_mask], df[test_mask], [int(y) for y in test_years]


def build_pipeline() -> Pipeline:
    pre = ColumnTransformer(
        [("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), CATEGORICAL)],
        remainder="passthrough",
    )
    model = RandomForestRegressor(
        n_estimators=100, max_depth=18, min_samples_leaf=5, n_jobs=-1, random_state=42
    )
    return Pipeline([("prep", pre), ("rf", model)])


def main():
    if not DATASET_PATH.exists():
        sys.exit(f"Dataset not found at {DATASET_PATH}. See the instructions at the top of this file.")

    df = load_and_clean(DATASET_PATH)
    train, test, test_years = time_split(df)
    print(f"Clean rows: {len(df)} | train: {len(train)} | test: {len(test)} (years {test_years})")

    pipe = build_pipeline()
    pipe.fit(train[FEATURES], train["Yield"])
    pred = pipe.predict(test[FEATURES])

    # Baseline: average training yield per crop. The model should beat this to be useful.
    crop_mean = train.groupby("Crop")["Yield"].mean()
    baseline = test["Crop"].map(crop_mean).fillna(train["Yield"].mean())

    metrics = {
        "mae_t_per_ha": float(mean_absolute_error(test["Yield"], pred)),
        "rmse_t_per_ha": float(np.sqrt(mean_squared_error(test["Yield"], pred))),
        "r2": float(r2_score(test["Yield"], pred)),
        "baseline_crop_mean_mae_t_per_ha": float(mean_absolute_error(test["Yield"], baseline)),
        "baseline_crop_mean_r2": float(r2_score(test["Yield"], baseline)),
    }
    print(json.dumps(metrics, indent=2))

    # Historical averages for the "compare with history" feature (training years only)
    by_crop_state = train.groupby(["Crop", "State_Name"])["Yield"].agg(["mean", "count"])
    by_crop = train.groupby("Crop")["Yield"].agg(["mean", "count"])
    history = {
        "by_crop_state": {f"{c}|{s}": {"mean": float(r["mean"]), "n": int(r["count"])}
                          for (c, s), r in by_crop_state.iterrows()},
        "by_crop": {c: {"mean": float(r["mean"]), "n": int(r["count"])} for c, r in by_crop.iterrows()},
        "years": [int(train["Crop_Year"].min()), int(train["Crop_Year"].max())],
    }

    districts_by_state = {
        s: sorted(g["District_Name"].unique().tolist()) for s, g in df.groupby("State_Name")
    }
    meta = {
        "model_name": "RandomForestRegressor",
        "dataset": "Crop Production in India (crop_production.csv)",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "test_years": test_years,
        "features_used": FEATURES,
        "metrics": metrics,
        "districts_by_state": districts_by_state,
        "crops": sorted(df["Crop"].unique().tolist()),
        "seasons": sorted(df["Season"].unique().tolist()),
        "history": history,
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, MODEL_PATH, compress=3)
    META_PATH.write_text(json.dumps(meta))
    print(f"Saved model -> {MODEL_PATH}\nSaved metadata -> {META_PATH}")

    # Sample prediction on one held-out row
    row = test.iloc[[0]]
    print("\nSample prediction (held-out row):")
    print(row[FEATURES].to_dict("records")[0])
    print(f"Actual yield: {row['Yield'].iloc[0]:.3f} t/ha | Predicted: {pipe.predict(row[FEATURES])[0]:.3f} t/ha")


if __name__ == "__main__":
    main()
