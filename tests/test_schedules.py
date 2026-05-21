"""Schedules — create, complete, recalculation."""
from datetime import datetime
from tests.conftest import make_ferment, make_batch


def test_schedules_list(auth_client):
    resp = auth_client.get("/schedules")
    assert resp.status_code == 200


def test_create_schedule_for_ferment(auth_client, db):
    from app.models.schedule import Schedule
    f = make_ferment(db); db.commit()
    resp = auth_client.post("/schedules/new", data={
        "name": "Feed starter", "target_type": "ferment",
        "target_id": str(f.id), "interval_days": "7",
        "next_due_at": "2025-05-20T09:00",
    })
    assert resp.status_code in (302, 303)
    s = db.query(Schedule).filter_by(name="Feed starter").first()
    assert s is not None
    assert s.interval_days == 7


def test_complete_schedule_recalculates_from_actual(auth_client, db):
    from app.models.schedule import Schedule, ScheduleEvent
    f = make_ferment(db); db.commit()
    s = Schedule(name="Feed", target_type="ferment", target_id=f.id,
                 interval_days=7, next_due_at=datetime(2025, 5, 10, 9, 0), is_active=True)
    db.add(s); db.commit()

    auth_client.post(f"/schedules/{s.id}/complete", data={
        "completed_at": "2025-05-12T09:00", "notes": "Fed late",
    })
    db.expire(s)
    # Completed 12 May + 7 days = 19 May
    assert s.next_due_at == datetime(2025, 5, 19, 9, 0)
    event = db.query(ScheduleEvent).filter_by(schedule_id=s.id).first()
    assert event.was_late is True


def test_complete_one_off_deactivates(auth_client, db):
    from app.models.schedule import Schedule
    f = make_ferment(db); db.commit()
    s = Schedule(name="One time", target_type="ferment", target_id=f.id,
                 interval_days=None, next_due_at=datetime(2025, 5, 10), is_active=True)
    db.add(s); db.commit()
    auth_client.post(f"/schedules/{s.id}/complete", data={"completed_at": "2025-05-10T10:00"})
    db.expire(s)
    assert s.is_active is False


def test_schedule_for_tool(auth_client, db):
    from app.models.schedule import Schedule
    from app.models.tool import Tool
    t = Tool(name="pH Meter", tool_type="ph_meter")
    db.add(t); db.commit()
    resp = auth_client.post("/schedules/new", data={
        "name": "Calibrate", "target_type": "tool",
        "target_id": str(t.id), "interval_days": "30",
        "next_due_at": "2025-06-01T09:00",
    })
    assert resp.status_code in (302, 303)
    s = db.query(Schedule).filter_by(name="Calibrate").first()
    assert s.target_type == "tool"


def test_delete_schedule(auth_client, db):
    from app.models.schedule import Schedule
    f = make_ferment(db); db.commit()
    s = Schedule(name="To delete", target_type="ferment", target_id=f.id, is_active=True)
    db.add(s); db.commit()
    resp = auth_client.post(f"/schedules/{s.id}/delete")
    assert resp.status_code in (302, 303)
    assert db.query(Schedule).filter_by(id=s.id).first() is None