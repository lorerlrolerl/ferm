"""Dashboard — renders correctly with and without data."""
from tests.conftest import make_ferment, make_batch


def test_dashboard_renders(auth_client):
    assert auth_client.get("/").status_code == 200


def test_dashboard_shows_active_ferments(auth_client, db):
    from app.models.lookup import Category, Status
    db.add_all([Category(name="LAB"), Status(name="active", color="#4ec9b0"), Status(name="stasis", color="#c8a96e")])
    db.commit()
    make_ferment(db, "Sauerkraut",  status_name="active"); db.commit()
    make_ferment(db, "Kombucha",    status_name="active"); db.commit()
    make_ferment(db, "SCOBY Hotel", status_name="stasis"); db.commit()
    resp = auth_client.get("/")
    assert resp.status_code == 200


def test_dashboard_empty_state(auth_client):
    resp = auth_client.get("/")
    assert resp.status_code == 200
    assert b"ferm" in resp.content


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["app"] == "ferm"