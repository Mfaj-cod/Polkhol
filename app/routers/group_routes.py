from __future__ import annotations

from datetime import timezone
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, Form, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import database
from app.auth import get_user_from_token
from app.database import get_db
from app.dependencies import require_user, verify_csrf
from app.models import User
from app.services.groups import add_members_to_group, create_group, create_message, get_group_aliases, get_membership, search_users


router = APIRouter()


def _format_timestamp(value) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime("%b %d, %Y %I:%M %p")


@router.get("/users/search")
async def user_search(
    q: str = Query(""),
    group_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    return JSONResponse({"results": search_users(db, q, user, group_id)})


@router.post("/groups")
async def create_group_route(
    request: Request,
    title: str = Form(...),
    member_codes: list[str] = Form(default=[]),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    verify_csrf(request, csrf_token)
    try:
        group = create_group(db, user, title, member_codes)
    except ValueError as exc:
        return RedirectResponse(url=f"/app?error={quote_plus(str(exc))}", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url=f"/groups/{group.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/groups/{group_id}/members")
async def add_group_members(
    request: Request,
    group_id: int,
    member_codes: list[str] = Form(default=[]),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    verify_csrf(request, csrf_token)
    try:
        added = add_members_to_group(db, user, group_id, member_codes)
    except (ValueError, PermissionError) as exc:
        return RedirectResponse(url=f"/app?error={quote_plus(str(exc))}", status_code=status.HTTP_303_SEE_OTHER)

    aliases = get_group_aliases(db, group_id)
    await request.app.state.ws_manager.broadcast(group_id, {"type": "roster", "aliases": aliases})
    notice = "Members updated." if added else "No new members were added."
    return RedirectResponse(url=f"/app?notice={quote_plus(notice)}", status_code=status.HTTP_303_SEE_OTHER)


@router.websocket("/ws/groups/{group_id}")
async def group_socket(websocket: WebSocket, group_id: int):
    settings = websocket.app.state.settings
    token = websocket.cookies.get(settings.session_cookie_name)
    session_factory = database.SessionLocal
    if session_factory is None:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    db = session_factory()
    try:
        user = get_user_from_token(db, token, settings)
        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        membership = get_membership(db, group_id, user.id)
        if membership is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        manager = websocket.app.state.ws_manager
        await manager.connect(group_id, websocket)
        await websocket.send_json({"type": "roster", "aliases": get_group_aliases(db, group_id)})

        while True:
            payload = await websocket.receive_json()
            body = str(payload.get("body", "")).strip()
            if not body:
                continue
            if len(body) > settings.max_message_length:
                await websocket.send_json(
                    {"type": "error", "message": f"Messages must be {settings.max_message_length} characters or fewer."}
                )
                continue

            message = create_message(db, membership, body)
            await manager.broadcast(
                group_id,
                {
                    "type": "message",
                    "message": {
                        "alias": membership.alias,
                        "body": message.body,
                        "created_at": _format_timestamp(message.created_at),
                    },
                },
            )
    except WebSocketDisconnect:
        websocket.app.state.ws_manager.disconnect(group_id, websocket)
    finally:
        websocket.app.state.ws_manager.disconnect(group_id, websocket)
        db.close()