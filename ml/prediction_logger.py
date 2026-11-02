import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "storage" / "model_registry.db"


def initialize_prediction_table():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                prediction_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                model_version INTEGER NOT NULL,
                input_features TEXT NOT NULL,
                predicted_value REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (model_id) REFERENCES models(model_id)
            )
        """)


def log_prediction(
    model_id: str,
    model_version: int,
    input_features: dict,
    predicted_value: float,
) -> dict:
    initialize_prediction_table()

    prediction_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO predictions (
                prediction_id,
                model_id,
                model_version,
                input_features,
                predicted_value,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                prediction_id,
                model_id,
                model_version,
                json.dumps(input_features),
                predicted_value,
                created_at,
            ),
        )

    return {
        "prediction_id": prediction_id,
        "created_at": created_at,
    }


def list_predictions(limit: int = 100) -> list[dict]:
    initialize_prediction_table()

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT *
            FROM predictions
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    results = []

    for row in rows:
        item = dict(row)
        item["input_features"] = json.loads(item["input_features"])
        results.append(item)

    return results