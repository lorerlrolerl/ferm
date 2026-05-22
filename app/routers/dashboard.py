from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth import require_user
from app.database import get_db
from app.models.ferment import Batch, Ferment
from app.models.log import BatchLog
from app.models.lookup import Status
from app.models.schedule import Schedule
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
    active_id = _get_status_id(db, "active")
    stasis_id = _get_status_id(db, "stasis")
    ready_id  = _get_status_id(db, "ready")

    # ── KPI counts — based on ferment status ───────────────────────────────
    total_ferments = db.query(Ferment).filter(Ferment.archived_at == None).count()
    active_count   = db.query(Ferment).filter(Ferment.status_id == active_id, Ferment.archived_at == None).count()
    stasis_count   = db.query(Ferment).filter(Ferment.status_id == stasis_id, Ferment.archived_at == None).count()
    ready_count    = db.query(Ferment).filter(Ferment.status_id == ready_id,  Ferment.archived_at == None).count()

    # ── Active + stasis ferments ───────────────────────────────────────────
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

    # Preload last log per batch for all active ferments
    batch_ids = [b.id for f in active_ferments for b in f.batches]
    last_log_by_batch = {}
    if batch_ids:
        # Subquery: most recent log per batch
        subq = (
            db.query(
                BatchLog.batch_id,
                func.max(BatchLog.logged_at).label("latest")
            )
            .filter(BatchLog.batch_id.in_(batch_ids))
            .group_by(BatchLog.batch_id)
            .subquery()
        )
        last_logs = (
            db.query(BatchLog)
            .join(subq, (BatchLog.batch_id == subq.c.batch_id) &
                         (BatchLog.logged_at == subq.c.latest))
            .all()
        )
        last_log_by_batch = {log.batch_id: log for log in last_logs}

    ferment_data = []
    stasis_data  = []
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

        # Last log info for this batch
        last_log = last_log_by_batch.get(latest_batch.id) if latest_batch else None
        days_since_log = (now - last_log.logged_at).days if last_log and last_log.logged_at else None

        entry = {
            "ferment": ferment,
            "latest_batch": latest_batch,
            "age_days": age_days,
            "last_log": last_log,
            "days_since_log": days_since_log,
        }
        if ferment.status_id == stasis_id:
            stasis_data.append(entry)
        else:
            ferment_data.append(entry)

    # Active first, then stasis below
    ferment_data = ferment_data + stasis_data

    # ── Schedules due ──────────────────────────────────────────────────────
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

    hour = now.hour
    if hour < 12:
        greeting = "Goedemorgen"
    elif hour < 18:
        greeting = "Goedemiddag"
    else:
        greeting = "Goedenavond"

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "current_user": current_user,
            "greeting": greeting,
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