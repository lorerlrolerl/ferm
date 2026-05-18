from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.auth import require_editor
from app.database import get_db
from app.models.ferment import Batch
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
    status_id: Optional[int] = Form(None),
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
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
        return datetime.now(timezone.utc).replace(tzinfo=None)

    smells  = db.query(SmellDescriptor).filter(SmellDescriptor.id.in_(smell_ids)).all() if smell_ids else []
    visuals = db.query(VisualDescriptor).filter(VisualDescriptor.id.in_(visual_ids)).all() if visual_ids else []

    entry = BatchLog(
        batch_id=batch_id,
        logged_at=parse_dt(logged_at),
        logged_by_id=current_user.id,
        status_id=status_id or None,
        ph=ph,
        temperature=temperature,
        smell_notes=smell_notes or None,
        visual_notes=visual_notes or None,
        notes=notes or None,
    )
    entry.smell_descriptors  = smells
    entry.visual_descriptors = visuals
    db.add(entry)

    # If status changed, update the batch status too
    if status_id:
        batch.status_id = status_id

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