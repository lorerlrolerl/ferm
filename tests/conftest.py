"""
Test configuration and fixtures.
Uses a separate in-memory SQLite database — never touches ferm.db.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import *  # noqa: F401,F403 — registers all models
from app.auth import hash_password

TEST_DB_URL = "sqlite:///:memory:"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, follow_redirects=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_db(db):
    """Seed lookup tables and an admin user."""
    from app.models.lookup import Category, Status, CutSize, Tag
    from app.models.user import User, UserRole

    db.add_all([
        Category(name="LAB"),
        Category(name="Kombucha"),
        Status(name="active", color="#4ec9b0"),
        Status(name="ready",  color="#b5cea8"),
        Status(name="failed", color="#f44747"),
        CutSize(name="Thinly Shredded"),
        CutSize(name="Liquid"),
        Tag(name="Vegetable"),
        Tag(name="Liquid"),
    ])
    admin = User(
        username="admin",
        email="admin@ferm.local",
        hashed_password=hash_password("testpass"),
        role=UserRole.admin,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    return db


@pytest.fixture
def auth_client(client, seeded_db):
    """Client with admin session cookie set."""
    resp = client.post("/login", data={"username": "admin", "password": "testpass"})
    assert resp.status_code in (302, 303), f"Login failed: {resp.status_code}"
    return client