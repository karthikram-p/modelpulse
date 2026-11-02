from ml.performance_monitor import get_model_health


def evaluate_recovery_need(model_id: str) -> dict:
    """
    Decide whether a model is eligible for a retraining request.

    This function does not train or deploy a model.
    It only evaluates the current health status.
    """

    health = get_model_health(model_id)

    if health["status"] == "INSUFFICIENT_DATA":
        return {
            "model_id": model_id,
            "recovery_required": False,
            "status": "WAITING_FOR_DATA",
            "reason": health["message"],
        }

    if health["status"] == "DEGRADED":
        return {
            "model_id": model_id,
            "recovery_required": True,
            "status": "RETRAINING_RECOMMENDED",
            "reason": health["message"],
        }

    return {
        "model_id": model_id,
        "recovery_required": False,
        "status": "MODEL_HEALTHY",
        "reason": health["message"],
    }