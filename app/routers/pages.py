from __future__ import annotations

from fastapi import APIRouter, Depends, Request # type: ignore
from fastapi.responses import RedirectResponse # type: ignore
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_optional, render_template
from app.models import User
from app.services.groups import get_room_data, list_groups_for_user


router = APIRouter()


@router.get("/")
async def home(request: Request, user: User | None = Depends(get_current_user_optional)) -> RedirectResponse:
    return RedirectResponse(url="/app" if user else "/login", status_code=303)


@router.get("/signup")
async def signup_page(request: Request, user: User | None = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url="/app", status_code=303)
    return render_template(
        request,
        "signup.html",
        {"notice": request.query_params.get("notice"), "error": request.query_params.get("error")},
    )


@router.get("/login")
async def login_page(request: Request, user: User | None = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url="/app", status_code=303)
    return render_template(
        request,
        "login.html",
        {"notice": request.query_params.get("notice"), "error": request.query_params.get("error")},
    )


@router.get("/app")
async def app_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    groups = list_groups_for_user(db, user)
    return render_template(
        request,
        "app.html",
        {
            "groups": groups,
            "notice": request.query_params.get("notice"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/groups/{group_id}")
async def group_room(
    request: Request,
    group_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    room = get_room_data(db, group_id, user)
    if room is None:
        return RedirectResponse(url="/app?error=You+do+not+have+access+to+that+group.", status_code=303)

    groups = list_groups_for_user(db, user)
    return render_template(
        request,
        "group.html",
        {
            "groups": groups,
            "room": room,
            "notice": request.query_params.get("notice"),
        },
    )


@router.get("/settings")
async def settings_page(request: Request, user: User | None = Depends(get_current_user_optional)):
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    return render_template(
        request,
        "settings.html",
        {"notice": request.query_params.get("notice"), "error": request.query_params.get("error")},
    )


@router.get("/admin/accounts")
async def admin_accounts(
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    if not user.is_admin:
        return RedirectResponse(url="/app?error=Admin+access+required.", status_code=303)

    from sqlalchemy import select

    accounts = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return render_template(
        request,
        "admin_accounts.html",
        {"accounts": accounts, "notice": request.query_params.get("notice")},
    )