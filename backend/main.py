from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from data_pipeline.ingestion import ingest_dataset

from ml.registry import (
    list_models,
    approve_model,
    promote_model,
)

import joblib
import pandas as pd

from fastapi import HTTPException
from pydantic import BaseModel, Field

from ml.registry import get_production_model

from ml.prediction_logger import log_prediction, list_predictions

from ml.monitor import detect_data_drift
from ml.registry import get_production_model
from ml.prediction_logger import list_predictions

from pydantic import BaseModel, Field

from ml.performance_monitor import (
    record_actual_value,
    get_performance_summary,
)

import sqlite3

from ml.performance_monitor import get_model_health

from ml.recovery import evaluate_recovery_need

from ml.model_comparison import compare_models

from ml.recovery_workflow import (
    run_recovery,
    get_job,
    get_all_jobs,
    approve_recovery_job,
    reject_recovery_job,
)

from fastapi import HTTPException

from ml.recovery_workflow import run_recovery_dry_run

from fastapi.middleware.cors import CORSMiddleware

class ActualOutcome(BaseModel):
    prediction_id: str
    actual_value: float = Field(ge=0)

class PredictionInput(BaseModel):
    season: int = Field(ge=1, le=4)
    yr: int = Field(ge=0, le=1)
    mnth: int = Field(ge=1, le=12)
    hr: int = Field(ge=0, le=23)
    holiday: int = Field(ge=0, le=1)
    weekday: int = Field(ge=0, le=6)
    workingday: int = Field(ge=0, le=1)
    weathersit: int = Field(ge=1, le=4)
    temp: float = Field(ge=0, le=1)
    atemp: float = Field(ge=0, le=1)
    hum: float = Field(ge=0, le=1)
    windspeed: float = Field(ge=0, le=1)

app = FastAPI(
    title="ModelPulse API",
    description="Model Monitoring and Recovery Platform",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
def root():
    return {
        "message": "Welcome to ModelPulse",
        "version": "0.2.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "modelpulse-api",
    }


@app.post("/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

    upload_path = UPLOAD_DIR / f"{Path(file.filename).name}"

    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        upload_path.write_bytes(content)

        result = ingest_dataset(str(upload_path))

        return result

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Dataset processing failed: {exc}",
        ) from exc

    finally:
        await file.close()

@app.get("/models")
def get_models():
    return {
        "models": list_models()
    }


@app.post("/models/{model_id}/approve")
def approve_registered_model(model_id: str):
    try:
        return approve_model(model_id)

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.post("/models/{model_id}/promote")
def promote_registered_model(model_id: str):
    try:
        return promote_model(model_id)

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

@app.post("/predict")
def predict_rentals(data: PredictionInput):
    # 1. Retrieve the production model
    model_info = get_production_model()

    if model_info is None:
        raise HTTPException(
            status_code=409,
            detail="No production model available. "
                   "Approve and promote a model first."
        )

    # 2. Load the registered model artifact
    try:
        model = joblib.load(model_info["artifact_path"])
    except (OSError, ValueError, EOFError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not load the production model artifact."
        ) from exc

    # 3. Prepare input in the exact training feature order
    features = pd.DataFrame(
        [data.model_dump()]
    )

    # 4. Generate prediction
    try:
        prediction = float(model.predict(features)[0])
        prediction_record = log_prediction(
            model_id=model_info["model_id"],
            model_version=model_info["version"],
            input_features=data.model_dump(),
            predicted_value=prediction,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Prediction failed."
        ) from exc

    # 5. Return prediction and model details
    return {
        "prediction_id": prediction_record["prediction_id"],
        "model_id": model_info["model_id"],
        "model_version": f"v{model_info['version']}",
        "prediction": round(prediction, 2),
        "target": "cnt",
        "status": "SUCCESS",
        "created_at": prediction_record["created_at"],
    }

@app.get("/predictions")
def get_prediction_history(limit: int = 100):
    if not 1 <= limit <= 1000:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 1000.",
        )

    return {
        "predictions": list_predictions(limit=limit)
    }

@app.get("/monitoring/drift")
def monitor_data_drift(limit: int = 100):
    if not 10 <= limit <= 1000:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 10 and 1000.",
        )

    model_info = get_production_model()

    if model_info is None:
        raise HTTPException(
            status_code=409,
            detail="No production model available.",
        )

    predictions = list_predictions(limit=limit)

    # Only compare predictions generated by the production model.
    predictions = [
        item for item in predictions
        if item["model_id"] == model_info["model_id"]
    ]

    if len(predictions) < 10:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": "Generate at least 10 predictions "
                       "with the production model before monitoring.",
            "prediction_count": len(predictions),
        }

    try:
        result = detect_data_drift(
            training_data_path=model_info["dataset_path"],
            recent_predictions=predictions,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    return result

@app.post("/monitoring/actual")
def record_actual_outcome(data: ActualOutcome):
    try:
        return record_actual_value(
            prediction_id=data.prediction_id,
            actual_value=data.actual_value,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="This prediction has already been evaluated.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

@app.get("/monitoring/performance/{model_id}")
def model_performance_summary(model_id: str):
    return get_performance_summary(model_id)

@app.get("/monitoring/health/{model_id}")
def model_health(model_id: str):
    return get_model_health(model_id)

@app.get("/recovery/check/{model_id}")
def check_recovery(model_id: str):
    return evaluate_recovery_need(model_id)

@app.get("/models/{candidate_model_id}/compare")
def compare_registered_candidate(candidate_model_id: str):
    try:
        return compare_models(candidate_model_id)

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

@app.post("/recovery/run/{model_id}")
def start_recovery(model_id: str):
    try:
        return run_recovery(model_id)

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@app.get("/recovery/jobs")
def list_recovery_jobs():
    return {"jobs": get_all_jobs()}


@app.get("/recovery/jobs/{job_id}")
def retrieve_recovery_job(job_id: str):
    job = get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Recovery job not found.",
        )

    return job


@app.post("/recovery/jobs/{job_id}/approve")
def approve_recovery(job_id: str):
    try:
        return approve_recovery_job(job_id)

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@app.post("/recovery/jobs/{job_id}/reject")
def reject_recovery(job_id: str, reason: str):
    try:
        return reject_recovery_job(job_id, reason)

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

@app.post("/recovery/dry-run/{model_id}")
def recovery_dry_run(model_id: str):
    try:
        return run_recovery_dry_run(model_id)

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc