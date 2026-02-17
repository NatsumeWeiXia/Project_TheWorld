import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

# Force tests to use an isolated local SQLite database.
# This prevents any mutation to shared/dev/prod Postgres instances.
test_db_dir = Path(".runtime")
test_db_dir.mkdir(parents=True, exist_ok=True)
test_db_path = test_db_dir / f"pytest_{os.getpid()}_{uuid4().hex}.db"
os.environ["TW_DATABASE_URL"] = f"sqlite+pysqlite:///{test_db_path.as_posix()}"

from src.app.infra.db.base import Base
from src.app.infra.db.session import engine
from src.app.main import app


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def headers():
    return {"X-Tenant-Id": "tenant-a", "Authorization": "Bearer test-token"}


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db_file():
    yield
    try:
        test_db_path.unlink(missing_ok=True)
    except OSError:
        # Ignore cleanup errors on locked files in CI/Windows.
        pass
