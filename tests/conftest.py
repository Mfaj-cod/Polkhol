from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import database as db_module
from app.config import Settings
from app.main import create_app


@pytest.fixture()
def client():
    test_data_dir = ROOT / '.testdata'
    test_data_dir.mkdir(exist_ok=True)
    db_path = test_data_dir / f"test-{uuid.uuid4().hex}.db"
    settings = Settings(
        app_name="PolKhol Test",
        database_url=f"sqlite:///{db_path}",
        secret_key="test-secret-key",
        admin_email="owner@example.com",
        session_cookie_name="polkhol_session",
        csrf_cookie_name="polkhol_csrf",
        session_ttl_hours=24,
        max_message_length=2000,
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client

    if db_module.engine is not None:
        db_module.engine.dispose()
    if db_path.exists():
        db_path.unlink()
    if test_data_dir.exists() and not any(test_data_dir.iterdir()):
        shutil.rmtree(test_data_dir)