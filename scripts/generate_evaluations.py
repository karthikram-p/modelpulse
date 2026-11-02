import sys
from pathlib import Path

import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.registry import get_production_model
from ml.prediction_logger import log_prediction
from ml.performance_monitor import record_actual_value


FEATURE_COLUMNS = [
    "season", "yr", "mnth", "hr", "holiday", "weekday",
    "workingday", "weathersit", "temp", "atemp", "hum", "windspeed"
]

TARGET_COLUMN = "cnt"


def main():
    production = get_production_model()

    if production is None:
        raise RuntimeError("No production model is registered.")

    dataset_path = Path(production["dataset_path"])
    artifact_path = Path(production["artifact_path"])

    if not dataset_path.is_file():
        raise FileNotFoundError(dataset_path)

    if not artifact_path.is_file():
        raise FileNotFoundError(artifact_path)

    df = pd.read_parquet(dataset_path)

    required = FEATURE_COLUMNS + [TARGET_COLUMN]
    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df[required].copy()

    if df.isna().any().any():
        raise ValueError("Dataset contains missing values.")

    # Use the chronological holdout portion.
    split_index = int(len(df) * 0.8)
    test_df = df.iloc[split_index:].copy()

    model = joblib.load(artifact_path)

    # Generate genuine predictions for held-out observations.
    # The actual values come from the dataset, not from predictions.
    predictions = model.predict(test_df[FEATURE_COLUMNS])

    recorded = 0

    for index, (_, row) in enumerate(test_df.iterrows()):
        features = {
            column: float(row[column])
            for column in FEATURE_COLUMNS
        }

        # Log prediction using the existing project's function.
        result = log_prediction(
            model_id=production["model_id"],
            model_version=production["version"],
            input_features=features,
            predicted_value=float(predictions[index]),
        )

        # Support either a returned prediction ID string or a dict.
        if isinstance(result, dict):
            prediction_id = result.get("prediction_id")
        else:
            prediction_id = result

        if not prediction_id:
            raise RuntimeError(
                "Prediction logger did not return a prediction ID."
            )

        record_actual_value(
            prediction_id=prediction_id,
            actual_value=float(row[TARGET_COLUMN]),
        )

        recorded += 1

    print({
        "model_id": production["model_id"],
        "model_version": production["version"],
        "evaluations_recorded": recorded,
        "evaluation_source": "held-out Bike Sharing dataset",
        "status": "SUCCESS",
    })


if __name__ == "__main__":
    main()