"""Tests for ingredient CRUD and deletion protection."""
from app.models.ingredient import Ingredient
from app.models.ferment import Ferment, Batch, BatchIngredient


def test_ingredient_list(auth_client):
    resp = auth_client.get("/ingredients")
    assert resp.status_code == 200


def test_create_ingredient(auth_client, seeded_db):
    resp = auth_client.post("/ingredients/new", data={
        "name": "White Cabbage",
        "cut_size_id": seeded_db.query(__import__('app.models.lookup', fromlist=['CutSize']).CutSize).first().id,
    })
    assert resp.status_code in (302, 303)
    ing = seeded_db.query(Ingredient).filter_by(name="White Cabbage").first()
    assert ing is not None


def test_duplicate_ingredient_rejected(auth_client, seeded_db):
    from app.models.lookup import CutSize
    cs = seeded_db.query(CutSize).filter_by(name="Thinly Shredded").first()
    # Create first
    auth_client.post("/ingredients/new", data={"name": "Cabbage", "cut_size_id": cs.id})
    # Create duplicate
    resp = auth_client.post("/ingredients/new", data={"name": "Cabbage", "cut_size_id": cs.id})
    assert resp.status_code == 422


def test_delete_unused_ingredient(auth_client, seeded_db):
    from app.models.lookup import CutSize
    cs = seeded_db.query(CutSize).first()
    ing = Ingredient(name="Temp", cut_size_id=cs.id)
    seeded_db.add(ing)
    seeded_db.commit()

    resp = auth_client.post(f"/ingredients/{ing.id}/delete")
    assert resp.status_code in (302, 303)
    refreshed = seeded_db.query(Ingredient).filter_by(id=ing.id).first()
    assert refreshed is None or refreshed.is_active is False


def test_delete_in_use_ingredient_blocked(auth_client, seeded_db):
    from app.models.lookup import CutSize, Status, Category
    cs  = seeded_db.query(CutSize).first()
    cat = seeded_db.query(Category).first()
    st  = seeded_db.query(Status).first()

    ing = Ingredient(name="InUse", cut_size_id=cs.id)
    seeded_db.add(ing)
    seeded_db.flush()

    ferment = Ferment(name="Test Ferment", category_id=cat.id, status_id=st.id)
    seeded_db.add(ferment)
    seeded_db.flush()

    batch = Batch(ferment_id=ferment.id, batch_number=1, stage=1, lot_code="TEST-001")
    seeded_db.add(batch)
    seeded_db.flush()

    seeded_db.add(BatchIngredient(batch_id=batch.id, ingredient_id=ing.id, quantity=500))
    seeded_db.commit()

    resp = auth_client.post(f"/ingredients/{ing.id}/delete")
    # Should redirect with error, not actually delete
    assert resp.status_code in (302, 303)
    still_there = seeded_db.query(Ingredient).filter_by(id=ing.id).first()
    assert still_there is not None
    assert still_there.is_active is True