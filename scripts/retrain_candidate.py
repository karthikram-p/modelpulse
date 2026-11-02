import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.retraining import retrain_candidate


def main():
    dataset_path = sys.argv[1] if len(sys.argv) > 1 else None

    result = retrain_candidate(dataset_path)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()