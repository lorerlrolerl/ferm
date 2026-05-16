"""
Auth router — login and logout.
"""

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.templates import templates
from app.auth import (
    COOKIE_NAME,
    COOKIE_MAX_AGE,
    create_session_cookie,
    get_current_user,
    verify_password,
)
from app.database import get_db
from app.models.user import User

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    current_user=Depends(get_current_user),
    error: str = None,
):
    # Already logged in — go to dashboard
    if current_user:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request, "login.html", {"error": error})


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.username == username,
        User.is_active == True,
    ).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid username or password."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_session_cookie(user.id),
        max_age=COOKIE_MAX_AGE,
        httponly=True,   # not accessible via JS
        samesite="lax",  # CSRF protection
        secure=False,    # set True in production with HTTPS
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(COOKIE_NAME)
    return response