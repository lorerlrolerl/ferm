from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.auth import require_user, require_editor
from app.database import get_db
from app.lot_code import generate_lot_code, next_batch_number
from app.models.ferment import Batch, Ferment
from app.models.lookup import Category, Status
from app.models.user import User
from app.templates import templates

router = APIRouter(prefix="/ferments")


def _form_lookups(db: Session) -> dict:
    return {
        "categories": db.query(Category).order_by(Category.name).all(),
        "statuses": db.query(Status).order_by(Status.name).all(),
    }


def _parse_date(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        return datetime.strptime(val, "%Y-%m-%d")
    except ValueError:
        return None


# ── List ───────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
def ferments_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    category_id: Optional[int] = None,
    status_id: Optional[int] = None,
    q: Optional[str] = None,
):
    query = (
        db.query(Ferment)
        .filter(Ferment.archived_at == None)
        .options(
            joinedload(Ferment.category),
            joinedload(Ferment.status),
            joinedload(Ferment.batches),
        )
    )
    if category_id:
        query = query.filter(Ferment.category_id == category_id)
    if status_id:
        query = query.filter(Ferment.status_id == status_id)
    if q:
        query = query.filter(Ferment.name.ilike(f"%{q}%"))

    ferments = query.order_by(Ferment.created_at.desc()).all()

    return templates.TemplateResponse(
        request,
        "ferments/list.html",
        {
            "current_user": current_user,
            "ferments": ferments,
            "categories": db.query(Category).order_by(Category.name).all(),
            "statuses": db.query(Status).order_by(Status.name).all(),
            "filters": {"category_id": category_id, "status_id": status_id, "q": q or ""},
        },
    )


# ── New ────────────────────────────────────────────────────────────────────

@router.get("/new", response_class=HTMLResponse)
def ferments_new(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    today = datetime.now().strftime("%Y-%m-%d")
    return templates.TemplateResponse(
        request,
        "ferments/new.html",
        {"current_user": current_user, "errors": {}, "today": today, **_form_lookups(db)},
    )


@router.post("/new")
def ferments_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
    # Ferment fields
    name: str = Form(...),
    category_id: Optional[int] = Form(None),
    status_id: Optional[int] = Form(None),
    is_ongoing: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    # Batch fields
    batch_stage: int = Form(1),
    batch_started_at: Optional[str] = Form(None),
    batch_target_ready_at: Optional[str] = Form(None),
    batch_target_ph: Optional[float] = Form(None),
    batch_notes: Optional[str] = Form(None),
    batch_lot_code: Optional[str] = Form(None),
):
    errors = {}
    if not name.strip():
        errors["name"] = "Name is required."

    # Check lot code uniqueness if provided
    if batch_lot_code and batch_lot_code.strip():
        existing = db.query(Batch).filter(Batch.lot_code == batch_lot_code.strip()).first()
        if existing:
            errors["batch_lot_code"] = f"Lot code '{batch_lot_code}' is already in use."

    if errors:
        today = datetime.now().strftime("%Y-%m-%d")
        return templates.TemplateResponse(
            request,
            "ferments/new.html",
            {"current_user": current_user, "errors": errors, "today": today, **_form_lookups(db)},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    started = _parse_date(batch_started_at) or datetime.now(timezone.utc).replace(tzinfo=None)

    # Get category name for lot code generation
    category_name = None
    if category_id:
        cat = db.query(Category).filter(Category.id == category_id).first()
        category_name = cat.name if cat else None

    ferment = Ferment(
        name=name.strip(),
        description=description or None,
        category_id=category_id,
        status_id=status_id,
        is_ongoing=bool(is_ongoing),
        created_by_id=current_user.id,
    )
    db.add(ferment)
    db.flush()  # get ferment.id

    batch_num = 1  # first batch
    lot_code = (
        batch_lot_code.strip()
        if batch_lot_code and batch_lot_code.strip()
        else generate_lot_code(name.strip(), category_name, started, batch_stage, batch_num)
    )

    batch = Batch(
        ferment_id=ferment.id,
        batch_number=batch_num,
        lot_code=lot_code,
        stage=batch_stage,
        status_id=status_id,
        started_at=started,
        target_ready_at=_parse_date(batch_target_ready_at),
        target_ph=batch_target_ph,
        notes=batch_notes or None,
        created_by_id=current_user.id,
    )
    db.add(batch)
    db.commit()

    return RedirectResponse(f"/ferments/{ferment.id}", status_code=status.HTTP_303_SEE_OTHER)


# ── Detail ─────────────────────────────────────────────────────────────────

@router.get("/{ferment_id}", response_class=HTMLResponse)
def ferments_detail(
    ferment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    ferment = (
        db.query(Ferment)
        .filter(Ferment.id == ferment_id)
        .options(
            joinedload(Ferment.category),
            joinedload(Ferment.status),
            joinedload(Ferment.created_by_user),
            joinedload(Ferment.batches).joinedload(Batch.status),
            joinedload(Ferment.batches).joinedload(Batch.ingredients),
            joinedload(Ferment.batches).joinedload(Batch.additives),
            joinedload(Ferment.batches).joinedload(Batch.containers),
        )
        .first()
    )

    if not ferment:
        return templates.TemplateResponse(
            request, "404.html", {"current_user": current_user}, status_code=404
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    batches = sorted(ferment.batches, key=lambda b: b.started_at or datetime.min)

    return templates.TemplateResponse(
        request,
        "ferments/detail.html",
        {
            "current_user": current_user,
            "ferment": ferment,
            "batches": batches,
            "now": now,
        },
    )


# ── Edit ferment ───────────────────────────────────────────────────────────

@router.get("/{ferment_id}/edit", response_class=HTMLResponse)
def ferments_edit(
    ferment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    ferment = db.query(Ferment).filter(Ferment.id == ferment_id).first()
    if not ferment:
        return RedirectResponse("/ferments", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        request,
        "ferments/edit.html",
        {"current_user": current_user, "ferment": ferment, "errors": {}, **_form_lookups(db)},
    )


@router.post("/{ferment_id}/edit")
def ferments_update(
    ferment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
    name: str = Form(...),
    category_id: Optional[int] = Form(None),
    status_id: Optional[int] = Form(None),
    is_ongoing: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
):
    ferment = db.query(Ferment).filter(Ferment.id == ferment_id).first()
    if not ferment:
        return RedirectResponse("/ferments", status_code=status.HTTP_302_FOUND)

    errors = {}
    if not name.strip():
        errors["name"] = "Name is required."

    if errors:
        return templates.TemplateResponse(
            request,
            "ferments/edit.html",
            {"current_user": current_user, "ferment": ferment, "errors": errors, **_form_lookups(db)},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    ferment.name = name.strip()
    ferment.description = description or None
    ferment.category_id = category_id
    ferment.status_id = status_id
    ferment.is_ongoing = bool(is_ongoing)
    db.commit()

    return RedirectResponse(f"/ferments/{ferment_id}", status_code=status.HTTP_303_SEE_OTHER)