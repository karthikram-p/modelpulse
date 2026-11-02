import json
import sqlite3
import uuid

from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "storage" / "model_registry.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_registry():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS models (
                model_id TEXT PRIMARY KEY,
                version INTEGER NOT NULL UNIQUE,
                model_name TEXT NOT NULL,
                artifact_path TEXT NOT NULL,
                dataset_path TEXT NOT NULL,
                mae REAL NOT NULL,
                rmse REAL NOT NULL,
                r2 REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


def register_model(
    artifact_path: str,
    dataset_path: str,
    metrics_path: str,
):
    artifact = Path(artifact_path).resolve()
    dataset = Path(dataset_path).resolve()
    metrics_file = Path(metrics_path).resolve()

    for path in [artifact, dataset, metrics_file]:
        if not path.is_file():
            raise FileNotFoundError(
                f"Required file not found: {path}"
            )

    with metrics_file.open("r", encoding="utf-8") as file:
        metrics = json.load(file)

    initialize_registry()

    with get_connection() as connection:
        # Assign the next available version.
        row = connection.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 AS next_version "
            "FROM models"
        ).fetchone()

        version = row["next_version"]

        model_id = str(uuid.uuid4())

        connection.execute("""
            INSERT INTO models (
                model_id,
                version,
                model_name,
                artifact_path,
                dataset_path,
                mae,
                rmse,
                r2,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            model_id,
            version,
            "bike-rental-model",
            str(artifact),
            str(dataset),
            metrics["mae"],
            metrics["rmse"],
            metrics["r2"],
            "CANDIDATE",
            datetime.now(timezone.utc).isoformat(),
        ))

    return {
        "model_id": model_id,
        "version": f"v{version}",
        "status": "CANDIDATE",
        "metrics": metrics,
    }


def list_models():
    initialize_registry()

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT *
            FROM models
            ORDER BY version DESC
        """).fetchall()

    return [dict(row) for row in rows]

def approve_model(model_id: str) -> dict:
    initialize_registry()

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM models WHERE model_id = ?",
            (model_id,),
        ).fetchone()

        if row is None:
            raise LookupError("Model not found.")

        if row["status"] != "CANDIDATE":
            raise ValueError(
                f"Cannot approve a model with status "
                f"'{row['status']}'. Only CANDIDATE models "
                "can be approved."
            )

        connection.execute(
            """
            UPDATE models
            SET status = 'APPROVED'
            WHERE model_id = ?
            """,
            (model_id,),
        )

        updated = connection.execute(
            "SELECT * FROM models WHERE model_id = ?",
            (model_id,),
        ).fetchone()

    return dict(updated)


def promote_model(model_id: str) -> dict:
    initialize_registry()

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM models WHERE model_id = ?",
            (model_id,),
        ).fetchone()

        if row is None:
            raise LookupError("Model not found.")

        if row["status"] != "APPROVED":
            raise ValueError(
                "Only APPROVED models can be promoted."
            )

        # Retire the current production model, if one exists.
        connection.execute(
            """
            UPDATE models
            SET status = 'RETIRED'
            WHERE status = 'PRODUCTION'
            """
        )

        # Promote the approved candidate.
        connection.execute(
            """
            UPDATE models
            SET status = 'PRODUCTION'
            WHERE model_id = ?
            """,
            (model_id,),
        )

        updated = connection.execute(
            "SELECT * FROM models WHERE model_id = ?",
            (model_id,),
        ).fetchone()

    return dict(updated)

def get_production_model():
    initialize_registry()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM models
            WHERE status = 'PRODUCTION'
            ORDER BY version DESC
            LIMIT 1
            """
        ).fetchone()

    return dict(row) if row else None