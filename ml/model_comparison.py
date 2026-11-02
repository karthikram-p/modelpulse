import sqlite3
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "storage" / "model_registry.db"

FEATURE_COLUMNS = [
    "season", "yr", "mnth", "hr", "holiday", "weekday",
    "workingday", "weathersit", "temp", "atemp", "hum", "windspeed"
]

TARGET_COLUMN = "cnt"


def get_model(model_id: str):
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        row = connection.execute(
            "SELECT * FROM models WHERE model_id = ?",
            (model_id,),
        ).fetchone()

    return dict(row) if row else None


def evaluate_model(model, X_test, y_test):
    predictions = model.predict(X_test)

    return {
        "mae": float(mean_absolute_error(y_test, predictions)),
        "rmse": float(mean_squared_error(y_test, predictions) ** 0.5),
        "r2": float(r2_score(y_test, predictions)),
    }


def compare_models(candidate_model_id: str) -> dict:
    # 1. Retrieve the current production model.
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        production_row = connection.execute(
            """
            SELECT *
            FROM models
            WHERE status = 'PRODUCTION'
            ORDER BY version DESC
            LIMIT 1
            """
        ).fetchone()

    if production_row is None:
        raise LookupError("No production model is registered.")

    production = dict(production_row)

    # 2. Retrieve the candidate.
    candidate = get_model(candidate_model_id)

    if candidate is None:
        raise LookupError("Candidate model not found.")

    if candidate["status"] != "CANDIDATE":
        raise ValueError(
            "Only models with CANDIDATE status can be compared."
        )

    # 3. Load the shared dataset.
    # Both models must be evaluated on the same rows.
    if Path(production["dataset_path"]).resolve() != Path(
        candidate["dataset_path"]
    ).resolve():
        raise ValueError(
            "Models reference different datasets. "
            "Use an explicitly selected common evaluation dataset."
        )

    dataset_path = Path(production["dataset_path"])

    if not dataset_path.is_file():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {dataset_path}"
        )

    df = pd.read_parquet(dataset_path)

    required_columns = FEATURE_COLUMNS + [TARGET_COLUMN]
    missing = [c for c in required_columns if c not in df.columns]

    if missing:
        raise ValueError(f"Dataset is missing columns: {missing}")

    df = df[required_columns].copy()

    for column in required_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    if df.isna().any().any():
        raise ValueError(
            "Evaluation data contains missing or non-numeric values."
        )

    if len(df) < 10:
        raise ValueError("Not enough rows for model comparison.")

    # 4. Use the same chronological holdout for both models.
    split_index = int(len(df) * 0.8)

    X_test = df[FEATURE_COLUMNS].iloc[split_index:]
    y_test = df[TARGET_COLUMN].iloc[split_index:]

    # 5. Load both saved artifacts.
    production_model = joblib.load(production["artifact_path"])
    candidate_model = joblib.load(candidate["artifact_path"])

    production_metrics = evaluate_model(
        production_model, X_test, y_test
    )
    candidate_metrics = evaluate_model(
        candidate_model, X_test, y_test
    )

    # 6. Calculate changes relative to production.
    mae_change = (
        candidate_metrics["mae"] - production_metrics["mae"]
    )
    rmse_change = (
        candidate_metrics["rmse"] - production_metrics["rmse"]
    )
    r2_change = (
        candidate_metrics["r2"] - production_metrics["r2"]
    )

    mae_improvement_pct = (
        (production_metrics["mae"] - candidate_metrics["mae"])
        / production_metrics["mae"] * 100
        if production_metrics["mae"] != 0
        else 0.0
    )

    # 7. Apply explicit, configurable acceptance criteria.
    # Require at least 1% MAE improvement, no more than 2%
    # RMSE degradation, and no more than 0.01 R² reduction.
    mae_pass = (
        candidate_metrics["mae"]
        <= production_metrics["mae"] * 0.99
    )
    rmse_pass = (
        candidate_metrics["rmse"]
        <= production_metrics["rmse"] * 1.02
    )
    r2_pass = (
        candidate_metrics["r2"]
        >= production_metrics["r2"] - 0.01
    )

    eligible = mae_pass and rmse_pass and r2_pass

    return {
        "production_model": {
            "model_id": production["model_id"],
            "version": production["version"],
            "metrics": production_metrics,
        },
        "candidate_model": {
            "model_id": candidate["model_id"],
            "version": candidate["version"],
            "metrics": candidate_metrics,
        },
        "comparison": {
            "test_rows": int(len(X_test)),
            "mae_change": mae_change,
            "mae_improvement_percent": mae_improvement_pct,
            "rmse_change": rmse_change,
            "r2_change": r2_change,
        },
        "acceptance_checks": {
            "mae_improved_by_at_least_1_percent": mae_pass,
            "rmse_degradation_within_2_percent": rmse_pass,
            "r2_drop_within_0_01": r2_pass,
        },
        "recommendation": (
            "CANDIDATE_ELIGIBLE_FOR_APPROVAL"
            if eligible
            else "KEEP_PRODUCTION"
        ),
        "production_changed": False,
        "note": (
            "This comparison uses the shared chronological holdout. "
            "Eligibility is a recommendation, not automatic approval."
        ),
    }