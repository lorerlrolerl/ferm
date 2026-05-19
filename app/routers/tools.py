from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import require_user, require_editor, require_admin
from app.database import get_db
from app.models.tool import Tool
from app.models.user import User
from app.templates import templates

router = APIRouter(prefix="/tools")


@router.get("", response_class=HTMLResponse)
def tools_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    tools = db.query(Tool).order_by(Tool.name).all()
    return templates.TemplateResponse(request, "tools/list.html", {
        "current_user": current_user,
        "tools": tools,
    })


@router.get("/new", response_class=HTMLResponse)
def tools_new(request: Request, current_user: User = Depends(require_editor)):
    return templates.TemplateResponse(request, "tools/new.html", {
        "current_user": current_user, "errors": {},
    })


@router.post("/new")
def tools_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
    name: str = Form(...),
    tool_type: str = Form(...),
    description: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    errors = {}
    if not name.strip():
        errors["name"] = "Name is required."
    if not tool_type.strip():
        errors["tool_type"] = "Type is required."
    if errors:
        return templates.TemplateResponse(request, "tools/new.html",
            {"current_user": current_user, "errors": errors},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    db.add(Tool(name=name.strip(), tool_type=tool_type.strip(),
                description=description or None, notes=notes or None))
    db.commit()
    return RedirectResponse("/tools", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{tool_id}/edit", response_class=HTMLResponse)
def tools_edit(
    tool_id: int, request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    tool = db.query(Tool).filter_by(id=tool_id).first()
    if not tool:
        return RedirectResponse("/tools", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request, "tools/edit.html", {
        "current_user": current_user, "tool": tool, "errors": {},
    })


@router.post("/{tool_id}/edit")
def tools_update(
    tool_id: int, request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
    name: str = Form(...),
    tool_type: str = Form(...),
    description: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    tool = db.query(Tool).filter_by(id=tool_id).first()
    if not tool:
        return RedirectResponse("/tools", status_code=status.HTTP_302_FOUND)
    errors = {}
    if not name.strip():
        errors["name"] = "Name is required."
    if errors:
        return templates.TemplateResponse(request, "tools/edit.html",
            {"current_user": current_user, "tool": tool, "errors": errors},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    tool.name = name.strip()
    tool.tool_type = tool_type.strip()
    tool.description = description or None
    tool.notes = notes or None
    db.commit()
    return RedirectResponse("/tools", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{tool_id}/delete")
def tools_delete(
    tool_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    tool = db.query(Tool).filter_by(id=tool_id).first()
    if tool:
        db.delete(tool)
        db.commit()
    return RedirectResponse("/tools", status_code=status.HTTP_303_SEE_OTHER)