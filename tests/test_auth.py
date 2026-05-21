"""
Authentication tests — uses real login flow (not dependency override)
to actually test the auth mechanism end-to-end.
"""


def test_login_page_renders(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"ferm" in resp.content


def test_login_success_redirects(client, seeded_db):
    resp = client.post("/login", data={"username": "admin", "password": "adminpass"})
    assert resp.status_code in (302, 303)
    assert resp.headers["location"] == "/"


def test_login_wrong_password(client, seeded_db):
    resp = client.post("/login", data={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user(client, seeded_db):
    resp = client.post("/login", data={"username": "ghost", "password": "x"})
    assert resp.status_code == 401


def test_login_inactive_user(client, seeded_db):
    from app.models.user import User
    user = seeded_db.query(User).filter_by(username="editor").first()
    user.is_active = False
    seeded_db.commit()
    resp = client.post("/login", data={"username": "editor", "password": "editorpass"})
    assert resp.status_code == 401


def test_logout_clears_session(real_auth_client):
    resp = real_auth_client.get("/logout")
    assert resp.status_code in (302, 303)
    assert resp.headers["location"] == "/login"


def test_dashboard_redirects_unauthenticated(client):
    resp = client.get("/")
    assert resp.status_code in (302, 303)
    assert "/login" in resp.headers["location"]


def test_ferments_redirects_unauthenticated(client):
    resp = client.get("/ferments")
    assert resp.status_code in (302, 303)


def test_settings_requires_admin(editor_client):
    resp = editor_client.get("/settings")
    assert resp.status_code in (302, 303, 403)


def test_users_requires_admin(editor_client):
    resp = editor_client.get("/users")
    assert resp.status_code in (302, 303, 403)


def test_viewer_cannot_create_ferment(viewer_client):
    resp = viewer_client.post("/ferments/new", data={"name": "Sneaky", "batch_stage": "1"})
    assert resp.status_code in (302, 303, 403)


def test_viewer_cannot_create_ingredient(viewer_client):
    resp = viewer_client.post("/ingredients/new", data={"name": "Cabbage"})
    assert resp.status_code in (302, 303, 403)


def test_change_password_wrong_current(real_auth_client):
    resp = real_auth_client.post("/users/me/password", data={
        "current_password": "wrong",
        "new_password": "newpass123",
        "confirm_password": "newpass123",
    })
    assert resp.status_code == 422


def test_change_password_mismatch(real_auth_client):
    resp = real_auth_client.post("/users/me/password", data={
        "current_password": "adminpass",
        "new_password": "newpass123",
        "confirm_password": "different123",
    })
    assert resp.status_code == 422


def test_change_password_success(real_auth_client):
    resp = real_auth_client.post("/users/me/password", data={
        "current_password": "adminpass",
        "new_password": "newpass123",
        "confirm_password": "newpass123",
    })
    assert resp.status_code == 200