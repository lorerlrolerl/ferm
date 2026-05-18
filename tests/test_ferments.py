"""Tests for ferment and batch creation."""
from app.models.ferment import Ferment, Batch


def test_ferments_list(auth_client):
    resp = auth_client.get("/ferments")
    assert resp.status_code == 200


def test_create_ferment(auth_client, seeded_db):
    from app.models.lookup import Category, Status
    cat = seeded_db.query(Category).first()
    st  = seeded_db.query(Status).first()

    resp = auth_client.post("/ferments/new", data={
        "name": "House Sauerkraut",
        "category_id": cat.id,
        "status_id": st.id,
        "batch_stage": 1,
        "batch_started_at": "2025-05-01",
    })
    assert resp.status_code in (302, 303)
    ferment = seeded_db.query(Ferment).filter_by(name="House Sauerkraut").first()
    assert ferment is not None
    assert len(ferment.batches) == 1


def test_lot_code_uniqueness(auth_client, seeded_db):
    from app.models.lookup import Category, Status
    cat = seeded_db.query(Category).first()
    st  = seeded_db.query(Status).first()

    # Create first ferment with a specific lot code
    auth_client.post("/ferments/new", data={
        "name": "Ferment A",
        "category_id": cat.id,
        "status_id": st.id,
        "batch_stage": 1,
        "batch_lot_code": "UNIQUE-LOT-001",
    })

    # Try to create another with the same lot code
    resp = auth_client.post("/ferments/new", data={
        "name": "Ferment B",
        "category_id": cat.id,
        "status_id": st.id,
        "batch_stage": 1,
        "batch_lot_code": "UNIQUE-LOT-001",
    })
    assert resp.status_code == 422


def test_ferment_detail(auth_client, seeded_db):
    from app.models.lookup import Category, Status
    cat = seeded_db.query(Category).first()
    st  = seeded_db.query(Status).first()
    ferment = Ferment(name="Detail Test", category_id=cat.id, status_id=st.id)
    seeded_db.add(ferment)
    seeded_db.flush()
    batch = Batch(ferment_id=ferment.id, batch_number=1, stage=1, lot_code="DT-001")
    seeded_db.add(batch)
    seeded_db.commit()

    resp = auth_client.get(f"/ferments/{ferment.id}")
    assert resp.status_code == 200
    assert b"Detail Test" in resp.content


def test_viewer_cannot_create_ferment(client, seeded_db):
    from app.models.user import User, UserRole
    from app.auth import hash_password
    viewer = User(
        username="viewer", email="v@ferm.local",
        hashed_password=hash_password("viewpass"),
        role=UserRole.viewer, is_active=True,
    )
    seeded_db.add(viewer)
    seeded_db.commit()

    client.post("/login", data={"username": "viewer", "password": "viewpass"})
    resp = client.post("/ferments/new", data={"name": "Sneaky Ferment", "batch_stage": 1})
    # Should be forbidden
    assert resp.status_code in (302, 303, 403)