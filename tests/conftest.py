"""
Test configuration for ferm.

Database strategy: pytest-env sets DATABASE_URL=sqlite:///./test.db before
any import, so the app's own engine points at the test database from the start.
No patching needed — the app behaves exactly as in production.

Auth strategy:
- Most tests use dependency overrides (require_user/editor/admin → fake user).
  Fast, focused, no login round-trip needed.
- test_auth.py uses real login to test the actual auth flow end-to-end.
"""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ── Test database (set via pytest-env in pyproject.toml) ──────────────────
# DATABASE_URL=sqlite:///./test.db is already in the environment when this
# module is imported, so app.config.settings picks it up automatically.

from app.database import Base, get_db, engine as app_engine
from app.main import app
from app.models import *  # noqa: F401,F403 — registers all models with Base
from app.auth import hash_password, require_user, require_editor, require_admin
from app.models.user import User, UserRole

# Session bound to the same engine the app uses (test.db via env var)
TestingSession = sessionmaker(bind=app_engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


# ── Fake users for dependency injection ────────────────────────────────────

fake_admin = User(
    id=1, username="admin", email="admin@ferm.local",
    hashed_password="x", role=UserRole.admin, is_active=True,
)
fake_editor = User(
    id=2, username="editor", email="editor@ferm.local",
    hashed_password="x", role=UserRole.editor, is_active=True,
)
fake_viewer = User(
    id=3, username="viewer", email="viewer@ferm.local",
    hashed_password="x", role=UserRole.viewer, is_active=True,
)


# ── DB lifecycle ───────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test, drop after. Keeps tests isolated."""
    Base.metadata.create_all(bind=app_engine)
    yield
    Base.metadata.drop_all(bind=app_engine)


# ── Base client (no auth) ──────────────────────────────────────────────────

@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, follow_redirects=False) as c:
        yield c
    app.dependency_overrides.clear()


# ── Authenticated clients via dependency override ──────────────────────────

@pytest.fixture
def auth_client(client):
    """Admin client — uses dependency override, no login needed."""
    app.dependency_overrides[require_user]   = lambda: fake_admin
    app.dependency_overrides[require_editor] = lambda: fake_admin
    app.dependency_overrides[require_admin]  = lambda: fake_admin
    yield client
    # clear only auth overrides; get_db cleared by client fixture
    for dep in [require_user, require_editor, require_admin]:
        app.dependency_overrides.pop(dep, None)


@pytest.fixture
def editor_client(client):
    """Editor client — can create/edit but not admin actions."""
    app.dependency_overrides[require_user]   = lambda: fake_editor
    app.dependency_overrides[require_editor] = lambda: fake_editor
    app.dependency_overrides[require_admin]  = _forbidden
    yield client
    for dep in [require_user, require_editor, require_admin]:
        app.dependency_overrides.pop(dep, None)


@pytest.fixture
def viewer_client(client):
    """Viewer client — read only."""
    app.dependency_overrides[require_user]   = lambda: fake_viewer
    app.dependency_overrides[require_editor] = _forbidden
    app.dependency_overrides[require_admin]  = _forbidden
    yield client
    for dep in [require_user, require_editor, require_admin]:
        app.dependency_overrides.pop(dep, None)


def _forbidden():
    from fastapi import HTTPException, status
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


# ── DB fixture for direct inserts ──────────────────────────────────────────

@pytest.fixture
def db():
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seeded_db(db):
    """
    Seed lookup tables + real users for tests that need them
    (primarily test_auth.py which tests the actual login flow).
    """
    from app.models.lookup import (
        Category, Status, CutSize, Tag,
        SmellDescriptor, VisualDescriptor,
        VesselType, VesselMaterial,
    )

    db.add_all([
        Category(name="LAB",      description="Lactic acid bacteria"),
        Category(name="Kombucha", description="SCOBY-based"),
        Status(name="active",  color="#4ec9b0"),
        Status(name="ready",   color="#b5cea8"),
        Status(name="failed",  color="#f44747"),
        Status(name="stasis",  color="#c8a96e"),
        CutSize(name="Thinly Shredded",   description="Fine strips"),
        CutSize(name="Coarsely Shredded", description="Thick strips"),
        CutSize(name="Whole",             description="Intact"),
        Tag(name="Vegetable"),
        Tag(name="Liquid"),
        Tag(name="Herb"),
        SmellDescriptor(name="Acidic"),
        SmellDescriptor(name="Funky"),
        VisualDescriptor(name="Cloudy"),
        VisualDescriptor(name="Clear"),
        VesselType(name="Jar"),
        VesselType(name="Crock"),
        VesselMaterial(name="Glass"),
        VesselMaterial(name="Ceramic"),
        User(
            username="admin", email="admin@ferm.local",
            hashed_password=hash_password("adminpass"),
            role=UserRole.admin, is_active=True,
        ),
        User(
            username="editor", email="editor@ferm.local",
            hashed_password=hash_password("editorpass"),
            role=UserRole.editor, is_active=True,
        ),
        User(
            username="viewer", email="viewer@ferm.local",
            hashed_password=hash_password("viewerpass"),
            role=UserRole.viewer, is_active=True,
        ),
    ])
    db.commit()
    return db


# ── Real-login clients for auth tests ──────────────────────────────────────

@pytest.fixture
def real_auth_client(client, seeded_db):
    """Uses actual POST /login — for testing the auth flow itself."""
    resp = client.post("/login", data={"username": "admin", "password": "adminpass"})
    assert resp.status_code in (302, 303), f"Login failed: {resp.status_code}"
    return client


@pytest.fixture
def real_viewer_client(client, seeded_db):
    resp = client.post("/login", data={"username": "viewer", "password": "viewerpass"})
    assert resp.status_code in (302, 303)
    return client


# ── DB helpers ─────────────────────────────────────────────────────────────

def make_ferment(db, name="Test Ferment", category_name="LAB",
                 status_name="active", created_by_id=None):
    from app.models.lookup import Category, Status
    from app.models.ferment import Ferment
    cat = db.query(Category).filter_by(name=category_name).first()
    st  = db.query(Status).filter_by(name=status_name).first()
    f = Ferment(
        name=name,
        category_id=cat.id if cat else None,
        status_id=st.id if st else None,
        created_by_id=created_by_id,
    )
    db.add(f); db.flush()
    return f


def make_batch(db, ferment_id, lot_code="TEST-001", stage=1, batch_number=1):
    from app.models.ferment import Batch
    b = Batch(ferment_id=ferment_id, lot_code=lot_code,
              stage=stage, batch_number=batch_number)
    db.add(b); db.flush()
    return b


def make_ingredient(db, name="Cabbage", cut_size_name="Thinly Shredded"):
    from app.models.lookup import CutSize
    from app.models.ingredient import Ingredient
    cs = db.query(CutSize).filter_by(name=cut_size_name).first()
    ing = Ingredient(name=name, cut_size_id=cs.id if cs else None, is_active=True)
    db.add(ing); db.flush()
    return ing