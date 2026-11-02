import sys
from pathlib import Path

# Add the project root to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml.recovery_workflow import run_recovery_dry_run

from unittest.mock import patch

from ml.recovery_workflow import run_recovery_dry_run


PRODUCTION_ID = "production-model-001"
CANDIDATE_ID = "candidate-model-002"
JOB_ID = "dry-run-job-001"

PRODUCTION_MODEL = {
    "model_id": PRODUCTION_ID,
    "dataset_path": "datasets/bike_sharing/hour.csv",
    "status": "PRODUCTION",
}

CANDIDATE_MODEL = {
    "model_id": CANDIDATE_ID,
    "status": "CANDIDATE",
    "created_at": "2026-10-31T10:00:00",
}

COMPARISON = {
    "recommendation": "KEEP_PRODUCTION",
    "production_model": {
        "metrics": {"mae": 44.99, "rmse": 69.56, "r2": 0.9005}
    },
    "candidate_model": {
        "metrics": {"mae": 44.99, "rmse": 69.56, "r2": 0.9005}
    },
}


def test_dry_run_never_promotes_production():
    existing_models = [PRODUCTION_MODEL]
    updated_models = [PRODUCTION_MODEL, CANDIDATE_MODEL]

    jobs = {}

    def fake_create_job(model_id, status, reason):
        jobs[JOB_ID] = {
            "job_id": JOB_ID,
            "production_model_id": model_id,
            "status": status,
            "reason": reason,
        }
        return JOB_ID

    def fake_update_job(job_id, **kwargs):
        jobs[job_id].update(kwargs)

    def fake_get_job(job_id):
        return jobs[job_id].copy()

    with (
        patch(
            "ml.recovery_workflow.get_production_model",
            side_effect=[PRODUCTION_MODEL, PRODUCTION_MODEL],
        ),
        patch(
            "ml.recovery_workflow.create_job",
            side_effect=fake_create_job,
        ),
        patch(
            "ml.recovery_workflow.list_models",
            side_effect=[existing_models, updated_models],
        ),
        patch("ml.recovery_workflow.retrain_candidate") as mock_retrain,
        patch(
            "ml.recovery_workflow.compare_models",
            return_value=COMPARISON,
        ) as mock_compare,
        patch(
            "ml.recovery_workflow.update_job",
            side_effect=fake_update_job,
        ),
        patch(
            "ml.recovery_workflow.get_job",
            side_effect=fake_get_job,
        ),
        patch(
            "ml.recovery_workflow.approve_model"
        ) as mock_approve,
        patch(
            "ml.recovery_workflow.promote_model"
        ) as mock_promote,
    ):
        result = run_recovery_dry_run(PRODUCTION_ID)

    mock_retrain.assert_called_once_with(
        PRODUCTION_MODEL["dataset_path"]
    )
    mock_compare.assert_called_once_with(CANDIDATE_ID)

    mock_approve.assert_not_called()
    mock_promote.assert_not_called()

    assert result["status"] == "DRY_RUN_COMPLETED"
    assert result["candidate_model_id"] == CANDIDATE_ID
    assert result["rehearsal"] is True
    assert result["production_changed"] is False
    assert result["candidate_recommendation"] == "KEEP_PRODUCTION"

    print("PASS: Candidate retraining was executed.")
    print("PASS: Candidate was compared with production.")
    print("PASS: No model approval occurred.")
    print("PASS: No model promotion occurred.")
    print("PASS: Production model remained unchanged.")
    print("PASS: Dry run completed successfully.")


def test_dry_run_rejects_non_production_model():
    with (
        patch(
            "ml.recovery_workflow.get_production_model",
            return_value=PRODUCTION_MODEL,
        ),
        patch(
            "ml.recovery_workflow.create_job"
        ) as mock_create_job,
        patch(
            "ml.recovery_workflow.approve_model"
        ) as mock_approve,
        patch(
            "ml.recovery_workflow.promote_model"
        ) as mock_promote,
    ):
        try:
            run_recovery_dry_run("some-other-model")
        except ValueError as exc:
            assert "current production model" in str(exc)
        else:
            raise AssertionError("Expected ValueError was not raised.")

    mock_create_job.assert_not_called()
    mock_approve.assert_not_called()
    mock_promote.assert_not_called()

    print("PASS: Dry run rejects a non-production model ID.")
    print("PASS: No recovery job or promotion was triggered.")


def main():
    test_dry_run_never_promotes_production()
    test_dry_run_rejects_non_production_model()
    print("\nPassed: 2/2")


if __name__ == "__main__":
    main()