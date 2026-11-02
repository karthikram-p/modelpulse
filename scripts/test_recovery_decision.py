import sys
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.recovery import evaluate_recovery_need


MODEL_ID = "4cf84ae1-30ae-46d4-acee-1b4220384738"


def run_test(name, health_status, expected_status):
    mocked_health = {
        "model_id": MODEL_ID,
        "status": health_status,
        "evaluation_count": 100,
        "mae": 120.0 if health_status == "DEGRADED" else 45.0,
        "mae_threshold": 75.0,
        "message": f"Simulated test condition: {health_status}",
    }

    with patch(
        "ml.recovery.get_model_health",
        return_value=mocked_health,
    ):
        result = evaluate_recovery_need(MODEL_ID)

    passed = result["status"] == expected_status

    print(f"\nTest: {name}")
    print(f"Expected: {expected_status}")
    print(f"Actual:   {result['status']}")
    print(f"Result:   {'PASS' if passed else 'FAIL'}")

    return passed


def main():
    results = [
        run_test(
            "Healthy model",
            "HEALTHY",
            "MODEL_HEALTHY",
        ),
        run_test(
            "Insufficient evaluation data",
            "INSUFFICIENT_DATA",
            "WAITING_FOR_DATA",
        ),
        run_test(
            "Degraded model",
            "DEGRADED",
            "RETRAINING_RECOMMENDED",
        ),
    ]

    print(f"\nPassed: {sum(results)}/{len(results)}")

    if not all(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()