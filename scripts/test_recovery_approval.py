import sys
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.recovery_workflow import approve_recovery_job


JOB_ID = "test-recovery-job"
CANDIDATE_ID = "test-candidate-model"


def test_approval_rejected_for_ineligible_job():
    job = {
        "job_id": JOB_ID,
        "status": "DRY_RUN_COMPLETED",
        "candidate_model_id": CANDIDATE_ID,
    }

    with patch(
        "ml.recovery_workflow.get_job",
        return_value=job,
    ), patch(
        "ml.recovery_workflow.approve_model",
    ) as mock_approve, patch(
        "ml.recovery_workflow.promote_model",
    ) as mock_promote:

        try:
            approve_recovery_job(JOB_ID)
            raise AssertionError("Expected approval to be rejected.")
        except ValueError:
            pass

        assert not mock_approve.called
        assert not mock_promote.called

    print("PASS: Dry-run jobs cannot be approved.")
    print("PASS: No model was approved or promoted.")


def test_approval_rejected_for_missing_job():
    with patch(
        "ml.recovery_workflow.get_job",
        return_value=None,
    ), patch(
        "ml.recovery_workflow.approve_model",
    ) as mock_approve, patch(
        "ml.recovery_workflow.promote_model",
    ) as mock_promote:

        try:
            approve_recovery_job(JOB_ID)
            raise AssertionError("Expected missing job to be rejected.")
        except LookupError:
            pass

        assert not mock_approve.called
        assert not mock_promote.called

    print("PASS: Missing recovery jobs cannot be approved.")

def test_eligible_job_approves_and_promotes_candidate():
    job = {
        "job_id": JOB_ID,
        "status": "AWAITING_APPROVAL",
        "candidate_model_id": CANDIDATE_ID,
    }

    with patch(
        "ml.recovery_workflow.get_job",
        return_value=job,
    ), patch(
        "ml.recovery_workflow.approve_model",
    ) as mock_approve, patch(
        "ml.recovery_workflow.promote_model",
    ) as mock_promote, patch(
        "ml.recovery_workflow.update_job",
    ) as mock_update:

        mock_update.return_value = None

        with patch(
            "ml.recovery_workflow.get_job",
            side_effect=[
                job,
                {
                    **job,
                    "status": "DEPLOYED",
                    "reason": "Candidate approved and promoted to production.",
                },
            ],
        ):
            result = approve_recovery_job(JOB_ID)

        mock_approve.assert_called_once_with(CANDIDATE_ID)
        mock_promote.assert_called_once_with(CANDIDATE_ID)

        assert result["status"] == "DEPLOYED"

    print("PASS: Eligible candidate was approved.")
    print("PASS: Correct candidate was promoted.")
    print("PASS: Recovery job reached DEPLOYED.")


def main():
    test_approval_rejected_for_ineligible_job()
    test_approval_rejected_for_missing_job()
    test_eligible_job_approves_and_promotes_candidate()
    print("\nPassed: 3/3")

if __name__ == "__main__":
    main()