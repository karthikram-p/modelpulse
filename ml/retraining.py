import json
import uuid
from pathlib import Path

import pandas as pd
import joblib

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from ml.registry import register_model


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "storage" / "processed"
MODELS_DIR = BASE_DIR / "storage" / "models"

FEATURE_COLUMNS = [
    "season", "yr", "mnth", "hr", "holiday", "weekday",
    "workingday", "weathersit", "temp", "atemp", "hum", "windspeed"
]

TARGET_COLUMN = "cnt"


def retrain_candidate(dataset_path: str | None = None) -> dict:
    """
    Train and register a candidate model.

    The existing production model remains unchanged.
    """

    # 1. Select the dataset explicitly when provided.
    if dataset_path is None:
        parquet_files = sorted(
            PROCESSED_DIR.glob("*.parquet"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        if not parquet_files:
            raise FileNotFoundError(
                "No processed Parquet datasets found."
            )

        dataset = parquet_files[0].resolve()
    else:
        dataset = Path(dataset_path).resolve()

    if not dataset.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {dataset}"
        )

    # 2. Load and validate the training data.
    df = pd.read_parquet(dataset)

    required_columns = FEATURE_COLUMNS + [TARGET_COLUMN]
    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Dataset is missing required columns: {missing}"
        )

    df = df[required_columns].copy()

    for column in required_columns:
        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        )

    if df.isna().any().any():
        raise ValueError(
            "Dataset contains missing or non-numeric values "
            "in required training columns."
        )

    if len(df) < 10:
        raise ValueError(
            "At least 10 rows are required for this prototype."
        )

    # 3. Split chronologically: first 80% for training,
    #    final 20% for evaluation.
    split_index = int(len(df) * 0.8)

    if split_index <= 0 or split_index >= len(df):
        raise ValueError("Unable to create a valid train/test split.")

    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]

    y_train = y.iloc[:split_index]
    y_test = y.iloc[split_index:]

    # 4. Train a candidate model.
    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    # 5. Evaluate on the chronological test set.
    predictions = model.predict(X_test)

    metrics = {
        "mae": float(mean_absolute_error(y_test, predictions)),
        "rmse": float(mean_squared_error(y_test, predictions) ** 0.5),
        "r2": float(r2_score(y_test, predictions)),
        "training_rows": int(len(X_train)),
        "testing_rows": int(len(X_test)),
    }

    # 6. Save unique artifacts so existing models are preserved.
    run_id = uuid.uuid4().hex[:12]
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    artifact_path = MODELS_DIR / f"candidate_{run_id}.joblib"
    metrics_path = MODELS_DIR / f"candidate_{run_id}_metrics.json"

    joblib.dump(model, artifact_path)

    with metrics_path.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)

    # 7. Register as CANDIDATE.
    registration = register_model(
        artifact_path=str(artifact_path),
        dataset_path=str(dataset),
        metrics_path=str(metrics_path),
    )

    return {
        "status": "CANDIDATE_CREATED",
        "registration": registration,
        "metrics": metrics,
        "dataset_path": str(dataset),
        "artifact_path": str(artifact_path),
        "message": (
            "Candidate registered successfully. "
            "The production model has not been changed."
        ),
    }