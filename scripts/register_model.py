import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(BASE_DIR))

from ml.registry import register_model, list_models


MODEL_DIR = BASE_DIR / "storage" / "models"
PROCESSED_DIR = BASE_DIR / "storage" / "processed"

model_path = MODEL_DIR / "bike_rental_model.joblib"
metrics_path = MODEL_DIR / "metrics.json"

dataset_files = sorted(
    PROCESSED_DIR.glob("*.parquet"),
    key=lambda path: path.stat().st_mtime,
    reverse=True,
)

if not dataset_files:
    raise FileNotFoundError(
        "No processed dataset found."
    )

result = register_model(
    artifact_path=str(model_path),
    dataset_path=str(dataset_files[0]),
    metrics_path=str(metrics_path),
)

print("Model registered successfully:")
print(json.dumps(result, indent=2))

print("\nRegistered models:")
print(json.dumps(list_models(), indent=2))