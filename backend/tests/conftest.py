"""Pytest fixtures — isolated SQLite test DB (never corrupts bnpl_local.db)."""

from __future__ import annotations

import importlib
import os
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_TEST_DB_PATH = _BACKEND_ROOT / "data" / "test_bnpl.db"
_TEST_DB_URL = f"sqlite:///{_TEST_DB_PATH.as_posix()}"


def _remove_sqlite_sidecars(path: Path) -> None:
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(f"{path}{suffix}")
        if sidecar.exists():
            sidecar.unlink()


def _sqlite_opens(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 100:
        return False
    try:
        conn = sqlite3.connect(str(path), timeout=5)
        conn.execute("SELECT 1 FROM sqlite_schema LIMIT 1")
        conn.close()
        return True
    except sqlite3.Error:
        return False


def _seed_test_database() -> None:
    _TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()
    _remove_sqlite_sidecars(_TEST_DB_PATH)

    os.environ["DATABASE_URL"] = _TEST_DB_URL
    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.db.session as db_session

    importlib.reload(db_session)

    from app.db.session import SessionLocal
    from app.services.database_init import init_database

    db = SessionLocal()
    try:
        init_database(db)
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def test_sqlite_database():
    """Fresh seeded DB for the whole test session."""
    if not _sqlite_opens(_TEST_DB_PATH):
        _seed_test_database()
    elif _sqlite_opens(_TEST_DB_PATH):
        conn = sqlite3.connect(str(_TEST_DB_PATH))
        try:
            count = conn.execute("SELECT COUNT(*) FROM sme_profile").fetchone()[0]
        except sqlite3.Error:
            count = 0
        finally:
            conn.close()
        if count < 1:
            _seed_test_database()
    else:
        _seed_test_database()

    os.environ["DATABASE_URL"] = _TEST_DB_URL
    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.db.session as db_session

    importlib.reload(db_session)
    yield _TEST_DB_PATH


@pytest.fixture(scope="session")
def engine(test_sqlite_database):
    url = _TEST_DB_URL
    eng = create_engine(url, connect_args={"check_same_thread": False})
    return eng


@pytest.fixture
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
