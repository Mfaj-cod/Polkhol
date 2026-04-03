from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import get_user_from_token
from app.config import Settings
from app.database import get_db
from app.models import User


TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User | None:
    if getattr(request.state, "user_loaded", False):
        return getattr(request.state, "current_user", None)

    token = request.cookies.get(settings.session_cookie_name)
    user = get_user_from_token(db, token, settings)
    request.state.user_loaded = True
    request.state.current_user = user
    return user


def require_user(user: User | None = Depends(get_current_user_optional)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return user


def ensure_csrf_token(request: Request) -> str:
    settings: Settings = request.app.state.settings
    token = request.cookies.get(settings.csrf_cookie_name)
    if token:
        return token

    token = secrets.token_urlsafe(32)
    request.state.csrf_token = token
    return token


def verify_csrf(request: Request, submitted_token: str | None) -> None:
    settings: Settings = request.app.state.settings
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    if not cookie_token or not submitted_token or cookie_token != submitted_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token.")


def render_template(
    request: Request,
    template_name: str,
    context: dict | None = None,
    status_code: int = status.HTTP_200_OK,
):
    payload = {
        "request": request,
        "app_name": request.app.state.settings.app_name,
        "asset_version": getattr(request.app.state, "asset_version", "dev"),
        "csrf_token": ensure_csrf_token(request),
        "current_user": getattr(request.state, "current_user", None),
    }
    if context:
        payload.update(context)

    response = TEMPLATES.TemplateResponse(request, template_name, payload, status_code=status_code)
    settings: Settings = request.app.state.settings
    if request.cookies.get(settings.csrf_cookie_name) is None:
        response.set_cookie(
            settings.csrf_cookie_name,
            payload["csrf_token"],
            httponly=False,
            samesite="lax",
            secure=False,
        )
    return response


def redirect(url: str, request: Request) -> RedirectResponse:
    response = RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)
    settings: Settings = request.app.state.settings
    if request.cookies.get(settings.csrf_cookie_name) is None:
        response.set_cookie(
            settings.csrf_cookie_name,
            ensure_csrf_token(request),
            httponly=False,
            samesite="lax",
            secure=False,
        )
    return response


