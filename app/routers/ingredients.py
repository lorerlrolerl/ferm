from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.auth import require_user, require_editor, require_admin
from app.database import get_db
from app.models.ingredient import Ingredient
from app.models.lookup import CutSize, Tag
from app.models.user import User
from app.templates import templates

router = APIRouter(prefix="/ingredients")


def _form_lookups(db: Session) -> dict:
    return {
        "cut_sizes": db.query(CutSize).order_by(CutSize.name).all(),
        "tags": db.query(Tag).order_by(Tag.name).all(),
    }


# ── List ───────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
def ingredients_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    q: Optional[str] = None,
    tag_id: Optional[str] = None,
    cut_size_id: Optional[str] = None,
):
    tid  = int(tag_id)       if tag_id       and tag_id.strip()       else None
    csid = int(cut_size_id)  if cut_size_id  and cut_size_id.strip()  else None

    query = (
        db.query(Ingredient)
        .options(joinedload(Ingredient.cut_size), joinedload(Ingredient.tags))
        .filter(Ingredient.is_active == True)
    )
    if q:
        query = query.filter(Ingredient.name.ilike(f"%{q}%"))
    if tid:
        query = query.filter(Ingredient.tags.any(Tag.id == tid))
    if csid:
        query = query.filter(Ingredient.cut_size_id == csid)


    ingredients = query.all()

    return templates.TemplateResponse(
        request,
        "ingredients/list.html",
        {
            "current_user": current_user,
            "ingredients": ingredients,
            "filters": {"q": q or "", "tag_id": tid, "cut_size_id": csid},
            **_form_lookups(db),
        },
    )


# ── New ────────────────────────────────────────────────────────────────────

@router.get("/new", response_class=HTMLResponse)
def ingredients_new(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    return templates.TemplateResponse(
        request,
        "ingredients/new.html",
        {"current_user": current_user, "errors": {}, **_form_lookups(db)},
    )


@router.post("/new")
def ingredients_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    cut_size_id: Optional[int] = Form(None),
    tag_ids: list[int] = Form(default=[]),
):
    errors = {}
    if not name.strip():
        errors["name"] = "Name is required."

    # Check uniqueness: same name + same cut size = duplicate
    existing = db.query(Ingredient).filter(
        Ingredient.name.ilike(name.strip()),
        Ingredient.cut_size_id == cut_size_id,
        Ingredient.is_active == True,
    ).first()
    if existing:
        cut = existing.cut_size.name if existing.cut_size else "no cut size"
        errors["name"] = f"'{name.strip()}' with '{cut}' already exists."

    if errors:
        return templates.TemplateResponse(
            request,
            "ingredients/new.html",
            {"current_user": current_user, "errors": errors, **_form_lookups(db)},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all() if tag_ids else []

    ingredient = Ingredient(
        name=name.strip(),
        description=description or None,
        cut_size_id=cut_size_id or None,
    )
    ingredient.tags = tags
    db.add(ingredient)
    db.commit()

    return RedirectResponse("/ingredients", status_code=status.HTTP_303_SEE_OTHER)


# ── Edit ───────────────────────────────────────────────────────────────────

@router.get("/{ingredient_id}/edit", response_class=HTMLResponse)
def ingredients_edit(
    ingredient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    ingredient = (
        db.query(Ingredient)
        .options(joinedload(Ingredient.cut_size), joinedload(Ingredient.tags))
        .filter(Ingredient.id == ingredient_id)
        .first()
    )
    if not ingredient:
        return RedirectResponse("/ingredients", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        request,
        "ingredients/edit.html",
        {
            "current_user": current_user,
            "ingredient": ingredient,
            "errors": {},
            "selected_tag_ids": [t.id for t in ingredient.tags],
            **_form_lookups(db),
        },
    )


@router.post("/{ingredient_id}/edit")
def ingredients_update(
    ingredient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    cut_size_id: Optional[int] = Form(None),
    tag_ids: list[int] = Form(default=[]),
):
    ingredient = (
        db.query(Ingredient)
        .options(joinedload(Ingredient.tags))
        .filter(Ingredient.id == ingredient_id)
        .first()
    )
    if not ingredient:
        return RedirectResponse("/ingredients", status_code=status.HTTP_302_FOUND)

    errors = {}
    if not name.strip():
        errors["name"] = "Name is required."

    # Uniqueness check excluding self
    existing = db.query(Ingredient).filter(
        Ingredient.name.ilike(name.strip()),
        Ingredient.cut_size_id == cut_size_id,
        Ingredient.is_active == True,
        Ingredient.id != ingredient_id,
    ).first()
    if existing:
        cut = existing.cut_size.name if existing.cut_size else "no cut size"
        errors["name"] = f"'{name.strip()}' with '{cut}' already exists."

    if errors:
        return templates.TemplateResponse(
            request,
            "ingredients/edit.html",
            {
                "current_user": current_user,
                "ingredient": ingredient,
                "errors": errors,
                "selected_tag_ids": tag_ids,
                **_form_lookups(db),
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # Edit propagates everywhere — ingredient is the same object
    # referenced by all batches, so updating it updates it everywhere
    ingredient.name = name.strip()
    ingredient.description = description or None
    ingredient.cut_size_id = cut_size_id or None
    ingredient.tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all() if tag_ids else []
    db.commit()

    return RedirectResponse("/ingredients", status_code=status.HTTP_303_SEE_OTHER)


# ── Delete ─────────────────────────────────────────────────────────────────

@router.post("/{ingredient_id}/delete")
def ingredients_delete(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    ingredient = (
        db.query(Ingredient)
        .options(joinedload(Ingredient.batch_ingredients))
        .filter(Ingredient.id == ingredient_id)
        .first()
    )
    if not ingredient:
        return RedirectResponse("/ingredients", status_code=status.HTTP_302_FOUND)

    # Protected — cannot delete if used in any batch
    if ingredient.is_in_use:
        return RedirectResponse(
            "/ingredients?error=in_use",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Soft delete — mark inactive instead of removing from DB
    ingredient.is_active = False
    db.commit()

    return RedirectResponse("/ingredients", status_code=status.HTTP_303_SEE_OTHER)