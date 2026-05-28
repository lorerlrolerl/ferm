from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import require_admin, require_user, hash_password, verify_password
from app.database import get_db
from app.models.user import User, UserRole
from app.models.ferment import Ferment, Batch
from app.models.log import BatchLog
from app.templates import templates

router = APIRouter(prefix="/users")

ROLES = [r.value for r in UserRole]


def _user_has_content(db: Session, user: User) -> bool:
    """True if the user has created any ferments, batches, or log entries."""
    if db.query(Ferment).filter_by(created_by_id=user.id).first():
        return True
    if db.query(Batch).filter_by(created_by_id=user.id).first():
        return True
    if db.query(BatchLog).filter_by(logged_by_id=user.id).first():
        return True
    return False


# ── List ───────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
def users_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    q: Optional[str] = None,
    sort: Optional[str] = None,
    dir: Optional[str] = None,
):
    sort_by  = sort or "username"
    sort_dir = dir  or "asc"

    query = db.query(User)
    if q:
        query = query.filter(User.username.ilike(f"%{q}%") | User.email.ilike(f"%{q}%"))

    sort_map = {
        "username": User.username,
        "email":    User.email,
        "role":     User.role,
        "status":   User.is_active,
        "created":  User.created_at,
    }
    col = sort_map.get(sort_by, User.username)
    query = query.order_by(col.asc() if sort_dir == "asc" else col.desc())
    users = query.all()

    return templates.TemplateResponse(request, "users/list.html", {
        "current_user": current_user,
        "users": users,
        "q": q or "",
        "sort": sort_by,
        "dir": sort_dir,
    })


# ── New ────────────────────────────────────────────────────────────────────

@router.get("/new", response_class=HTMLResponse)
def users_new(
    request: Request,
    current_user: User = Depends(require_admin),
):
    return templates.TemplateResponse(request, "users/new.html", {
        "current_user": current_user,
        "roles": ROLES,
        "errors": {},
    })


