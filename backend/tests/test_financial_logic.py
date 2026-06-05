"""Unit & integration tests for KPI, health, financing, and cross-feature consistency."""

from __future__ import annotations

import pandas as pd
import pytest

from app.services import data_processor, health_score_service
from app.services.financing_recommendation_service import (
    normalize_purchase_category,
    parse_purchase_amount,
    resolve_purchase_scenario,
)


def _sample_df() -> pd.DataFrame:
    """90 days: heavy outflows → negative net (mirrors distressed SME pattern)."""
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=90, freq="D")
    rows = []
    for i, d in enumerate(dates):
        if i % 3 == 0:
            rows.append({"txn_date": d.date(), "amount_rm": 8000.0, "category": "Sales", "is_expense": False})
        if i % 2 == 0:
            rows.append({"txn_date": d.date(), "amount_rm": 12000.0, "category": "Payroll", "is_expense": True})
    return pd.DataFrame(rows)


class TestKpiCalculations:
    def test_net_is_inflows_minus_outflows_90d(self):
        df = _sample_df()
        kpis = data_processor.compute_kpis_from_transactions(df)
        df["txn_date"] = pd.to_datetime(df["txn_date"])
        start = pd.Timestamp.today().normalize() - pd.Timedelta(days=90)
        recent = df[df["txn_date"] >= start]
        expected_net = float(
            recent.loc[~recent["is_expense"], "amount_rm"].sum()
            - recent.loc[recent["is_expense"], "amount_rm"].sum()
        )
        assert kpis["net_operating_cash_rm"] == round(expected_net, 2)

    def test_empty_df_returns_safe_defaults(self):
        kpis = data_processor.compute_kpis_from_transactions(pd.DataFrame())
        assert kpis["current_ratio"] == 1.0
        assert kpis["net_operating_cash_rm"] == 0.0

    def test_burn_is_positive_when_expenses_exist(self):
        kpis = data_processor.compute_kpis_from_transactions(_sample_df())
        assert kpis["burn_rate_monthly_rm"] > 0

    def test_monthly_series_revenue_expense_split(self):
        df = _sample_df()
        series = data_processor.monthly_series(df)
        assert series
        for p in series:
            assert "revenue_rm" in p and "expense_rm" in p
            assert p["revenue_rm"] >= 0 and p["expense_rm"] >= 0


class TestHealthScore:
    def test_score_bounded_0_100(self):
        kpis = data_processor.compute_kpis_from_transactions(_sample_df())
        h = health_score_service.compute_health_score(kpis, runway_days=15.0, anomaly_count=2)
        assert 0 <= h["health_score"] <= 100
        assert h["health_grade"] in ("A", "B", "C", "D", "E", "F")
        assert h["health_label"] in ("STRONG", "STABLE", "FAIR", "WATCH")

    def test_low_runway_lowers_score(self):
        kpis = {"current_ratio": 0.8, "days_cash_on_hand": 5.0, "burn_rate_monthly_rm": 10000.0, "expense_mtd_rm": 9000.0}
        low = health_score_service.compute_health_score(kpis, runway_days=5.0, anomaly_count=0)["health_score"]
        high = health_score_service.compute_health_score(kpis, runway_days=120.0, anomaly_count=0)["health_score"]
        assert high > low


class TestPurchaseScenarioResolution:
    def test_simulate_amount_wins_over_chat_history(self):
        amt, cat = resolve_purchase_scenario(
            "I previously asked about RM 103,622 and TEKUN",
            purchase_amount=50000.0,
            purchase_category="equipment",
        )
        assert amt == 50000.0
        assert cat == "equipment"

    def test_parse_last_rm_in_question(self):
        assert parse_purchase_amount("need RM 12,500 for POS") == 12500.0

    def test_normalize_categories(self):
        assert normalize_purchase_category("Digital / Software") == "digital"
        assert normalize_purchase_category("Equipment") == "equipment"

    def test_zero_amount_treated_as_none(self):
        amt, cat = resolve_purchase_scenario("buy equipment", purchase_amount=0)
        assert amt is None


@pytest.mark.integration
class TestLiveDatabaseConsistency:
    """Requires session test DB with seeded SME id=1 (see tests/conftest.py)."""

    def test_snapshot_kpis_match_data_processor(self, db_session):
        from app.services.sme_financial_snapshot import get_snapshot

        snap = get_snapshot(db_session, 1)
        df = data_processor.load_transactions_df(db_session, 1)
        kpis = data_processor.compute_kpis_from_transactions(df)
        assert snap["kpis"]["net_operating_cash_rm"] == kpis["net_operating_cash_rm"]
        assert snap["kpis"]["burn_rate_monthly_rm"] == kpis["burn_rate_monthly_rm"]

    def test_recommendation_uses_same_snapshot_kpis(self, db_session):
        from app.services.financing_recommendation_service import build_recommendation
        from app.services.sme_financial_snapshot import get_snapshot

        snap = get_snapshot(db_session, 1)
        rec = build_recommendation(db_session, 1, purchase_amount=50000.0, purchase_category="equipment")
        assert rec["snapshot"]["kpis"]["net_operating_cash_rm"] == snap["kpis"]["net_operating_cash_rm"]
        assert rec["purchase_amount"] == 50000.0
        assert "star_line" in rec

    def test_dashboard_health_matches_snapshot(self, db_session):
        from app.services.sme_financial_snapshot import get_snapshot
        from app.services import data_processor, forecast_service, health_score_service, unsupervised_service

        df = data_processor.load_transactions_df(db_session, 1)
        kpis = data_processor.compute_kpis_from_transactions(df)
        fc = forecast_service.forecast_runway(db_session, 1)
        anomalies = unsupervised_service.detect_anomalies(db_session, 1)
        health = health_score_service.compute_health_score(
            kpis, fc.get("runway_days_est"), int(anomalies.get("total_flagged") or 0)
        )
        snap = get_snapshot(db_session, 1)
        assert health["health_score"] == snap["health"]["health_score"]
