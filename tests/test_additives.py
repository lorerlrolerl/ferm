"""Additives — CRUD and deletion protection."""
from app.models.additive import AdditiveType


def test_additives_list(auth_client):
    resp = auth_client.get("/additives")
    assert resp.status_code == 200


def test_create_additive(auth_client, db):
    from app.models.additive import Additive
    resp = auth_client.post("/additives/new", data={"name": "Himalayan Salt", "additive_type": "salt"})
    assert resp.status_code in (302, 303)
    assert db.query(Additive).filter_by(name="Himalayan Salt").first() is not None


def test_duplicate_additive_rejected(auth_client):
    auth_client.post("/additives/new", data={"name": "Salt", "additive_type": "salt"})
    resp = auth_client.post("/additives/new", data={"name": "Salt", "additive_type": "salt"})
    assert resp.status_code == 422


def test_same_name_different_type_allowed(auth_client, db):
    from app.models.additive import Additive
    auth_client.post("/additives/new", data={"name": "Honey", "additive_type": "sugar"})
    resp = auth_client.post("/additives/new", data={"name": "Honey", "additive_type": "other"})
    assert resp.status_code in (302, 303)
    assert db.query(Additive).filter_by(name="Honey").count() == 2


def test_delete_unused_additive(auth_client, db):
    from app.models.additive import Additive
    a = Additive(name="Temp", additive_type=AdditiveType.salt)
    db.add(a); db.commit()
    resp = auth_client.post(f"/additives/{a.id}/delete")
    assert resp.status_code in (302, 303)
    assert db.query(Additive).filter_by(id=a.id).first() is None


def test_delete_in_use_additive_blocked(auth_client, db):
    from app.models.additive import Additive
    from app.models.ferment import BatchAdditive
    from tests.conftest import make_ferment, make_batch
    f = make_ferment(db); b = make_batch(db, f.id, lot_code="ADD-T01")
    a = Additive(name="Used Salt", additive_type=AdditiveType.salt)
    db.add(a); db.flush()
    db.add(BatchAdditive(batch_id=b.id, additive_id=a.id, quantity=20))
    db.commit()
    resp = auth_client.post(f"/additives/{a.id}/delete")
    assert resp.status_code in (302, 303)
    assert db.query(Additive).filter_by(id=a.id).first() is not None


def test_edit_additive(auth_client, db):
    from app.models.additive import Additive
    a = Additive(name="Old Salt", additive_type=AdditiveType.salt)
    db.add(a); db.commit()
    resp = auth_client.post(f"/additives/{a.id}/edit", data={"name": "New Salt", "additive_type": "salt"})
    assert resp.status_code in (302, 303)
    db.expire(a)
    assert a.name == "New Salt"