"""
Train the crop-recommendation classifier.

DATASET (download it yourself - not included):
  Kaggle: "Crop Recommendation Dataset" (file: Crop_recommendation.csv)
  Save it as: backend/datasets/crop_recommendation.csv
  Expected columns: N, P, K, temperature, humidity, ph, rainfall, label
  (about 2,200 rows, 22 crops). Check the Kaggle page for licence and source.

HONEST CAVEATS:
  - This is a small, very clean dataset. Near-perfect accuracy on it does NOT mean
    the model is reliable on real farms. Treat results as a starting suggestion.
  - It has no location column, so location is not used.

Run from backend/:   python -m app.ml.train_crop_recommender
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, precision_recall_fscore_support
from sklearn.model_selection import cross_val_score, train_test_split

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATASET_PATH = BACKEND_DIR / "datasets" / "crop_recommendation.csv"
MODEL_PATH = BACKEND_DIR / "trained_models" / "crop_recommender.joblib"
META_PATH = BACKEND_DIR / "trained_models" / "crop_recommender_metadata.json"

FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
TARGET = "label"


def load_and_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if missing:
        sys.exit(f"Dataset is missing columns: {missing}. Found: {list(df.columns)}")
    df = df[FEATURES + [TARGET]].copy()
    df[TARGET] = df[TARGET].astype(str).str.strip().str.lower()
    for c in FEATURES:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna()
    # Remove exact duplicates BEFORE splitting so copies of a row can't land in both sets.
    df = df.drop_duplicates()
    return df.reset_index(drop=True)


def main():
    if not DATASET_PATH.exists():
        sys.exit(f"Dataset not found at {DATASET_PATH}. See the instructions at the top of this file.")

    df = load_and_clean(DATASET_PATH)
    print(f"Clean rows: {len(df)} | crops: {df[TARGET].nunique()}")

    train, test = train_test_split(df, test_size=0.2, random_state=42, stratify=df[TARGET])
    model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    model.fit(train[FEATURES], train[TARGET])

    pred = model.predict(test[FEATURES])
    p, r, f1, _ = precision_recall_fscore_support(test[TARGET], pred, average="macro", zero_division=0)
    cv = cross_val_score(
        RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
        train[FEATURES], train[TARGET], cv=5,
    )
    metrics = {
        "accuracy": float(accuracy_score(test[TARGET], pred)),
        "precision_macro": float(p),
        "recall_macro": float(r),
        "f1_macro": float(f1),
        "cv_accuracy_mean_on_train": float(cv.mean()),
        "n_train": int(len(train)),
        "n_test": int(len(test)),
    }
    print(json.dumps(metrics, indent=2))
    print(classification_report(test[TARGET], pred, zero_division=0))

    # Typical growing ranges per crop, derived from the training data (5th-95th percentile)
    crop_ranges = {}
    for crop, g in train.groupby(TARGET):
        crop_ranges[crop] = {
            f: {"low": float(g[f].quantile(0.05)), "high": float(g[f].quantile(0.95))}
            for f in FEATURES
        }

    meta = {
        "model_name": "RandomForestClassifier",
        "dataset": "Crop Recommendation Dataset (Crop_recommendation.csv)",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "features": FEATURES,
        "classes": [str(c) for c in model.classes_],
        "metrics": metrics,
        "training_range": {f: {"min": float(df[f].min()), "max": float(df[f].max())} for f in FEATURES},
        "crop_ranges": crop_ranges,
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH, compress=3)
    META_PATH.write_text(json.dumps(meta))
    print(f"Saved model -> {MODEL_PATH}\nSaved metadata -> {META_PATH}")

    row = test.iloc[[0]]
    top = model.predict_proba(row[FEATURES])[0]
    print("\nSample prediction (held-out row):")
    print(row[FEATURES].to_dict("records")[0])
    print(f"Actual: {row[TARGET].iloc[0]} | Predicted: {model.classes_[top.argmax()]} (score {top.max():.2f})")


if __name__ == "__main__":
    main()
