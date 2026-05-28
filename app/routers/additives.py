from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import require_user, require_editor, require_admin
from app.database import get_db
from app.models.additive import Additive, AdditiveType
from app.models.ferment import BatchAdditive
from app.models.user import User
from app.templates import templates

router = APIRouter(prefix="/additives")


def _form_lookups(db: Session) -> dict:
    return {
        "additive_types": db.query(AdditiveType).order_by(AdditiveType.name).all(),
    }


@router.get("", response_class=HTMLResponse)
def additives_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    q: Optional[str] = None,
    type_id: Optional[str] = None,
    sort: Optional[str] = None,
    dir: Optional[str] = None,
):
    tid      = int(type_id) if type_id and type_id.strip() else None
    sort_by  = sort or "name"
    sort_dir = dir  or "asc"

    query = db.query(Additive)
    if q:
        query = query.filter(Additive.name.ilike(f"%{q}%"))
    if tid:
        query = query.filter(Additive.additive_type_id == tid)

    if sort_by == "type":
        query = query.outerjoin(AdditiveType, Additive.additive_type_id == AdditiveType.id)
        query = query.order_by(AdditiveType.name.asc() if sort_dir == "asc" else AdditiveType.name.desc())
    else:
        query = query.order_by(Additive.name.asc() if sort_dir == "asc" else Additive.name.desc())

    additives = query.all()
    additive_types = db.query(AdditiveType).order_by(AdditiveType.name).all()
    return templates.TemplateResponse(request, "additives/list.html", {
        "current_user": current_user,
        "additives": additives,
        "additive_types": additive_types,
        "filters": {"q": q or "", "type_id": tid},
        "sort": sort_by,
        "dir": sort_dir,
    })


@router.get("/new", response_class=HTMLResponse)
def additives_new(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    return templates.TemplateResponse(request, "additives/new.html", {
        "current_user": current_user,
        "errors": {},
        **_form_lookups(db),
    })


@router.post("/new")
def additives_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
    name: str = Form(...),
    additive_type_id: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
):
    errors = {}
    if not name.strip():
        errors["name"] = "Name is required."

    existing = db.query(Additive).filter(
        Additive.name == name.strip(),
        Additive.additive_type_id == additive_type_id,
    ).first()
    if existing:
        errors["name"] = "An additive with this name and type already exists."

    if errors:
        return templates.TemplateResponse(request, "additives/new.html", {
            "current_user": current_user, "errors": errors, **_form_lookups(db),
        }, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    db.add(Additive(
        name=name.strip(),
        additive_type_id=additive_type_id or None,
        description=description or None,
    ))
    db.commit()
    return RedirectResponse("/additives", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{additive_id}/edit", response_class=HTMLResponse)
def additives_edit(
    additive_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    additive = db.query(Additive).filter_by(id=additive_id).first()
    if not additive:
        return RedirectResponse("/additives", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request, "additives/edit.html", {
        "current_user": current_user,
        "additive": additive,
        "errors": {},
        **_form_lookups(db),
    })


@router.post("/{additive_id}/edit")
def additives_update(
    additive_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
    name: str = Form(...),
    additive_type_id: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
):
    additive = db.query(Additive).filter_by(id=additive_id).first()
    if not additive:
        return RedirectResponse("/additives", status_code=status.HTTP_302_FOUND)
    additive.name             = name.strip()
    additive.additive_type_id = additive_type_id or None
    additive.description      = description or None
    db.commit()
    return RedirectResponse("/additives", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{additive_id}/delete")
def additives_delete(
    additive_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    additive = db.query(Additive).filter_by(id=additive_id).first()
    if not additive:
        return RedirectResponse("/additives", status_code=status.HTTP_302_FOUND)
    in_use = db.query(BatchAdditive).filter_by(additive_id=additive_id).first()
    if in_use:
        return RedirectResponse("/additives?error=in_use", status_code=status.HTTP_302_FOUND)
    db.delete(additive)
    db.commit()
    return RedirectResponse("/additives", status_code=status.HTTP_303_SEE_OTHER)