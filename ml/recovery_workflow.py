import json
import sqlite3
import uuid

from datetime import datetime, timezone
from pathlib import Path

from ml.registry import (
    get_production_model,
    list_models,
    approve_model,
    promote_model,
)
from ml.recovery import evaluate_recovery_need
from ml.retraining import retrain_candidate
from ml.model_comparison import compare_models


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "storage" / "model_registry.db"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def connect_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def initialize_recovery_jobs():
    with connect_db() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS recovery_jobs (
                job_id TEXT PRIMARY KEY,
                production_model_id TEXT NOT NULL,
                candidate_model_id TEXT,
                status TEXT NOT NULL,
                reason TEXT,
                comparison_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


def create_job(model_id: str, status: str, reason: str) -> str:
    job_id = str(uuid.uuid4())
    timestamp = now_utc()

    with connect_db() as connection:
        connection.execute(
            """
            INSERT INTO recovery_jobs (
                job_id,
                production_model_id,
                status,
                reason,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                model_id,
                status,
                reason,
                timestamp,
                timestamp,
            ),
        )

    return job_id


def update_job(
    job_id: str,
    status: str,
    reason: str | None = None,
    candidate_model_id: str | None = None,
    comparison: dict | None = None,
):
    with connect_db() as connection:
        connection.row_factory = sqlite3.Row

        existing = connection.execute(
            "SELECT * FROM recovery_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()

        if existing is None:
            raise LookupError("Recovery job not found.")

        # Preserve values when an update doesn't supply replacements.
        candidate_id = (
            candidate_model_id
            if candidate_model_id is not None
            else existing["candidate_model_id"]
        )

        comparison_json = (
            json.dumps(comparison)
            if comparison is not None
            else existing["comparison_json"]
        )

        connection.execute(
            """
            UPDATE recovery_jobs
            SET candidate_model_id = ?,
                status = ?,
                reason = ?,
                comparison_json = ?,
                updated_at = ?
            WHERE job_id = ?
            """,
            (
                candidate_id,
                status,
                reason,
                comparison_json,
                now_utc(),
                job_id,
            ),
        )


def get_job(job_id: str) -> dict | None:
    with connect_db() as connection:
        connection.row_factory = sqlite3.Row

        row = connection.execute(
            "SELECT * FROM recovery_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()

    if row is None:
        return None

    result = dict(row)
    result["comparison"] = (
        json.loads(result.pop("comparison_json"))
        if result["comparison_json"]
        else None
    )

    return result


def get_all_jobs() -> list[dict]:
    with connect_db() as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            "SELECT * FROM recovery_jobs ORDER BY created_at DESC"
        ).fetchall()

    jobs = []

    for row in rows:
        item = dict(row)
        raw_comparison = item.pop("comparison_json")
        item["comparison"] = (
            json.loads(raw_comparison) if raw_comparison else None
        )
        jobs.append(item)

    return jobs


def normalize_models(result) -> list[dict]:
    """Support either a list of models or a {'models': [...]} result."""
    if isinstance(result, dict):
        result = result.get("models", [])

    return list(result or [])

def run_recovery(model_id: str) -> dict:
    production = get_production_model()

    if production is None:
        raise LookupError("No production model is registered.")

    if production["model_id"] != model_id:
        raise ValueError(
            "Recovery can only be started for the current production model."
        )

    decision = evaluate_recovery_need(model_id)

    job_id = create_job(
        model_id=model_id,
        status="PENDING",
        reason="Recovery health check started.",
    )

    # Do not retrain without sufficient performance evidence.
    if decision["status"] == "WAITING_FOR_DATA":
        update_job(
            job_id,
            status="WAITING_FOR_DATA",
            reason=decision["reason"],
        )
        return get_job(job_id)

    if not decision["recovery_required"]:
        update_job(
            job_id,
            status="NO_RECOVERY_REQUIRED",
            reason=decision["reason"],
        )
        return get_job(job_id)

    try:
        update_job(
            job_id,
            status="RETRAINING",
            reason="Production model is degraded; training candidate.",
        )

        # Use the production model's dataset explicitly.
        # This avoids accidentally selecting a different, newer dataset.
        existing_models = normalize_models(list_models())
        previous_ids = {
            model["model_id"] for model in existing_models
        }

        retrain_candidate(production["dataset_path"])

        updated_models = normalize_models(list_models())

        new_candidates = [
            model
            for model in updated_models
            if model["model_id"] not in previous_ids
            and model["status"] == "CANDIDATE"
        ]

        if not new_candidates:
            raise RuntimeError(
                "Retraining finished, but no new candidate was found "
                "in the model registry."
            )

        # If more than one candidate appeared, select the most recent.
        new_candidates.sort(
            key=lambda model: model.get("created_at", ""),
            reverse=True,
        )
        candidate = new_candidates[0]
        candidate_id = candidate["model_id"]

        update_job(
            job_id,
            status="EVALUATING",
            reason="Candidate registered; comparing against production.",
            candidate_model_id=candidate_id,
        )

        comparison = compare_models(candidate_id)
        recommendation = comparison["recommendation"]

        if recommendation == "CANDIDATE_ELIGIBLE_FOR_APPROVAL":
            status = "AWAITING_APPROVAL"
            reason = "Candidate passed the configured acceptance checks."
        else:
            status = "REJECTED"
            reason = (
                "Candidate did not satisfy the configured acceptance "
                "criteria. Production remains unchanged."
            )

        update_job(
            job_id,
            status=status,
            reason=reason,
            candidate_model_id=candidate_id,
            comparison=comparison,
        )

        return get_job(job_id)

    except Exception as exc:
        update_job(
            job_id,
            status="FAILED",
            reason=f"{type(exc).__name__}: {exc}",
        )
        raise

def approve_recovery_job(job_id: str) -> dict:
    job = get_job(job_id)

    if job is None:
        raise LookupError("Recovery job not found.")

    if job["status"] != "AWAITING_APPROVAL":
        raise ValueError(
            f"Cannot approve a job with status '{job['status']}'."
        )

    candidate_id = job["candidate_model_id"]

    if not candidate_id:
        raise ValueError("Recovery job has no candidate model.")

    try:
        # Both operations apply to the explicitly identified candidate.
        approve_model(candidate_id)
        promote_model(candidate_id)

        update_job(
            job_id,
            status="DEPLOYED",
            reason=(
                "Candidate approved and promoted to production."
            ),
        )

        return get_job(job_id)

    except Exception as exc:
        # The registry may have changed before an error occurred.
        # Inspect registry state before retrying the operation.
        update_job(
            job_id,
            status="APPROVAL_FAILED",
            reason=(
                f"{type(exc).__name__}: {exc}. "
                "Inspect the model registry before retrying."
            ),
        )
        raise


def reject_recovery_job(job_id: str, reason: str) -> dict:
    job = get_job(job_id)

    if job is None:
        raise LookupError("Recovery job not found.")

    if job["status"] != "AWAITING_APPROVAL":
        raise ValueError(
            f"Cannot reject a job with status '{job['status']}'."
        )

    if not reason.strip():
        raise ValueError("A rejection reason is required.")

    update_job(
        job_id,
        status="REJECTED",
        reason=f"Rejected by reviewer: {reason.strip()}",
    )

    return get_job(job_id)

def run_recovery_dry_run(model_id: str) -> dict:
    """
    Rehearse degraded-model recovery without approving or
    promoting the candidate.

    A candidate model and recovery-job record may be created.
    The production model must remain unchanged.
    """
    production = get_production_model()

    if production is None:
        raise LookupError("No production model is registered.")

    if production["model_id"] != model_id:
        raise ValueError(
            "The rehearsal must start from the current production model."
        )

    # Create a distinctly marked test job.
    job_id = create_job(
        model_id=model_id,
        status="DRY_RUN_RUNNING",
        reason="Controlled recovery rehearsal; degradation simulated.",
    )

    try:
        # Record existing models to identify the new candidate.
        existing_models = normalize_models(list_models())
        previous_ids = {
            model["model_id"] for model in existing_models
        }

        # Retrain using the production model's exact dataset.
        retrain_candidate(production["dataset_path"])

        updated_models = normalize_models(list_models())

        new_candidates = [
            model
            for model in updated_models
            if model["model_id"] not in previous_ids
            and model["status"] == "CANDIDATE"
        ]

        if not new_candidates:
            raise RuntimeError(
                "Retraining finished, but no new candidate was registered."
            )

        new_candidates.sort(
            key=lambda model: model.get("created_at", ""),
            reverse=True,
        )

        candidate = new_candidates[0]
        candidate_id = candidate["model_id"]

        update_job(
            job_id,
            status="DRY_RUN_EVALUATING",
            reason="Candidate registered; comparing model metrics.",
            candidate_model_id=candidate_id,
        )

        # Evaluate candidate against the current production model.
        comparison = compare_models(candidate_id)

        recommendation = comparison["recommendation"]

        if recommendation == "CANDIDATE_ELIGIBLE_FOR_APPROVAL":
            outcome = "Candidate passed comparison; approval was not requested."
        else:
            outcome = "Candidate failed comparison; production remains unchanged."

        # Never use approve_model() or promote_model() in this function.
        update_job(
            job_id,
            status="DRY_RUN_COMPLETED",
            reason=(
                f"Rehearsal completed. {outcome} "
                f"Comparison recommendation: {recommendation}."
            ),
            candidate_model_id=candidate_id,
            comparison=comparison,
        )

        # Verify the production model ID has not changed.
        current_production = get_production_model()

        if (
            current_production is None
            or current_production["model_id"] != model_id
        ):
            raise RuntimeError(
                "Production model changed during the rehearsal. "
                "Inspect the registry immediately."
            )

        result = get_job(job_id)

        result["rehearsal"] = True
        result["production_changed"] = False
        result["candidate_recommendation"] = recommendation

        return result

    except Exception as exc:
        update_job(
            job_id,
            status="DRY_RUN_FAILED",
            reason=f"{type(exc).__name__}: {exc}",
        )
        raise

initialize_recovery_jobs()