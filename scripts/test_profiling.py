import sys
import json
from pathlib import Path

# Add the project root to Python's module search path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from data_pipeline.profiling import profile_dataset


PROCESSED_DIR = BASE_DIR / "storage" / "processed"

parquet_files = sorted(
    PROCESSED_DIR.glob("*.parquet"),
    key=lambda path: path.stat().st_mtime,
    reverse=True,
)

if not parquet_files:
    raise FileNotFoundError(
        "No processed Parquet files found."
    )

result = profile_dataset(str(parquet_files[0]))

print(json.dumps(result, indent=2))