import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.model_comparison import compare_models


PRODUCTION_ID = "production-test-id"
CANDIDATE_ID = "candidate-test-id"


class FakeModel:
    def __init__(self, predictions):
        self.predictions = np.asarray(predictions, dtype=float)

    def predict(self, X):
        assert len(X) == len(self.predictions)
        return self.predictions


def run_test(name, production_predictions, candidate_predictions,
             expected_recommendation):

    rows = 20
    dataset = pd.DataFrame({
        "season": [1] * rows,
        "yr": [1] * rows,
        "mnth": [1] * rows,
        "hr": list(range(rows)),
        "holiday": [0] * rows,
        "weekday": [1] * rows,
        "workingday": [1] * rows,
        "weathersit": [1] * rows,
        "temp": [0.5] * rows,
        "atemp": [0.5] * rows,
        "hum": [0.5] * rows,
        "windspeed": [0.1] * rows,
        "cnt": [100.0] * rows,
    })

    production = {
        "model_id": PRODUCTION_ID,
        "version": "v1",
        "status": "PRODUCTION",
        "dataset_path": str(BASE_DIR / "fake.parquet"),
        "artifact_path": "fake-production.joblib",
    }

    candidate = {
        "model_id": CANDIDATE_ID,
        "version": "v2",
        "status": "CANDIDATE",
        "dataset_path": str(BASE_DIR / "fake.parquet"),
        "artifact_path": "fake-candidate.joblib",
    }

    fake_connection = MagicMock()
    fake_connection.__enter__.return_value = fake_connection
    fake_connection.__exit__.return_value = False

    fake_cursor = MagicMock()
    fake_cursor.fetchone.return_value = production
    fake_connection.execute.return_value = fake_cursor

    def fake_connect(*args, **kwargs):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.__exit__.return_value = False

        cursor = MagicMock()
        cursor.fetchone.return_value = (
            candidate if args else production
        )
        connection.execute.return_value = cursor
        return connection

    with (
        patch(
            "ml.model_comparison.sqlite3.connect",
            side_effect=[fake_connection, fake_connection],
        ),
        patch(
            "ml.model_comparison.get_model",
            return_value=candidate,
        ),
        patch(
            "ml.model_comparison.Path.is_file",
            return_value=True,
        ),
        patch(
            "ml.model_comparison.pd.read_parquet",
            return_value=dataset,
        ),
        patch(
            "ml.model_comparison.joblib.load",
            side_effect=[
                FakeModel(production_predictions),
                FakeModel(candidate_predictions),
            ],
        ),
    ):
        result = compare_models(CANDIDATE_ID)

    actual = result["recommendation"]
    passed = actual == expected_recommendation

    print(f"\nTest: {name}")
    print(f"Expected: {expected_recommendation}")
    print(f"Actual:   {actual}")
    print(f"Result:   {'PASS' if passed else 'FAIL'}")
    print(f"Acceptance checks: {result['acceptance_checks']}")
    print(f"Production changed: {result['production_changed']}")

    return passed


def main():
    y_true = np.full(4, 100.0)

    tests = [
        (
            "Candidate improves MAE",
            y_true + 20,
            y_true + 5,
            "CANDIDATE_ELIGIBLE_FOR_APPROVAL",
        ),
        (
            "Candidate fails MAE improvement",
            y_true + 20,
            y_true + 19.9,
            "KEEP_PRODUCTION",
        ),
    ]

    results = []

    for name, prod_predictions, cand_predictions, expected in tests:
        results.append(
            run_test(
                name,
                prod_predictions,
                cand_predictions,
                expected,
            )
        )

    print(f"\nPassed: {sum(results)}/{len(results)}")

    if not all(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()