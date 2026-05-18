"""Tests for authentication."""


def test_login_page_renders(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"ferm" in resp.content


def test_login_success(client, seeded_db):
    resp = client.post("/login", data={"username": "admin", "password": "testpass"})
    assert resp.status_code in (302, 303)
    assert resp.headers["location"] == "/"


def test_login_wrong_password(client, seeded_db):
    resp = client.post("/login", data={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401
    assert b"Invalid" in resp.content


def test_login_unknown_user(client, seeded_db):
    resp = client.post("/login", data={"username": "nobody", "password": "x"})
    assert resp.status_code == 401


def test_logout_clears_session(auth_client):
    resp = auth_client.get("/logout")
    assert resp.status_code in (302, 303)
    assert resp.headers["location"] == "/login"


def test_dashboard_requires_auth(client):
    resp = client.get("/")
    assert resp.status_code in (302, 303)
    assert "/login" in resp.headers["location"]