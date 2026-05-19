from typing import Optional
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models.lookup import (
    Category, Status, CutSize, Tag,
    SmellDescriptor, VisualDescriptor,
    VesselType, VesselMaterial,
)
from app.models.ferment import Ferment, Batch, Container
from app.models.ingredient import Ingredient, ingredient_tags
from app.models.log import log_smells, log_visuals
from app.models.user import User
from app.templates import templates

router = APIRouter(prefix="/settings")


# ── Usage counters ─────────────────────────────────────────────────────────

def _status_usage(db, sid):
    return {
        "ferments":   db.query(Ferment).filter_by(status_id=sid).count(),
        "batches":    db.query(Batch).filter_by(status_id=sid).count(),
        "containers": db.query(Container).filter_by(status_id=sid).count(),
    }

def _category_usage(db, cid):
    return {"ferments": db.query(Ferment).filter_by(category_id=cid).count()}

def _cut_size_usage(db, csid):
    return {"ingredients": db.query(Ingredient).filter_by(cut_size_id=csid, is_active=True).count()}

def _tag_usage(db, tid):
    rows = db.execute(ingredient_tags.select().where(ingredient_tags.c.tag_id == tid)).fetchall()
    return {"ingredients": len(rows)}

def _smell_usage(db, sid):
    rows = db.execute(log_smells.select().where(log_smells.c.smell_id == sid)).fetchall()
    return {"log entries": len(rows)}

def _visual_usage(db, vid):
    rows = db.execute(log_visuals.select().where(log_visuals.c.visual_id == vid)).fetchall()
    return {"log entries": len(rows)}

def _vessel_type_usage(db, vid):
    return {"containers": db.query(Container).filter_by(vessel_type_id=vid).count()}

def _vessel_material_usage(db, vid):
    return {"containers": db.query(Container).filter_by(vessel_material_id=vid).count()}

def _total(usage): return sum(usage.values())


# ── Item name resolvers (for popover links) ────────────────────────────────

def _status_names(db, sid):
    ferments   = db.query(Ferment).filter_by(status_id=sid).all()
    batches    = db.query(Batch).filter_by(status_id=sid).all()
    containers = db.query(Container).filter_by(status_id=sid).all()
    return {
        "ferments":   [{"name": f.name, "url": f"/ferments/{f.id}"} for f in ferments],
        "batches":    [{"name": b.lot_code or f"B{b.batch_number}", "url": f"/ferments/{b.ferment_id}/batches/{b.id}"} for b in batches],
        "containers": [{"name": c.name, "url": None} for c in containers],
    }

def _category_names(db, cid):
    ferments = db.query(Ferment).filter_by(category_id=cid).all()
    return {"ferments": [{"name": f.name, "url": f"/ferments/{f.id}"} for f in ferments]}

def _cut_size_names(db, csid):
    ings = db.query(Ingredient).filter_by(cut_size_id=csid, is_active=True).all()
    return {"ingredients": [{"name": i.name, "url": f"/ingredients/{i.id}/edit"} for i in ings]}

def _tag_names(db, tid):
    rows = db.execute(ingredient_tags.select().where(ingredient_tags.c.tag_id == tid)).fetchall()
    result = []
    for row in rows:
        ing = db.query(Ingredient).filter_by(id=row.ingredient_id).first()
        if ing:
            result.append({"name": ing.name, "url": f"/ingredients/{ing.id}/edit"})
    return {"ingredients": result}

def _smell_names(db, sid):
    rows = db.execute(log_smells.select().where(log_smells.c.smell_id == sid)).fetchall()
    return {"log entries": [{"name": f"Log #{row.log_id}", "url": None} for row in rows[:10]]}

def _visual_names(db, vid):
    rows = db.execute(log_visuals.select().where(log_visuals.c.visual_id == vid)).fetchall()
    return {"log entries": [{"name": f"Log #{row.log_id}", "url": None} for row in rows[:10]]}

def _vessel_type_names(db, vid):
    containers = db.query(Container).filter_by(vessel_type_id=vid).all()
    return {"containers": [{"name": c.name, "url": None} for c in containers]}

def _vessel_material_names(db, vid):
    containers = db.query(Container).filter_by(vessel_material_id=vid).all()
    return {"containers": [{"name": c.name, "url": None} for c in containers]}


# ── Model registry ─────────────────────────────────────────────────────────

MODELS     = {"statuses": Status, "categories": Category, "cut_sizes": CutSize,
              "tags": Tag, "smell_descriptors": SmellDescriptor,
              "visual_descriptors": VisualDescriptor, "vessel_types": VesselType,
              "vessel_materials": VesselMaterial}
