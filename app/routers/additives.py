from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.auth import require_user, require_editor, require_admin
from app.database import get_db
from app.models.additive import Additive, AdditiveType
from app.models.user import User
from app.templates import templates

router = APIRouter(prefix="/additives")


# ── List ───────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
def additives_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    q: Optional[str] = None,
    additive_type: Optional[str] = None,
):
    query = db.query(Additive)
    if q:
        query = query.filter(Additive.name.ilike(f"%{q}%"))
    if additive_type:
        query = query.filter(Additive.additive_type == additive_type)

    additives = query.order_by(Additive.name).all()

    return templates.TemplateResponse(
        request,
        "additives/list.html",
        {
            "current_user": current_user,
            "additives": additives,
            "additive_types": [t.value for t in AdditiveType],
            "filters": {"q": q or "", "additive_type": additive_type or ""},
        },
    )


# ── New ────────────────────────────────────────────────────────────────────

@router.get("/new", response_class=HTMLResponse)
def additives_new(
    request: Request,
    current_user: User = Depends(require_editor),
):
    return templates.TemplateResponse(
        request,
        "additives/new.html",
        {
            "current_user": current_user,
            "additive_types": [t.value for t in AdditiveType],
            "errors": {},
        },
    )


@router.post("/new")
def additives_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
    name: str = Form(...),
    additive_type: str = Form(...),
    description: Optional[str] = Form(None),
):
    errors = {}
    if not name.strip():
        errors["name"] = "Name is required."
    if additive_type not in [t.value for t in AdditiveType]:
        errors["additive_type"] = "Invalid type."

    existing = db.query(Additive).filter(
        Additive.name.ilike(name.strip()),
        Additive.additive_type == additive_type,
    ).first()
    if existing:
        errors["name"] = f"'{name.strip()}' ({additive_type}) already exists."

    if errors:
        return templates.TemplateResponse(
            request,
            "additives/new.html",
            {
                "current_user": current_user,
                "additive_types": [t.value for t in AdditiveType],
                "errors": errors,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    additive = Additive(
        name=name.strip(),
        additive_type=additive_type,
        description=description or None,
    )
    db.add(additive)
    db.commit()

    return RedirectResponse("/additives", status_code=status.HTTP_303_SEE_OTHER)


# ── Edit ───────────────────────────────────────────────────────────────────

@router.get("/{additive_id}/edit", response_class=HTMLResponse)
def additives_edit(
    additive_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    additive = db.query(Additive).filter(Additive.id == additive_id).first()
    if not additive:
        return RedirectResponse("/additives", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        request,
        "additives/edit.html",
        {
            "current_user": current_user,
            "additive": additive,
            "additive_types": [t.value for t in AdditiveType],
            "errors": {},
        },
    )


@router.post("/{additive_id}/edit")
def additives_update(
    additive_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
    name: str = Form(...),
    additive_type: str = Form(...),
    description: Optional[str] = Form(None),
):
    additive = db.query(Additive).filter(Additive.id == additive_id).first()
    if not additive:
        return RedirectResponse("/additives", status_code=status.HTTP_302_FOUND)

    errors = {}
    if not name.strip():
        errors["name"] = "Name is required."

    existing = db.query(Additive).filter(
        Additive.name.ilike(name.strip()),
        Additive.additive_type == additive_type,
        Additive.id != additive_id,
    ).first()
    if existing:
        errors["name"] = f"'{name.strip()}' ({additive_type}) already exists."

    if errors:
        return templates.TemplateResponse(
            request,
            "additives/edit.html",
            {
                "current_user": current_user,
                "additive": additive,
                "additive_types": [t.value for t in AdditiveType],
                "errors": errors,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    additive.name = name.strip()
    additive.additive_type = additive_type
    additive.description = description or None
    db.commit()

    return RedirectResponse("/additives", status_code=status.HTTP_303_SEE_OTHER)


# ── Delete ─────────────────────────────────────────────────────────────────

@router.post("/{additive_id}/delete")
def additives_delete(
    additive_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    additive = (
        db.query(Additive)
        .options(joinedload(Additive.batch_additives))
        .filter(Additive.id == additive_id)
        .first()
    )
    if not additive:
        return RedirectResponse("/additives", status_code=status.HTTP_302_FOUND)

    if additive.is_in_use:
        return RedirectResponse(
            "/additives?error=in_use",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    db.delete(additive)
    db.commit()

    return RedirectResponse("/additives", status_code=status.HTTP_303_SEE_OTHER)