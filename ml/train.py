import json
from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_squared_error, r2_score


BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = BASE_DIR / "storage" / "processed"
MODEL_DIR = BASE_DIR / "storage" / "models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)


FEATURE_COLUMNS = [
    "season",
    "yr",
    "mnth",
    "hr",
    "holiday",
    "weekday",
    "workingday",
    "weathersit",
    "temp",
    "atemp",
    "hum",
    "windspeed",
]

TARGET_COLUMN = "cnt"


def train_model():
    parquet_files = sorted(
        PROCESSED_DIR.glob("*.parquet"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not parquet_files:
        raise FileNotFoundError(
            "No processed Parquet dataset found."
        )

    df = pd.read_parquet(parquet_files[0])

    # Sort chronologically before splitting.
    df["dteday"] = pd.to_datetime(df["dteday"])

    df = df.sort_values(
        ["dteday", "hr"]
    ).reset_index(drop=True)

    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    # First 80% for training; last 20% for testing.
    split_index = int(len(df) * 0.8)

    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]

    y_train = y.iloc[:split_index]
    y_test = y.iloc[split_index:]

    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    metrics = {
        "training_rows": len(X_train),
        "testing_rows": len(X_test),
        "mae": round(
            float(mean_absolute_error(y_test, predictions)), 2
        ),
        "rmse": round(
            float(mean_squared_error(y_test, predictions) ** 0.5),
            2,
        ),
        "r2": round(
            float(r2_score(y_test, predictions)), 4
        ),
    }

    model_path = MODEL_DIR / "bike_rental_model.joblib"
    metrics_path = MODEL_DIR / "metrics.json"

    joblib.dump(model, model_path)

    with metrics_path.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)

    print("Model training completed.")
    print(json.dumps(metrics, indent=2))
    print(f"\nModel saved to: {model_path}")
    print(f"Metrics saved to: {metrics_path}")


if __name__ == "__main__":
    train_model()