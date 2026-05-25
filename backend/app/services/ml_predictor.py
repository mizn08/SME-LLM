"""Load sklearn/xgboost models and produce probabilities + SHAP-style explanations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.core.config import get_settings

FEATURE_ORDER = [
    "days_cash_on_hand",
    "current_ratio",
    "burn_rate_monthly_rm",
    "purchase_amount",
    "purchase_to_burn",
    "is_digitalisation",
    "is_agri",
    "monthly_net_cash",
]


def _model_dir() -> Path:
    settings = get_settings()
    base = Path(__file__).resolve().parents[1]
    configured = Path(settings.ML_MODELS_DIR)
    if configured.is_absolute():
        return configured
    # Docker image: backend/app/ml_models (bundled .pkl files)
    docker_dir = base / "ml_models"
    if docker_dir.is_dir() and any(docker_dir.glob("*.pkl")):
        return docker_dir
    # Development: ml_pipeline/models
    return Path(__file__).resolve().parents[2] / "ml_pipeline" / "models"


def _paths() -> tuple[Path, Path, Path, Path, Path]:
    ml_dir = _model_dir()
    return (
        ml_dir / "logistic_regression.pkl",
        ml_dir / "random_forest.pkl",
        ml_dir / "xgboost.pkl",
        ml_dir / "lightgbm.pkl",
        ml_dir / "feature_order.json",
    )


def models_exist() -> bool:
    lr, rf, xgb, _lgb, _fo = _paths()
    return lr.is_file() and rf.is_file() and xgb.is_file()


def _heuristic_probability(row: dict[str, float]) -> float:
    """Fallback when .pkl files are missing (e.g. first run before training)."""
    dch = row["days_cash_on_hand"]
    p2b = row["purchase_to_burn"]
    score = 0.45
    if dch < 20:
        score += 0.25
    if dch < 45:
        score += 0.1
    if p2b > 1.5:
        score += 0.15
    if row["current_ratio"] < 1.1:
        score += 0.1
    return float(min(max(score, 0.05), 0.95))


def build_feature_vector(
    kpis: dict[str, float],
    purchase_amount: float,
    purchase_category: str,
) -> dict[str, float]:
    burn = max(kpis.get("burn_rate_monthly_rm", 1.0), 1.0)
    cat_lower = purchase_category.lower()
    is_digital = 1.0 if any(
        k in cat_lower for k in ("digital", "software", "it", "cloud", "computer", "tech")
    ) else 0.0
    is_agri = 1.0 if any(k in cat_lower for k in ("agri", "farm", "crop", "livestock")) else 0.0
    monthly_net = kpis.get("net_operating_cash_rm", 0.0) / 3.0
    return {
        "days_cash_on_hand": kpis.get("days_cash_on_hand", 30.0),
        "current_ratio": kpis.get("current_ratio", 1.2),
        "burn_rate_monthly_rm": burn,
        "purchase_amount": purchase_amount,
        "purchase_to_burn": purchase_amount / burn,
        "is_digitalisation": is_digital,
        "is_agri": is_agri,
        "monthly_net_cash": monthly_net,
    }


def predict_probability(feature_row: dict[str, float]) -> tuple[float, dict[str, Any]]:
    """Return averaged ML probability and debug info."""
    if models_exist():
        try:
            lr_m = joblib.load(_paths()[0])
            rf_m = joblib.load(_paths()[1])
            xgb_m = joblib.load(_paths()[2])
            lgb_path = _paths()[3]
            X = pd.DataFrame([feature_row])[FEATURE_ORDER]
            lr_p = float(lr_m.predict_proba(X)[0][1])
            rf_p = float(rf_m.predict_proba(X)[0][1])
            xgb_p = float(xgb_m.predict_proba(X)[0][1])
            probs = [lr_p, rf_p, xgb_p]
            dbg: dict[str, Any] = {"lr": lr_p, "rf": rf_p, "xgb": xgb_p}
            if lgb_path.is_file():
                lgb_m = joblib.load(lgb_path)
                lgb_p = float(lgb_m.predict_proba(X)[0][1])
                probs.append(lgb_p)
                dbg["lgb"] = lgb_p
            prob = sum(probs) / len(probs)
            return prob, dbg
        except Exception:
            pass
    prob = _heuristic_probability(feature_row)
    return prob, {"lr": None, "rf": None, "xgb": None, "heuristic": True}


def compute_shap_top3(feature_row: dict[str, float]) -> list[dict[str, Any]]:
    """Top-3 local attributions using XGBoost SHAP or coefficient proxy."""
    items: list[dict[str, Any]] = []
    if models_exist():
        try:
            import shap  # type: ignore

            _, _, xgb_path, _, _ = _paths()
            model = joblib.load(xgb_path)
            X = pd.DataFrame([feature_row])[FEATURE_ORDER]
            explainer = shap.TreeExplainer(model)
            sv = explainer.shap_values(X)
            if isinstance(sv, list):
                sv = sv[1]
            vals = sv[0]
            pairs = list(zip(FEATURE_ORDER, vals, strict=False))
            pairs.sort(key=lambda x: abs(x[1]), reverse=True)
            for name, impact in pairs[:3]:
                direction = "positive" if impact >= 0 else "negative"
                items.append(
                    {
                        "feature": name,
                        "value": float(feature_row[name]),
                        "impact": float(round(impact, 4)),
                        "direction": direction,
                    }
                )
            return items
        except Exception:
            pass

    # Fallback: simple sensitivity narrative drivers
    drivers = [
        ("days_cash_on_hand", -0.02 * (60 - feature_row["days_cash_on_hand"])),
        ("purchase_to_burn", 0.08 * (feature_row["purchase_to_burn"] - 1)),
        ("current_ratio", 0.05 * (feature_row["current_ratio"] - 1)),
    ]
    drivers.sort(key=lambda x: abs(x[1]), reverse=True)
    for name, impact in drivers[:3]:
        items.append(
            {
                "feature": name,
                "value": float(feature_row[name]),
                "impact": float(round(impact, 4)),
                "direction": "positive" if impact >= 0 else "negative",
            }
        )
    return items