USAGE_FNS  = {"statuses": _status_usage, "categories": _category_usage,
              "cut_sizes": _cut_size_usage, "tags": _tag_usage,
              "smell_descriptors": _smell_usage, "visual_descriptors": _visual_usage,
              "vessel_types": _vessel_type_usage, "vessel_materials": _vessel_material_usage}
NAME_FNS   = {"statuses": _status_names, "categories": _category_names,
              "cut_sizes": _cut_size_names, "tags": _tag_names,
              "smell_descriptors": _smell_names, "visual_descriptors": _visual_names,
              "vessel_types": _vessel_type_names, "vessel_materials": _vessel_material_names}
HAS_COLOR  = {"statuses"}
HAS_DESC   = {"statuses", "categories", "cut_sizes"}


def _redirect(section, msg=None):
    url = f"/settings?section={section}#{section}"
    if msg:
        url = f"/settings?section={section}&msg={msg}#{section}"
    return RedirectResponse(url, status_code=302)


# ── Main page ──────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
def settings_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    section: str = "statuses",
    msg: Optional[str] = None,
):
    def with_usage(items, ufn):
        return [{"item": i, "usage": ufn(db, i.id), "total": _total(ufn(db, i.id))} for i in items]

    data = {
        "statuses":          with_usage(db.query(Status).order_by(Status.name).all(),           _status_usage),
        "categories":        with_usage(db.query(Category).order_by(Category.name).all(),       _category_usage),
        "cut_sizes":         with_usage(db.query(CutSize).order_by(CutSize.name).all(),         _cut_size_usage),
        "tags":              with_usage(db.query(Tag).order_by(Tag.name).all(),                  _tag_usage),
        "smell_descriptors": with_usage(db.query(SmellDescriptor).order_by(SmellDescriptor.name).all(), _smell_usage),
        "visual_descriptors":with_usage(db.query(VisualDescriptor).order_by(VisualDescriptor.name).all(),_visual_usage),
        "vessel_types":      with_usage(db.query(VesselType).order_by(VesselType.name).all(),   _vessel_type_usage),
        "vessel_materials":  with_usage(db.query(VesselMaterial).order_by(VesselMaterial.name).all(), _vessel_material_usage),
    }

    # Build item_names for JS popovers — only for items that have usage
    item_names = {}
    for key, rows in data.items():
        item_names[key] = {}
        name_fn = NAME_FNS.get(key)
        if name_fn:
            for row in rows:
                if row["total"] > 0:
                    item_names[key][row["item"].id] = name_fn(db, row["item"].id)

    return templates.TemplateResponse(request, "settings/index.html", {
        "current_user": current_user,
        "data": data,
        "active_section": section,
        "item_names": item_names,
        "msg": msg,
    })


# ── Create ─────────────────────────────────────────────────────────────────

@router.post("/{table}/new")
def lookup_create(
    table: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
):
    model = MODELS.get(table)
    if not model or not name.strip():
        return _redirect(table)
    if db.query(model).filter_by(name=name.strip()).first():
        return _redirect(table, "duplicate")
    kwargs = {"name": name.strip()}
    if table in HAS_DESC and description:
        kwargs["description"] = description
    if table in HAS_COLOR:
        kwargs["color"] = color or "#888888"
    db.add(model(**kwargs))
    db.commit()
    return _redirect(table)


# ── Edit ───────────────────────────────────────────────────────────────────

@router.post("/{table}/{item_id}/edit")
def lookup_edit(
    table: str, item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
):
    model = MODELS.get(table)
    if not model or not name.strip():
        return _redirect(table)
    item = db.query(model).filter_by(id=item_id).first()
    if not item:
        return _redirect(table)
    item.name = name.strip()
    if table in HAS_DESC:
        item.description = description or None
    if table in HAS_COLOR and color:
        item.color = color
    db.commit()
    return _redirect(table)


# ── Delete ─────────────────────────────────────────────────────────────────

@router.post("/{table}/{item_id}/delete")
def lookup_delete(
    table: str, item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    model = MODELS.get(table)
    if not model:
        return _redirect(table)
    item = db.query(model).filter_by(id=item_id).first()
    if not item:
        return _redirect(table)
    usage_fn = USAGE_FNS.get(table)
    if usage_fn and _total(usage_fn(db, item_id)) > 0:
        return _redirect(table, "in_use")
    db.delete(item)
    db.commit()
    return _redirect(table)