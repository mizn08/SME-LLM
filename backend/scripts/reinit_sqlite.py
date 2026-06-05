#!/usr/bin/env python3
"""Recreate bnpl_local.db when SQLite reports 'unsupported file format'."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    db_path = BACKEND_ROOT / "bnpl_local.db"
    if db_path.exists():
        backup = BACKEND_ROOT / "bnpl_local.db.bak"
        shutil.copy(db_path, backup)
        db_path.unlink()
        print(f"Backed up corrupt DB to {backup.name}")
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(f"{db_path}{suffix}")
            if sidecar.exists():
                sidecar.unlink()

    import os

    os.chdir(BACKEND_ROOT)
    os.environ.setdefault("DATABASE_URL", "sqlite:///./bnpl_local.db")
    os.environ.setdefault("PYTHONPATH", ".")

    from app.db.session import SessionLocal
    from app.services.database_init import init_database

    db = SessionLocal()
    try:
        result = init_database(db)
        db.commit()
    finally:
        db.close()

    print("Reinitialized bnpl_local.db:", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
