from __future__ import annotations

from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_session, hash_password, normalize_email, revoke_session, sync_admin_status, verify_password
from app.database import get_db
from app.dependencies import get_current_user_optional, get_settings, render_template, verify_csrf
from app.models import User
from app.services.identity import make_account_code


router = APIRouter()


def validate_credentials(email: str, password: str, username: str | None = None) -> str | None:
    if "@" not in email or len(email) > 255:
        return "Please enter a valid email address."
    if len(password) < 8:
        return "Passwords must be at least 8 characters."
    if username is not None:
        trimmed = username.strip()
        if len(trimmed) < 2 or len(trimmed) > 48:
            return "Username must be between 2 and 48 characters."
    return None


@router.post("/signup")
async def signup(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    username: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    if current_user:
        return RedirectResponse(url="/app", status_code=status.HTTP_303_SEE_OTHER)

    verify_csrf(request, csrf_token)
    error = validate_credentials(email, password, username)
    if error:
        return render_template(
            request,
            "signup.html",
            {"error": error, "form_data": {"email": email, "username": username}},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    normalized_email = normalize_email(email)
    user = User(
        email=normalized_email,
        username=username.strip(),
        account_code=make_account_code(db),
        password_hash=hash_password(password),
        is_admin=normalized_email == request.app.state.settings.admin_email,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render_template(
            request,
            "signup.html",
            {"error": "That email already has an account.", "form_data": {"email": email, "username": username}},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return RedirectResponse(url="/login?notice=Account+created.+Sign+in+to+continue.", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    settings=Depends(get_settings),
):
    verify_csrf(request, csrf_token)
    normalized_email = normalize_email(email)
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None or not verify_password(password, user.password_hash):
        return render_template(
            request,
            "login.html",
            {"error": "Incorrect email or password.", "form_data": {"email": email}},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    sync_admin_status(db, user, settings)
    token = create_session(db, user, settings)
    response = RedirectResponse(url="/app", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=settings.session_ttl_hours * 3600,
    )
    return response


@router.post("/logout")
async def logout(
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    settings=Depends(get_settings),
):
    verify_csrf(request, csrf_token)
    token = request.cookies.get(settings.session_cookie_name)
    revoke_session(db, token)
    response = RedirectResponse(url="/login?notice=Signed+out.", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(settings.session_cookie_name)
    return response


