"""
Authentication utilities.
- Password hashing with bcrypt
- Signed cookie sessions with itsdangerous
- FastAPI dependency for getting the current user
"""

import json
from typing import Optional

import bcrypt
from fastapi import Cookie, Depends, HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole

# ── Password ───────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Session cookie ─────────────────────────────────────────────────────────

_serializer = URLSafeTimedSerializer(settings.SECRET_KEY)
COOKIE_NAME = "ferm_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def create_session_cookie(user_id: int) -> str:
    """Return a signed, tamper-proof cookie value containing the user id."""
    return _serializer.dumps({"user_id": user_id})


def decode_session_cookie(cookie: str) -> Optional[int]:
    """
    Decode and verify the cookie. Returns user_id or None if invalid/expired.
    Max age: 7 days.
    """
    try:
        data = _serializer.loads(cookie, max_age=COOKIE_MAX_AGE)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None


# ── Dependencies ───────────────────────────────────────────────────────────

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Soft dependency — returns User or None.
    Use this for pages that work for both logged-in and anonymous users.
    """
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return None
    user_id = decode_session_cookie(cookie)
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id, User.is_active == True).first()


def require_user(
    current_user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    Hard dependency — redirects to login if not authenticated.
    Use this on all protected routes.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return current_user


def require_admin(
    current_user: User = Depends(require_user),
) -> User:
    """Hard dependency — 403 if user is not admin."""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


def require_editor(
    current_user: User = Depends(require_user),
) -> User:
    """Hard dependency — 403 if user is viewer only."""
    if current_user.role == UserRole.viewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editor access required.",
        )
    return current_user