@router.post("/new")
def users_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
):
    errors = {}
    if not username.strip():
        errors["username"] = "Username is required."
    if not email.strip():
        errors["email"] = "Email is required."
    if len(password) < 8:
        errors["password"] = "Password must be at least 8 characters."
    if role not in ROLES:
        errors["role"] = "Invalid role."
    if db.query(User).filter_by(username=username.strip()).first():
        errors["username"] = f"Username '{username.strip()}' is already taken."
    if db.query(User).filter_by(email=email.strip()).first():
        errors["email"] = "This email is already registered."

    if errors:
        return templates.TemplateResponse(request, "users/new.html", {
            "current_user": current_user, "roles": ROLES, "errors": errors,
        }, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    db.add(User(
        username=username.strip(),
        email=email.strip(),
        hashed_password=hash_password(password),
        role=UserRole(role),
        is_active=True,
    ))
    db.commit()
    return RedirectResponse("/users", status_code=status.HTTP_303_SEE_OTHER)


# ── Edit (admin) ───────────────────────────────────────────────────────────

# ── Profile (own page) ────────────────────────────────────────────────────

@router.get("/me", response_class=HTMLResponse)
def profile_page(
    request: Request,
    current_user: User = Depends(require_user),
):
    role_descriptions = {
        "admin":  "Full access. Can manage users, lookup tables, create and delete anything. Cannot be restricted.",
        "editor": "Can create and edit ferments, batches, ingredients, additives, log entries, and schedules. Cannot manage users or lookup tables.",
        "viewer": "Read-only access. Can view all ferments and their logs but cannot create or change anything.",
    }
    return templates.TemplateResponse(request, "users/profile.html", {
        "current_user": current_user,
        "role_description": role_descriptions.get(current_user.role.value, ""),
        "errors": {},
        "success": False,
    })


# ── Change own password ────────────────────────────────────────────────────

@router.get("/me/password", response_class=HTMLResponse)
def password_change_page(request: Request, current_user: User = Depends(require_user)):
    return RedirectResponse("/users/me", status_code=status.HTTP_302_FOUND)


@router.post("/me/password")
def password_change(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    errors = {}
    if not verify_password(current_password, current_user.hashed_password):
        errors["current_password"] = "Current password is incorrect."
    if len(new_password) < 8:
        errors["new_password"] = "New password must be at least 8 characters."
    if new_password != confirm_password:
        errors["confirm_password"] = "Passwords do not match."

    if errors:
        return templates.TemplateResponse(request, "users/password.html", {
            "current_user": current_user, "errors": errors, "success": False,
        }, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    user = db.query(User).filter_by(id=current_user.id).first()
    user.hashed_password = hash_password(new_password)
    db.commit()
    return templates.TemplateResponse(request, "users/profile.html", {
        "current_user": current_user,
        "role_description": {
            "admin":  "Full access. Can manage users, lookup tables, create and delete anything.",
            "editor": "Can create and edit ferments, batches, ingredients, additives, log entries, and schedules.",
            "viewer": "Read-only access. Cannot create or change anything.",
        }.get(current_user.role.value, ""),
        "errors": {}, "success": True,
    })



@router.get("/{user_id}", response_class=HTMLResponse)
def users_detail(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return RedirectResponse("/users", status_code=status.HTTP_302_FOUND)

    from sqlalchemy.orm import joinedload
    from app.models.lookup import Category, Status

    ferments = (db.query(Ferment)
        .filter_by(created_by_id=user.id)
        .options(joinedload(Ferment.category), joinedload(Ferment.status))
        .order_by(Ferment.created_at.desc()).all())

    batches  = (db.query(Batch)
        .filter_by(created_by_id=user.id)
        .options(joinedload(Batch.ferment))
        .order_by(Batch.created_at.desc()).all())

    logs     = (db.query(BatchLog)
        .filter_by(logged_by_id=user.id)
        .options(joinedload(BatchLog.batch))
        .order_by(BatchLog.logged_at.desc())
        .limit(20).all())

    return templates.TemplateResponse(request, "users/detail.html", {
        "current_user": current_user,
        "user": user,
        "ferments": ferments,
        "batches": batches,
        "logs": logs,
        "has_content": _user_has_content(db, user),
        "role_descriptions": {
            "admin":  "Full access. Can manage users, lookup tables, create and delete anything.",
            "editor": "Can create and edit ferments, batches, ingredients, additives, log entries, and schedules.",
            "viewer": "Read-only access. Cannot create or change anything.",
        },
    })


@router.get("/{user_id}/edit", response_class=HTMLResponse)
def users_edit(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return RedirectResponse("/users", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request, "users/edit.html", {
        "current_user": current_user,
        "user": user,
        "roles": ROLES,
        "errors": {},
        "has_content": _user_has_content(db, user),
    })


@router.post("/{user_id}/edit")
def users_update(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    email: str = Form(...),
    role: str = Form(...),
    is_active: Optional[str] = Form(None),
    new_password: Optional[str] = Form(None),
):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return RedirectResponse("/users", status_code=status.HTTP_302_FOUND)

    errors = {}
    if not email.strip():
        errors["email"] = "Email is required."
    if role not in ROLES:
        errors["role"] = "Invalid role."
    if new_password and len(new_password) < 8:
        errors["new_password"] = "Password must be at least 8 characters."

    # Prevent admin from deactivating themselves
    if user.id == current_user.id and not is_active:
        errors["is_active"] = "You cannot deactivate your own account."

    # Prevent changing the only admin's role
    if user.id == current_user.id and role != UserRole.admin.value:
        admin_count = db.query(User).filter_by(role=UserRole.admin, is_active=True).count()
        if admin_count <= 1:
            errors["role"] = "Cannot change role — you are the only active admin."

    if errors:
        return templates.TemplateResponse(request, "users/edit.html", {
            "current_user": current_user, "user": user, "roles": ROLES,
            "errors": errors, "has_content": _user_has_content(db, user),
        }, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    user.email = email.strip()
    user.role = UserRole(role)
    user.is_active = bool(is_active)
    if new_password:
        user.hashed_password = hash_password(new_password)
    db.commit()
    return RedirectResponse("/users", status_code=status.HTTP_303_SEE_OTHER)


# ── Deactivate (soft delete) ───────────────────────────────────────────────

@router.post("/{user_id}/deactivate")
def users_deactivate(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return RedirectResponse("/users", status_code=status.HTTP_302_FOUND)
    if user.id == current_user.id:
        return RedirectResponse("/users?error=self", status_code=status.HTTP_303_SEE_OTHER)
    user.is_active = False
    db.commit()
    return RedirectResponse("/users", status_code=status.HTTP_303_SEE_OTHER)


# ── Hard delete ────────────────────────────────────────────────────────────

@router.post("/{user_id}/delete")
def users_delete(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return RedirectResponse("/users", status_code=status.HTTP_302_FOUND)
    if user.id == current_user.id:
        return RedirectResponse("/users?error=self", status_code=status.HTTP_303_SEE_OTHER)
    if _user_has_content(db, user):
        return RedirectResponse("/users?error=has_content", status_code=status.HTTP_303_SEE_OTHER)
    db.delete(user)
    db.commit()
    return RedirectResponse("/users", status_code=status.HTTP_303_SEE_OTHER)