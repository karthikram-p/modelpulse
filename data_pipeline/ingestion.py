from pathlib import Path
from uuid import uuid4

import pandas as pd

from data_pipeline.validation import validate_dataset


BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "storage" / "raw"
PROCESSED_DIR = BASE_DIR / "storage" / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def ingest_dataset(source_path: str) -> dict:
    source = Path(source_path)

    if not source.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {source}"
        )

    if source.suffix.lower() != ".csv":
        raise ValueError("Only CSV files are supported.")

    batch_id = str(uuid4())

    raw_path = RAW_DIR / f"{batch_id}.csv"
    processed_path = PROCESSED_DIR / f"{batch_id}.parquet"

    # Preserve the original dataset
    df = pd.read_csv(source)

    df.to_csv(raw_path, index=False)

    # Validate the dataset
    validation_result = validate_dataset(df)

    if not validation_result["valid"]:
        return {
            "batch_id": batch_id,
            "status": "REJECTED",
            "raw_path": str(raw_path),
            "validation": validation_result,
        }

    # Convert validated data to Parquet
    df.to_parquet(
        processed_path,
        index=False,
        engine="pyarrow",
    )

    return {
        "batch_id": batch_id,
        "status": "PROCESSED",
        "raw_path": str(raw_path),
        "processed_path": str(processed_path),
        "row_count": len(df),
        "validation": validation_result,
    }