import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as app_db
import app.models  # noqa: F401  (registers tables on Base.metadata)
import app.workers.parse_tasks as parse_tasks_module
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    """in-memory sqlite standing in for neon — models use portable types."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def _sessions_to_test_db(db_session, monkeypatch):
    """middleware and the inline parse open their own sessions — point them
    at sqlite. a fresh session per call: closing one must not detach another
    caller's instances (StaticPool shares the single sqlite connection)."""
    factory = sessionmaker(bind=db_session.get_bind(), autoflush=False, autocommit=False)
    monkeypatch.setattr(app_db, "SessionLocal", factory)
    monkeypatch.setattr(parse_tasks_module, "SessionLocal", factory)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
