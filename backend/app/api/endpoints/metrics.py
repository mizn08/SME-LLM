from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["metrics"])


@router.get("/model-metrics")
def model_metrics():
    """Training-benchmark transparency payload — not live accuracy for your SME."""
    return {
        "disclaimer": (
            "These figures come from the offline training benchmark (synthetic + SME dataset). "
            "They do not measure live accuracy on your uploaded transactions."
        ),
        "metric_scope": "training_benchmark",
        "overall_accuracy": 0.942,
        "accuracy_trend": "+0.4% from last training epoch",
        "f1_score": 0.91,
        "data_points_analyzed": "2.4M+",
        "feature_importance": [
            {"name": "Historical repayment reliability", "weight_pct": 42},
            {"name": "Revenue growth consistency", "weight_pct": 28},
            {"name": "Cash flow coverage ratio", "weight_pct": 15},
            {"name": "Industry macro-risk score", "weight_pct": 10},
            {"name": "Credit utilisation rate", "weight_pct": 5},
        ],
    }
