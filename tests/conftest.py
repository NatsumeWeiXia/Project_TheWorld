import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

os.environ["TW_DATABASE_URL"] = "postgresql+psycopg://akyuu:akyuu@192.168.1.6:5432/gensokyo"

from src.app.infra.db.base import Base
from src.app.infra.db.session import engine
from src.app.main import app


@pytest.fixture(autouse=True)
def reset_db():
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS ontology_binding CASCADE"))
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def headers():
    return {"X-Tenant-Id": "tenant-a", "Authorization": "Bearer test-token"}
