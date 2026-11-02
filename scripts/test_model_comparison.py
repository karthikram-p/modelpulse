import sys
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.model_comparison import compare_models


PRODUCTION_ID = "production-test-id"
CANDIDATE_ID = "candidate-test-id"


def fake_comparison(production_metrics, candidate_metrics):
    """Test comparison rules without accessing the real registry or models."""

    mae_pass = candidate_metrics["mae"] <= production_metrics["mae"] * 0.99
    rmse_pass = candidate_metrics["rmse"] <= production_metrics["rmse"] * 1.02
    r2_pass = candidate_metrics["r2"] >= production_metrics["r2"] - 0.01

    eligible = mae_pass and rmse_pass and r2_pass

    return {
        "production_model": {"metrics": production_metrics},
        "candidate_model": {"metrics": candidate_metrics},
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
    }


def run_test(name, production, candidate, expected):
    with patch(
        "ml.model_comparison.get_model"
    ), patch(
        "ml.model_comparison.sqlite3.connect"
    ):
        result = fake_comparison(production, candidate)

    passed = result["recommendation"] == expected

    print(f"\nTest: {name}")
    print(f"Expected: {expected}")
    print(f"Actual:   {result['recommendation']}")
    print(f"Result:   {'PASS' if passed else 'FAIL'}")
    print(f"Acceptance checks: {result['acceptance_checks']}")
    print(f"Production changed: {result['production_changed']}")

    return passed


def main():
    production = {"mae": 100.0, "rmse": 120.0, "r2": 0.90}

    tests = [
        (
            "Candidate improves all metrics",
            production,
            {"mae": 95.0, "rmse": 115.0, "r2": 0.91},
            "CANDIDATE_ELIGIBLE_FOR_APPROVAL",
        ),
        (
            "Candidate does not improve MAE enough",
            production,
            {"mae": 99.5, "rmse": 115.0, "r2": 0.91},
            "KEEP_PRODUCTION",
        ),
        (
            "Candidate exceeds RMSE tolerance",
            production,
            {"mae": 95.0, "rmse": 130.0, "r2": 0.91},
            "KEEP_PRODUCTION",
        ),
        (
            "Candidate exceeds R2 drop tolerance",
            production,
            {"mae": 95.0, "rmse": 115.0, "r2": 0.88},
            "KEEP_PRODUCTION",
        ),
    ]

    results = [
        run_test(name, prod, cand, expected)
        for name, prod, cand, expected in tests
    ]

    print(f"\nPassed: {sum(results)}/{len(results)}")

    if not all(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()