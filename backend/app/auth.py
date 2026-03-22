from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import Cookie, Depends, HTTPException, Response, status

from . import db
from .config import settings
from .utils import utc_now, utc_now_iso


def create_session(response: Response, username: str, role: str) -> dict[str, str]:
    db.delete_expired_sessions(utc_now_iso())
    token = secrets.token_urlsafe(32)
    expires_at = (utc_now() + timedelta(hours=settings.session_ttl_hours)).isoformat()
    db.create_session(token, username, role, expires_at)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.secure_cookie,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    return {"username": username, "role": role, "expires_at": expires_at}


def clear_session(response: Response, token: str | None) -> None:
    if token:
        db.delete_session(token)
    response.delete_cookie(settings.session_cookie_name, path="/")


def require_session(session_token: str | None = Cookie(default=None, alias=settings.session_cookie_name)) -> dict[str, str]:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    db.delete_expired_sessions(utc_now_iso())
    session = db.get_session(session_token)
    if session is None or session["expires_at"] <= utc_now_iso():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return {
        "username": session["username"],
        "role": session["role"],
        "expires_at": session["expires_at"],
        "token": session_token,
    }


def require_admin(session_data: dict[str, str] = Depends(require_session)) -> dict[str, str]:
    if session_data["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return session_data


def require_user(session_data: dict[str, str] = Depends(require_session)) -> dict[str, str]:
    if session_data["role"] != "user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return session_data
