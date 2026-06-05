"""HTTP smoke tests for critical go-live endpoints."""

from __future__ import annotations

import importlib
import os

import pytest
from fastapi.testclient import TestClient

from tests.conftest import _TEST_DB_URL


@pytest.fixture
def client(test_sqlite_database):
    os.environ["DATABASE_URL"] = _TEST_DB_URL
    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.db.session as db_session

    importlib.reload(db_session)
    from app.main import app

    return TestClient(app)


@pytest.mark.integration
def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200


@pytest.mark.integration
def test_dashboard_sme1(client):
    r = client.get("/sme/1/dashboard")
    assert r.status_code == 200, r.text
    data = r.json()
    kpis = data["kpis"]
    assert "net_operating_cash_rm" in kpis
    assert data["health_score"] is not None
    assert data["health_grade"] is not None


@pytest.mark.integration
def test_chat_respects_purchase_amount(client):
    r = client.post(
        "/chat",
        json={
            "sme_id": 1,
            "message": "Should I use TEKUN for RM 103622?",
            "purchase_amount": 50000,
            "purchase_category": "equipment",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sme_id"] == 1
    assert "answer" in body and len(body["answer"]) > 10
