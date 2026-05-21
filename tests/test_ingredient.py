"""Ingredients — CRUD, tag assignment, deletion protection."""
from tests.conftest import make_ingredient, make_ferment, make_batch


def test_ingredients_list(auth_client):
    resp = auth_client.get("/ingredients")
    assert resp.status_code == 200


def test_create_ingredient(auth_client, db):
    from app.models.ingredient import Ingredient
    from app.models.lookup import CutSize
    db.add(CutSize(name="Thinly Shredded"))
    db.commit()
    cs = db.query(CutSize).filter_by(name="Thinly Shredded").first()
    resp = auth_client.post("/ingredients/new", data={
        "name": "White Cabbage", "cut_size_id": str(cs.id),
    })
    assert resp.status_code in (302, 303)
    ing = db.query(Ingredient).filter_by(name="White Cabbage").first()
    assert ing is not None
    assert ing.cut_size_id == cs.id


def test_create_ingredient_with_tags(auth_client, db):
    from app.models.ingredient import Ingredient
    from app.models.lookup import Tag
    db.add(Tag(name="Vegetable"))
    db.commit()
    tag = db.query(Tag).filter_by(name="Vegetable").first()
    resp = auth_client.post("/ingredients/new", data={
        "name": "Carrot", "tag_ids": str(tag.id),
    })
    assert resp.status_code in (302, 303)
    ing = db.query(Ingredient).filter_by(name="Carrot").first()
    assert ing is not None
    assert any(t.id == tag.id for t in ing.tags)


def test_duplicate_ingredient_rejected(auth_client, db):
    from app.models.lookup import CutSize
    db.add(CutSize(name="Thinly Shredded"))
    db.commit()
    cs = db.query(CutSize).filter_by(name="Thinly Shredded").first()
    auth_client.post("/ingredients/new", data={"name": "Cabbage", "cut_size_id": str(cs.id)})
    resp = auth_client.post("/ingredients/new", data={"name": "Cabbage", "cut_size_id": str(cs.id)})
    assert resp.status_code == 422


def test_same_name_different_cut_size_allowed(auth_client, db):
    from app.models.ingredient import Ingredient
    from app.models.lookup import CutSize
    db.add_all([CutSize(name="Thinly Shredded"), CutSize(name="Coarsely Shredded")])
    db.commit()
    cs1 = db.query(CutSize).filter_by(name="Thinly Shredded").first()
    cs2 = db.query(CutSize).filter_by(name="Coarsely Shredded").first()
    auth_client.post("/ingredients/new", data={"name": "Cabbage", "cut_size_id": str(cs1.id)})
    resp = auth_client.post("/ingredients/new", data={"name": "Cabbage", "cut_size_id": str(cs2.id)})
    assert resp.status_code in (302, 303)
    assert db.query(Ingredient).filter_by(name="Cabbage", is_active=True).count() == 2


def test_edit_ingredient_propagates(auth_client, db):
    from app.models.ingredient import Ingredient
    ing = make_ingredient(db, "Old Name")
    db.commit()
    resp = auth_client.post(f"/ingredients/{ing.id}/edit", data={"name": "New Name"})
    assert resp.status_code in (302, 303)
    db.expire(ing)
    assert ing.name == "New Name"


def test_delete_unused_ingredient(auth_client, db):
    from app.models.ingredient import Ingredient
    ing = make_ingredient(db, "Unused Herb")
    db.commit()
    resp = auth_client.post(f"/ingredients/{ing.id}/delete")
    assert resp.status_code in (302, 303)
    db.expire(ing)
    # Soft delete — marks inactive rather than removing
    assert ing.is_active is False


def test_delete_in_use_ingredient_blocked(auth_client, db):
    from app.models.ingredient import Ingredient
    from app.models.ferment import BatchIngredient
    f = make_ferment(db, "Sauerkraut")
    b = make_batch(db, f.id, lot_code="SKR-T01")
    ing = make_ingredient(db, "Protected Cabbage")
    db.add(BatchIngredient(batch_id=b.id, ingredient_id=ing.id, quantity=500))
    db.commit()

    resp = auth_client.post(f"/ingredients/{ing.id}/delete")
    assert resp.status_code in (302, 303)
    still = db.query(Ingredient).filter_by(id=ing.id).first()
    assert still is not None
    assert still.is_active is True


def test_viewer_cannot_delete_ingredient(viewer_client, db):
    ing = make_ingredient(db, "Safe Ingredient")
    db.commit()
    resp = viewer_client.post(f"/ingredients/{ing.id}/delete")
    assert resp.status_code in (302, 303, 403)