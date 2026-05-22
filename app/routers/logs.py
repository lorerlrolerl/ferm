from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.auth import require_editor
from app.database import get_db
from app.models.ferment import Batch, Ferment
from app.models.log import BatchLog
from app.models.lookup import Status, SmellDescriptor, VisualDescriptor
from app.models.user import User

router = APIRouter(prefix="/ferments/{ferment_id}/batches/{batch_id}/logs")


@router.post("/add")
def log_add(
    ferment_id: int,
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
    logged_at: Optional[str] = Form(None),
    status_id: Optional[str] = Form(None),
    ph: Optional[float] = Form(None),
    temperature: Optional[float] = Form(None),
    smell_ids: list[int] = Form(default=[]),
    smell_notes: Optional[str] = Form(None),
    visual_ids: list[int] = Form(default=[]),
    visual_notes: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    batch = db.query(Batch).filter(
        Batch.id == batch_id, Batch.ferment_id == ferment_id
    ).first()
    if not batch:
        return RedirectResponse(f"/ferments/{ferment_id}", status_code=status.HTTP_302_FOUND)

    def parse_dt(val):
        if not val:
            return datetime.now(timezone.utc).replace(tzinfo=None)
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
        return datetime.now(timezone.utc).replace(tzinfo=None)

    # Convert status_id from form string to int (empty string → None)
    sid = None
    if status_id and status_id.strip():
        try:
            sid = int(status_id)
        except ValueError:
            sid = None

    smells  = db.query(SmellDescriptor).filter(SmellDescriptor.id.in_(smell_ids)).all() if smell_ids else []
    visuals = db.query(VisualDescriptor).filter(VisualDescriptor.id.in_(visual_ids)).all() if visual_ids else []

    entry = BatchLog(
        batch_id=batch_id,
        logged_at=parse_dt(logged_at),
        logged_by_id=current_user.id,
        status_id=sid,
        ph=ph,
        temperature=temperature,
        smell_notes=smell_notes or None,
        visual_notes=visual_notes or None,
        notes=notes or None,
    )
    entry.smell_descriptors  = smells
    entry.visual_descriptors = visuals
    db.add(entry)

    # If status changed, update both batch and ferment status
    if sid:
        batch.status_id = sid
        ferment = db.query(Ferment).filter_by(id=ferment_id).first()
        if ferment:
            ferment.status_id = sid

    db.commit()

    return RedirectResponse(
        f"/ferments/{ferment_id}/batches/{batch_id}?tab=log",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/{log_id}/edit")
def log_edit_page(
    ferment_id: int,
    batch_id: int,
    log_id: int,
    request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    from app.templates import templates
    from fastapi.responses import HTMLResponse
    entry = db.query(BatchLog).filter(
        BatchLog.id == log_id, BatchLog.batch_id == batch_id
    ).first()
    if not entry:
        return RedirectResponse(
            f"/ferments/{ferment_id}/batches/{batch_id}?tab=log",
            status_code=status.HTTP_302_FOUND,
        )
    batch = db.query(Batch).filter_by(id=batch_id).first()
    from app.models.ferment import Ferment as FermentModel
    ferment = db.query(FermentModel).filter_by(id=ferment_id).first()
    statuses = db.query(Status).order_by(Status.name).all()
    smell_descriptors  = db.query(SmellDescriptor).order_by(SmellDescriptor.name).all()
    visual_descriptors = db.query(VisualDescriptor).order_by(VisualDescriptor.name).all()
    return templates.TemplateResponse(request, "batches/log_edit.html", {
        "current_user": current_user,
        "ferment": ferment,
        "batch": batch,
        "entry": entry,
        "statuses": statuses,
        "smell_descriptors": smell_descriptors,
        "visual_descriptors": visual_descriptors,
    })


@router.post("/{log_id}/edit")
def log_edit(
    ferment_id: int,
    batch_id: int,
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
    logged_at: Optional[str] = Form(None),
    status_id: Optional[str] = Form(None),
    ph: Optional[float] = Form(None),
    temperature: Optional[float] = Form(None),
    smell_ids: list[int] = Form(default=[]),
    smell_notes: Optional[str] = Form(None),
    visual_ids: list[int] = Form(default=[]),
    visual_notes: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    entry = db.query(BatchLog).filter(
        BatchLog.id == log_id, BatchLog.batch_id == batch_id
    ).first()
    if not entry:
        return RedirectResponse(
            f"/ferments/{ferment_id}/batches/{batch_id}?tab=log",
            status_code=status.HTTP_302_FOUND,
        )

    def parse_dt(val):
        if not val:
            return entry.logged_at
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
        return entry.logged_at

    sid = None
    if status_id and status_id.strip():
        try:
            sid = int(status_id)
        except ValueError:
            sid = None

    smells  = db.query(SmellDescriptor).filter(SmellDescriptor.id.in_(smell_ids)).all() if smell_ids else []
    visuals = db.query(VisualDescriptor).filter(VisualDescriptor.id.in_(visual_ids)).all() if visual_ids else []

    entry.logged_at          = parse_dt(logged_at)
    entry.status_id          = sid
    entry.ph                 = ph
    entry.temperature        = temperature
    entry.smell_notes        = smell_notes or None
    entry.visual_notes       = visual_notes or None
    entry.notes              = notes or None
    entry.smell_descriptors  = smells
    entry.visual_descriptors = visuals

    # Sync batch and ferment status to most recent log's status
    if sid:
        batch = db.query(Batch).filter_by(id=batch_id).first()
        if batch:
            batch.status_id = sid
        ferment = db.query(Ferment).filter_by(id=ferment_id).first()
        if ferment:
            ferment.status_id = sid

    db.commit()
    return RedirectResponse(
        f"/ferments/{ferment_id}/batches/{batch_id}?tab=log",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{log_id}/delete")
def log_delete(
    ferment_id: int,
    batch_id: int,
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    entry = db.query(BatchLog).filter(
        BatchLog.id == log_id, BatchLog.batch_id == batch_id
    ).first()
    if entry:
        db.delete(entry)
        db.commit()
    return RedirectResponse(
        f"/ferments/{ferment_id}/batches/{batch_id}?tab=log",
        status_code=status.HTTP_303_SEE_OTHER,
    )