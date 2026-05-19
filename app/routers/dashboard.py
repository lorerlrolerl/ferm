from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth import require_user
from app.database import get_db
from app.models.ferment import Batch, Ferment
from app.models.lookup import Status
from app.models.schedule import Schedule, ScheduleEvent
from app.models.tool import Tool
from app.models.user import User
from app.templates import templates

router = APIRouter()


def _get_status_id(db: Session, name: str) -> int | None:
    s = db.query(Status).filter(func.lower(Status.name) == name.lower()).first()
    return s.id if s else None


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # ── Status id lookups ──────────────────────────────────────────────────
    active_id  = _get_status_id(db, "active")
    stasis_id  = _get_status_id(db, "stasis")
    ready_id   = _get_status_id(db, "ready")

    # ── KPI counts ─────────────────────────────────────────────────────────
    total_ferments  = db.query(Ferment).filter(Ferment.archived_at == None).count()
    active_count    = db.query(Ferment).filter(Ferment.status_id == active_id,  Ferment.archived_at == None).count()
    stasis_count    = db.query(Ferment).filter(Ferment.status_id == stasis_id,  Ferment.archived_at == None).count()
    ready_count     = db.query(Ferment).filter(Ferment.status_id == ready_id,   Ferment.archived_at == None).count()

    # ── Active ferments with latest batch ──────────────────────────────────
    active_ferments = (
        db.query(Ferment)
        .filter(Ferment.archived_at == None)
        .filter(Ferment.status_id.in_(
            [sid for sid in [active_id, stasis_id] if sid is not None]
        ))
        .options(
            joinedload(Ferment.category),
            joinedload(Ferment.status),
            joinedload(Ferment.batches).joinedload(Batch.status),
        )
        .order_by(Ferment.created_at.desc())
        .all()
    )

    # Attach latest batch and age in days to each ferment
    ferment_data = []
    for ferment in active_ferments:
        latest_batch = (
            sorted(ferment.batches, key=lambda b: b.started_at or datetime.min)[-1]
            if ferment.batches else None
        )
        started = (
            latest_batch.started_at if latest_batch and latest_batch.started_at
            else ferment.created_at
        )
        age_days = (now - started).days if started else None

        ferment_data.append({
            "ferment": ferment,
            "latest_batch": latest_batch,
            "age_days": age_days,
        })

    # ── Schedules due today or overdue ─────────────────────────────────────
    due_schedules = (
        db.query(Schedule)
        .filter(
            Schedule.is_active == True,
            Schedule.next_due_at != None,
            Schedule.next_due_at <= now,
        )
        .order_by(Schedule.next_due_at.asc())
        .limit(10)
        .all()
    )

    # Resolve target names for due schedules
    def _target_name(s):
        try:
            if s.target_type == "ferment":
                obj = db.query(Ferment).filter_by(id=s.target_id).first()
                return obj.name if obj else f"Ferment #{s.target_id}"
            elif s.target_type == "batch":
                obj = db.query(Batch).filter_by(id=s.target_id).first()
                return obj.lot_code or f"Batch #{s.target_id}" if obj else f"Batch #{s.target_id}"
            elif s.target_type == "tool":
                obj = db.query(Tool).filter_by(id=s.target_id).first()
                return obj.name if obj else f"Tool #{s.target_id}"
        except Exception:
            pass
        return f"{s.target_type} #{s.target_id}"

    due_enriched = [
        {"schedule": s, "target_name": _target_name(s),
         "days_overdue": (now - s.next_due_at).days}
        for s in due_schedules
    ]

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "current_user": current_user,
            "total_ferments": total_ferments,
            "active_count": active_count,
            "stasis_count": stasis_count,
            "ready_count": ready_count,
            "ferment_data": ferment_data,
            "due_schedules": due_schedules,
            "due_enriched": due_enriched,
            "now": now,
        },
    )