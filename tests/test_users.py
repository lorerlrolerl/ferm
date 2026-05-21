"""User management — admin CRUD, deactivation, deletion protection."""
from app.models.user import User, UserRole
from app.auth import hash_password


def _seed_users(db):
    db.add_all([
        User(username="admin",  email="a@ferm.local", hashed_password=hash_password("adminpass"),  role=UserRole.admin,  is_active=True),
        User(username="editor", email="e@ferm.local", hashed_password=hash_password("editorpass"), role=UserRole.editor, is_active=True),
        User(username="viewer", email="v@ferm.local", hashed_password=hash_password("viewerpass"), role=UserRole.viewer, is_active=True),
    ])
    db.commit()


def test_users_list_accessible_by_admin(auth_client):
    assert auth_client.get("/users").status_code == 200


def test_users_list_blocked_for_editor(editor_client):
    assert editor_client.get("/users").status_code in (302, 303, 403)


def test_create_user(auth_client, db):
    resp = auth_client.post("/users/new", data={
        "username": "newuser", "email": "new@ferm.local",
        "password": "password123", "role": "viewer",
    })
    assert resp.status_code in (302, 303)
    assert db.query(User).filter_by(username="newuser").first() is not None


def test_create_user_duplicate_username(auth_client, db):
    _seed_users(db)
    resp = auth_client.post("/users/new", data={
        "username": "admin", "email": "other@ferm.local",
        "password": "password123", "role": "viewer",
    })
    assert resp.status_code == 422


def test_create_user_short_password(auth_client):
    resp = auth_client.post("/users/new", data={
        "username": "shortpass", "email": "sp@ferm.local",
        "password": "short", "role": "viewer",
    })
    assert resp.status_code == 422


def test_deactivate_user(auth_client, db):
    _seed_users(db)
    u = db.query(User).filter_by(username="viewer").first()
    resp = auth_client.post(f"/users/{u.id}/deactivate")
    assert resp.status_code in (302, 303)
    db.expire(u)
    assert u.is_active is False


def test_cannot_deactivate_self(auth_client, db):
    # fake_admin has id=1, seed a real user with id matching
    u = User(id=1, username="admin2", email="a2@ferm.local",
             hashed_password="x", role=UserRole.admin, is_active=True)
    db.add(u); db.commit()
    resp = auth_client.post(f"/users/{u.id}/deactivate")
    # Should redirect with error
    assert resp.status_code in (302, 303)
    location = resp.headers.get("location", "")
    assert "error" in location or db.query(User).filter_by(id=u.id, is_active=True).first() is not None


def test_delete_user_no_content(auth_client, db):
    # Seed admin first to occupy id=1 (matching fake_admin)
    db.add(User(username="admin_real", email="ar@ferm.local",
                hashed_password="x", role=UserRole.admin, is_active=True))
    db.flush()
    u = User(username="todelete", email="td@ferm.local",
             hashed_password="x", role=UserRole.viewer, is_active=True)
    db.add(u); db.commit()
    uid = u.id
    assert uid != 1, "User id collided with fake_admin id"
    resp = auth_client.post(f"/users/{uid}/delete")
    assert resp.status_code in (302, 303)
    assert db.query(User).filter_by(id=uid).first() is None


def test_delete_user_with_content_blocked(auth_client, db):
    from tests.conftest import make_ferment
    from app.models.lookup import Category, Status
    db.add_all([Category(name="LAB"), Status(name="active", color="#4ec9b0")])
    u = User(username="creator", email="c@ferm.local",
             hashed_password="x", role=UserRole.editor, is_active=True)
    db.add(u); db.commit()
    make_ferment(db, "Creator's Ferment", created_by_id=u.id)
    db.commit()
    resp = auth_client.post(f"/users/{u.id}/delete")
    assert resp.status_code in (302, 303)
    assert db.query(User).filter_by(id=u.id).first() is not None


def test_edit_user_role(auth_client, db):
    # Seed a real admin first so it gets id=1 (matching fake_admin)
    # then our test user gets a different id
    real_admin = User(username="admin_real", email="ar@ferm.local",
                      hashed_password="x", role=UserRole.admin, is_active=True)
    db.add(real_admin); db.flush()
    u = User(username="roletest", email="rt@ferm.local",
             hashed_password="x", role=UserRole.viewer, is_active=True)
    db.add(u); db.commit()
    assert u.id != 1, "Test user id collided with fake_admin"
    resp = auth_client.post(f"/users/{u.id}/edit", data={
        "email": "rt@ferm.local",
        "role": "editor",
        "is_active": "true",
    })
    assert resp.status_code in (302, 303)
    db.expire(u)
    assert u.role == UserRole.editor


def test_user_detail_page(auth_client, db):
    u = User(username="detailtest", email="dt@ferm.local",
             hashed_password="x", role=UserRole.editor, is_active=True)
    db.add(u); db.commit()
    resp = auth_client.get(f"/users/{u.id}")
    assert resp.status_code == 200
    assert b"detailtest" in resp.content