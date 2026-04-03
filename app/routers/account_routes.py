from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_user, verify_csrf
from app.models import User
from app.services.identity import make_random_username


router = APIRouter()


@router.post("/account/username")
async def update_username(
    request: Request,
    username: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    verify_csrf(request, csrf_token)
    cleaned = username.strip()
    if len(cleaned) < 2 or len(cleaned) > 48:
        return RedirectResponse(
            url="/settings?error=Username+must+be+between+2+and+48+characters.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    user.username = cleaned
    db.commit()
    return RedirectResponse(url="/settings?notice=Username+updated.", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/account/username/reset")
async def reset_username(
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    verify_csrf(request, csrf_token)
    user.username = make_random_username()
    db.commit()
    return RedirectResponse(url="/settings?notice=Username+reset.", status_code=status.HTTP_303_SEE_OTHER)


