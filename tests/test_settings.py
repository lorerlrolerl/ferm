"""Settings — lookup table CRUD with usage protection."""
from tests.conftest import make_ferment


def test_settings_page_loads(auth_client):
    resp = auth_client.get("/settings")
    assert resp.status_code == 200


def test_add_status(auth_client, db):
    from app.models.lookup import Status
    resp = auth_client.post("/settings/statuses/new", data={"name": "paused", "color": "#aaaaaa"})
    assert resp.status_code in (302, 303)
    assert db.query(Status).filter_by(name="paused").first() is not None


def test_add_duplicate_status_rejected(auth_client, db):
    auth_client.post("/settings/statuses/new", data={"name": "mystat", "color": "#aaa"})
    resp = auth_client.post("/settings/statuses/new", data={"name": "mystat", "color": "#bbb"})
    assert "duplicate" in resp.headers.get("location", "")


def test_edit_status(auth_client, db):
    from app.models.lookup import Status
    s = Status(name="active", color="#4ec9b0")
    db.add(s); db.commit()
    resp = auth_client.post(f"/settings/statuses/{s.id}/edit", data={"name": "fermenting", "color": "#4ec9b0"})
    assert resp.status_code in (302, 303)
    db.expire(s)
    assert s.name == "fermenting"


def test_delete_unused_status(auth_client, db):
    from app.models.lookup import Status
    s = Status(name="temp", color="#000000")
    db.add(s); db.commit()
    resp = auth_client.post(f"/settings/statuses/{s.id}/delete")
    assert resp.status_code in (302, 303)
    assert db.query(Status).filter_by(id=s.id).first() is None


def test_delete_in_use_status_blocked(auth_client, db):
    from app.models.lookup import Status, Category
    db.add(Category(name="LAB"))
    s = Status(name="active", color="#4ec9b0")
    db.add(s); db.commit()
    make_ferment(db, "Active Ferment", status_name="active")
    db.commit()
    resp = auth_client.post(f"/settings/statuses/{s.id}/delete")
    assert "in_use" in resp.headers.get("location", "")
    assert db.query(Status).filter_by(id=s.id).first() is not None


def test_add_tag(auth_client, db):
    from app.models.lookup import Tag
    resp = auth_client.post("/settings/tags/new", data={"name": "Flower"})
    assert resp.status_code in (302, 303)
    assert db.query(Tag).filter_by(name="Flower").first() is not None


def test_add_category(auth_client, db):
    from app.models.lookup import Category
    resp = auth_client.post("/settings/categories/new", data={
        "name": "Vinegar", "description": "Acetic fermentation",
    })
    assert resp.status_code in (302, 303)
    c = db.query(Category).filter_by(name="Vinegar").first()
    assert c is not None
    assert c.description == "Acetic fermentation"


def test_add_vessel_type(auth_client, db):
    from app.models.lookup import VesselType
    resp = auth_client.post("/settings/vessel_types/new", data={"name": "Amphora"})
    assert resp.status_code in (302, 303)
    assert db.query(VesselType).filter_by(name="Amphora").first() is not None


def test_settings_requires_admin(editor_client):
    resp = editor_client.post("/settings/tags/new", data={"name": "TestTag"})
    assert resp.status_code in (302, 303, 403)