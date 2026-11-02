import pandas as pd

from pathlib import Path

from ml.train import FEATURE_COLUMNS


BASE_DIR = Path(__file__).resolve().parent.parent


def detect_data_drift(
    training_data_path: str,
    recent_predictions: list[dict],
    threshold: float = 2.0,
) -> dict:
    """
    Compare training-data statistics with recent prediction inputs.

    A feature is flagged when its recent mean differs from the
    training mean by more than threshold training standard deviations.
    """

    if not recent_predictions:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": "No recent predictions available.",
            "features": {},
        }

    if threshold <= 0:
        raise ValueError("Threshold must be greater than zero.")

    training_path = Path(training_data_path)

    if not training_path.is_file():
        raise FileNotFoundError(
            f"Training dataset not found: {training_path}"
        )

    training_df = pd.read_parquet(training_path)

    missing_columns = [
        column for column in FEATURE_COLUMNS
        if column not in training_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Training dataset is missing columns: {missing_columns}"
        )

    recent_df = pd.DataFrame(
        [item["input_features"] for item in recent_predictions]
    )

    missing_recent = [
        column for column in FEATURE_COLUMNS
        if column not in recent_df.columns
    ]

    if missing_recent:
        raise ValueError(
            f"Recent predictions are missing features: {missing_recent}"
        )

    feature_results = {}

    for column in FEATURE_COLUMNS:
        training_values = pd.to_numeric(
            training_df[column], errors="coerce"
        ).dropna()

        recent_values = pd.to_numeric(
            recent_df[column], errors="coerce"
        ).dropna()

        if training_values.empty or recent_values.empty:
            feature_results[column] = {
                "status": "INSUFFICIENT_DATA"
            }
            continue

        training_mean = float(training_values.mean())
        training_std = float(training_values.std(ddof=0))
        recent_mean = float(recent_values.mean())

        difference = abs(recent_mean - training_mean)

        if training_std == 0:
            score = 0.0 if difference == 0 else None
            drift_detected = difference != 0
        else:
            score = difference / training_std
            drift_detected = score > threshold

        feature_results[column] = {
            "training_mean": round(training_mean, 4),
            "recent_mean": round(recent_mean, 4),
            "standardized_difference": (
                round(score, 4) if score is not None else None
            ),
            "drift_detected": drift_detected,
            "status": (
                "DRIFT_DETECTED"
                if drift_detected
                else "NORMAL"
            ),
        }

    drifted_features = [
        name
        for name, result in feature_results.items()
        if result.get("drift_detected", False)
    ]

    return {
        "status": (
            "DRIFT_DETECTED"
            if drifted_features
            else "NORMAL"
        ),
        "threshold": threshold,
        "prediction_count": len(recent_predictions),
        "drifted_features": drifted_features,
        "features": feature_results,
    }