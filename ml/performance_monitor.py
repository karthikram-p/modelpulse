import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "storage" / "model_registry.db"


def initialize_performance_table():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS model_performance (
                evaluation_id TEXT PRIMARY KEY,
                prediction_id TEXT NOT NULL UNIQUE,
                model_id TEXT NOT NULL,
                actual_value REAL NOT NULL,
                predicted_value REAL NOT NULL,
                absolute_error REAL NOT NULL,
                evaluated_at TEXT NOT NULL,
                FOREIGN KEY (prediction_id)
                    REFERENCES predictions(prediction_id),
                FOREIGN KEY (model_id)
                    REFERENCES models(model_id)
            )
        """)


def record_actual_value(
    prediction_id: str,
    actual_value: float,
) -> dict:
    if actual_value < 0:
        raise ValueError("Actual rental count cannot be negative.")

    initialize_performance_table()

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        prediction = connection.execute(
            """
            SELECT prediction_id, model_id, predicted_value
            FROM predictions
            WHERE prediction_id = ?
            """,
            (prediction_id,),
        ).fetchone()

        if prediction is None:
            raise LookupError("Prediction not found.")

        absolute_error = abs(
            actual_value - prediction["predicted_value"]
        )

        evaluation_id = str(uuid.uuid4())
        evaluated_at = datetime.now(timezone.utc).isoformat()

        connection.execute(
            """
            INSERT INTO model_performance (
                evaluation_id,
                prediction_id,
                model_id,
                actual_value,
                predicted_value,
                absolute_error,
                evaluated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evaluation_id,
                prediction_id,
                prediction["model_id"],
                actual_value,
                prediction["predicted_value"],
                absolute_error,
                evaluated_at,
            ),
        )

    return {
        "evaluation_id": evaluation_id,
        "prediction_id": prediction_id,
        "actual_value": actual_value,
        "predicted_value": prediction["predicted_value"],
        "absolute_error": round(absolute_error, 2),
        "evaluated_at": evaluated_at,
    }


def get_performance_summary(model_id: str) -> dict:
    initialize_performance_table()

    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS evaluation_count,
                AVG(absolute_error) AS mae,
                MAX(absolute_error) AS max_absolute_error
            FROM model_performance
            WHERE model_id = ?
            """,
            (model_id,),
        ).fetchone()

    count, mae, max_error = row

    return {
        "model_id": model_id,
        "evaluation_count": count,
        "mae": round(mae, 2) if mae is not None else None,
        "max_absolute_error": (
            round(max_error, 2) if max_error is not None else None
        ),
        "status": (
            "EVALUATED" if count > 0 else "INSUFFICIENT_DATA"
        ),
    }

def get_model_health(model_id: str) -> dict:
    """
    Summarize model health using observed prediction errors.

    This initial version uses a minimum evaluation count
    and a configurable MAE threshold.
    """
    minimum_evaluations = 30
    mae_threshold = 75.0

    performance = get_performance_summary(model_id)

    evaluation_count = performance["evaluation_count"]
    mae = performance["mae"]

    if evaluation_count < minimum_evaluations:
        status = "INSUFFICIENT_DATA"
        message = (
            f"Need at least {minimum_evaluations} evaluated "
            f"predictions; currently have {evaluation_count}."
        )
    elif mae > mae_threshold:
        status = "DEGRADED"
        message = (
            f"MAE exceeds the configured threshold "
            f"of {mae_threshold}."
        )
    else:
        status = "HEALTHY"
        message = (
            "MAE is within the configured threshold."
        )

    return {
        "model_id": model_id,
        "status": status,
        "evaluation_count": evaluation_count,
        "mae": mae,
        "mae_threshold": mae_threshold,
        "minimum_evaluations": minimum_evaluations,
        "message": message,
    }