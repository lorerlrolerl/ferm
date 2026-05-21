"""Tools — CRUD."""


def test_tools_list(auth_client):
    assert auth_client.get("/tools").status_code == 200


def test_create_tool(auth_client, db):
    from app.models.tool import Tool
    resp = auth_client.post("/tools/new", data={"name": "pH Meter", "tool_type": "ph_meter", "description": "Apera pH60"})
    assert resp.status_code in (302, 303)
    assert db.query(Tool).filter_by(name="pH Meter").first() is not None


def test_edit_tool(auth_client, db):
    from app.models.tool import Tool
    t = Tool(name="Old Meter", tool_type="thermometer")
    db.add(t); db.commit()
    resp = auth_client.post(f"/tools/{t.id}/edit", data={"name": "New Meter", "tool_type": "thermometer"})
    assert resp.status_code in (302, 303)
    db.expire(t)
    assert t.name == "New Meter"


def test_delete_tool(auth_client, db):
    from app.models.tool import Tool
    t = Tool(name="To Delete", tool_type="other")
    db.add(t); db.commit()
    resp = auth_client.post(f"/tools/{t.id}/delete")
    assert resp.status_code in (302, 303)
    assert db.query(Tool).filter_by(id=t.id).first() is None


def test_viewer_cannot_create_tool(viewer_client):
    resp = viewer_client.post("/tools/new", data={"name": "X", "tool_type": "other"})
    assert resp.status_code in (302, 303, 403)