from __future__ import annotations

import re

from sqlalchemy import select

from app import database
from app.models import Group, GroupMembership, User


def get_csrf(client, path: str) -> str:
    client.get(path)
    return client.cookies.get("polkhol_csrf")


def signup(client, email: str, username: str, password: str = "supersecret"):
    csrf = get_csrf(client, "/signup")
    return client.post(
        "/signup",
        data={
            "email": email,
            "username": username,
            "password": password,
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )


def login(client, email: str, password: str = "supersecret"):
    csrf = get_csrf(client, "/login")
    return client.post(
        "/login",
        data={"email": email, "password": password, "csrf_token": csrf},
        follow_redirects=False,
    )


def session_scope():
    session_factory = database.SessionLocal
    assert session_factory is not None
    return session_factory()


def get_user(email: str) -> User:
    with session_scope() as db:
        return db.scalar(select(User).where(User.email == email))


def get_group_by_title(title: str) -> Group:
    with session_scope() as db:
        return db.scalar(select(Group).where(Group.title == title))


def get_membership(group_id: int, user_id: int) -> GroupMembership:
    with session_scope() as db:
        return db.scalar(
            select(GroupMembership)
            .where(GroupMembership.group_id == group_id)
            .where(GroupMembership.user_id == user_id)
        )


def test_signup_login_logout_duplicate_email_and_admin_bootstrap(client):
    signup_response = signup(client, "owner@example.com", "Owner Name")
    assert signup_response.status_code == 303
    assert signup_response.headers["location"] == "/login?notice=Account+created.+Sign+in+to+continue."

    duplicate_response = signup(client, "owner@example.com", "Owner Name")
    assert duplicate_response.status_code == 400
    assert "That email already has an account." in duplicate_response.text

    login_response = login(client, "owner@example.com")
    assert login_response.status_code == 303
    assert login_response.headers["location"] == "/app"
    assert client.cookies.get("polkhol_session")

    admin_page = client.get("/admin/accounts")
    assert admin_page.status_code == 200
    assert "owner@example.com" in admin_page.text
    assert "Owner" in admin_page.text

    csrf = client.cookies.get("polkhol_csrf")
    logout_response = client.post("/logout", data={"csrf_token": csrf}, follow_redirects=False)
    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/login?notice=Signed+out."

    redirected = client.get("/app", follow_redirects=False)
    assert redirected.status_code == 303
    assert redirected.headers["location"] == "/login"


def test_duplicate_usernames_username_reset_and_alias_persistence(client):
    signup(client, "alpha@example.com", "Same Name")
    signup(client, "beta@example.com", "Same Name")

    beta_user = get_user("beta@example.com")
    login(client, "alpha@example.com")

    csrf = client.cookies.get("polkhol_csrf")
    create_response = client.post(
        "/groups",
        data={
            "title": "Cipher Circle",
            "member_codes": [beta_user.account_code],
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert create_response.status_code == 303

    group = get_group_by_title("Cipher Circle")
    alpha_user = get_user("alpha@example.com")
    membership = get_membership(group.id, alpha_user.id)
    original_alias = membership.alias

    room_page = client.get(f"/groups/{group.id}")
    assert room_page.status_code == 200
    assert original_alias in room_page.text
    assert "Same Name" not in room_page.text
    assert "alpha@example.com" not in room_page.text
    assert "beta@example.com" not in room_page.text

    csrf = client.cookies.get("polkhol_csrf")
    rename_response = client.post(
        "/account/username",
        data={"username": "Renamed User", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert rename_response.status_code == 303

    csrf = client.cookies.get("polkhol_csrf")
    reset_response = client.post("/account/username/reset", data={"csrf_token": csrf}, follow_redirects=False)
    assert reset_response.status_code == 303

    updated_user = get_user("alpha@example.com")
    assert updated_user.username != "Renamed User"

    refreshed_room_page = client.get(f"/groups/{group.id}")
    assert refreshed_room_page.status_code == 200
    assert original_alias in refreshed_room_page.text
    assert updated_user.username not in refreshed_room_page.text


def test_search_add_members_and_room_access_control(client):
    signup(client, "creator@example.com", "Host User")
    signup(client, "member@example.com", "Shared Name")
    signup(client, "other@example.com", "Shared Name")

    member_user = get_user("member@example.com")
    login(client, "creator@example.com")

    search_response = client.get("/users/search", params={"q": "Shared"})
    assert search_response.status_code == 200
    payload = search_response.json()["results"]
    assert any(result["account_code"] == member_user.account_code for result in payload)
    assert all(sorted(result.keys()) == ["account_code", "username"] for result in payload)
    assert "email" not in search_response.text
    assert '"id"' not in search_response.text

    csrf = client.cookies.get("polkhol_csrf")
    client.post("/groups", data={"title": "Late Joiners", "csrf_token": csrf}, follow_redirects=False)
    group = get_group_by_title("Late Joiners")

    csrf = client.cookies.get("polkhol_csrf")
    add_response = client.post(
        f"/groups/{group.id}/members",
        data={"member_codes": [member_user.account_code], "csrf_token": csrf},
        follow_redirects=False,
    )
    assert add_response.status_code == 303

    room_page = client.get(f"/groups/{group.id}")
    assert room_page.status_code == 200
    assert "Shared Name" not in room_page.text
    assert "member@example.com" not in room_page.text

    from fastapi.testclient import TestClient
    from app.main import create_app

    # Reuse the existing app while keeping cookies isolated.
    outsider = TestClient(client.app)
    try:
        login(outsider, "other@example.com")
        outsider_room = outsider.get(f"/groups/{group.id}", follow_redirects=False)
        assert outsider_room.status_code == 303
        assert outsider_room.headers["location"] == "/app?error=You+do+not+have+access+to+that+group."
    finally:
        outsider.close()


def test_websocket_message_flow_and_persistence(client):
    signup(client, "roomowner@example.com", "Room Owner")
    signup(client, "listener@example.com", "Listener")
    listener = get_user("listener@example.com")

    login(client, "roomowner@example.com")
    csrf = client.cookies.get("polkhol_csrf")
    client.post(
        "/groups",
        data={"title": "Socket Room", "member_codes": [listener.account_code], "csrf_token": csrf},
        follow_redirects=False,
    )
    group = get_group_by_title("Socket Room")

    from fastapi.testclient import TestClient

    listener_client = TestClient(client.app)
    try:
        login(listener_client, "listener@example.com")
        room_page = listener_client.get(f"/groups/{group.id}")
        assert room_page.status_code == 200
        assert "listener@example.com" not in room_page.text
        assert "Listener" not in room_page.text

        with listener_client.websocket_connect(f"/ws/groups/{group.id}") as websocket:
            roster_event = websocket.receive_json()
            assert roster_event["type"] == "roster"
            assert isinstance(roster_event["aliases"], list)

            websocket.send_json({"body": "The masks stay on."})
            message_event = websocket.receive_json()
            assert message_event["type"] == "message"
            assert message_event["message"]["body"] == "The masks stay on."
            assert "alias" in message_event["message"]
            assert "Listener" not in str(message_event)
            assert "listener@example.com" not in str(message_event)

        persisted_room = listener_client.get(f"/groups/{group.id}")
        assert "The masks stay on." in persisted_room.text
        assert "Listener" not in persisted_room.text
    finally:
        listener_client.close()