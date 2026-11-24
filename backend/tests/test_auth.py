from app.core.database import SessionLocal
from app.core.security import verify_password
from app.models import User

from tests.conftest import auth_header, register


def test_register_login_and_password_is_hashed(client):
    created = register(client)
    assert created["access_token"]
    assert created["user"]["email"] == "user@example.com"
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "user@example.com").one()
        assert user.password_hash != "secret123"
        assert verify_password("secret123", user.password_hash)
        assert user.profile is not None
    finally:
        db.close()

    login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "secret123"})
    assert login.status_code == 200
    me = client.get("/api/v1/users/me", headers=auth_header(login.json()["access_token"]))
    assert me.status_code == 200
    assert me.json()["profile"]["display_name"] == ""


def test_duplicate_email_and_password_rules(client):
    register(client)
    again = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "secret123", "confirm_password": "secret123"},
    )
    assert again.status_code == 400
    weak = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "password", "confirm_password": "password"},
    )
    assert weak.status_code == 422
    mismatch = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "secret123", "confirm_password": "secret456"},
    )
    assert mismatch.status_code == 422


def test_disabled_user_cannot_login(client):
    register(client)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "user@example.com").one()
        user.status = "disabled"
        db.commit()
    finally:
        db.close()
    response = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "secret123"})
    assert response.status_code == 403


def test_refresh_rotates_and_logout_revokes_session(client):
    created = register(client)
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": created["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != created["refresh_token"]
    old = client.post("/api/v1/auth/refresh", json={"refresh_token": created["refresh_token"]})
    assert old.status_code == 401

    me = client.get("/api/v1/users/me", headers=auth_header(refreshed.json()["access_token"]))
    assert me.status_code == 200
    logout = client.post(
        "/api/v1/auth/logout",
        headers=auth_header(refreshed.json()["access_token"]),
        json={"refresh_token": refreshed.json()["refresh_token"]},
    )
    assert logout.status_code == 200
    denied = client.get("/api/v1/users/me", headers=auth_header(refreshed.json()["access_token"]))
    assert denied.status_code == 401


def test_sessions_are_isolated_and_refresh_marks_old_session_revoked(client):
    first = register(client, "a@example.com")
    second = register(client, "b@example.com")
    mine = client.get("/api/v1/auth/sessions", headers=auth_header(first["access_token"]))
    assert mine.status_code == 200
    assert len(mine.json()) == 1
    assert mine.json()[0]["current"] is True
    assert mine.json()[0]["revoked"] is False
    other = client.get("/api/v1/auth/sessions", headers=auth_header(second["access_token"]))
    assert other.status_code == 200
    assert {item["id"] for item in other.json()}.isdisjoint({item["id"] for item in mine.json()})

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert refreshed.status_code == 200
    listed = client.get("/api/v1/auth/sessions", headers=auth_header(refreshed.json()["access_token"]))
    assert listed.status_code == 200
    revoked = [item for item in listed.json() if item["revoked"]]
    current = [item for item in listed.json() if item["current"]]
    assert len(revoked) == 1
    assert revoked[0]["current"] is False
    assert len(current) == 1
    assert current[0]["revoked"] is False


def test_change_password_keeps_current_session_and_revokes_others(client):
    created = register(client)
    other = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "secret123"})
    assert other.status_code == 200
    wrong = client.post(
        "/api/v1/auth/change-password",
        headers=auth_header(created["access_token"]),
        json={"old_password": "wrong123", "new_password": "newsecret1", "confirm_password": "newsecret1"},
    )
    assert wrong.status_code == 400
    changed = client.post(
        "/api/v1/auth/change-password",
        headers=auth_header(created["access_token"]),
        json={"old_password": "secret123", "new_password": "newsecret1", "confirm_password": "newsecret1"},
    )
    assert changed.status_code == 200
    old_login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "secret123"})
    assert old_login.status_code == 400
    new_login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "newsecret1"})
    assert new_login.status_code == 200
    stale = client.post("/api/v1/auth/refresh", json={"refresh_token": other.json()["refresh_token"]})
    assert stale.status_code == 401
    me = client.get("/api/v1/users/me", headers=auth_header(created["access_token"]))
    assert me.status_code == 200


def test_profile_update_and_cross_user_isolation(client):
    first = register(client, "a@example.com")
    updated = client.put(
        "/api/v1/users/me",
        headers=auth_header(first["access_token"]),
        json={"display_name": "张三", "city": "上海", "target_role": "前端工程师", "years_experience": "1", "phone": "", "bio": ""},
    )
    assert updated.status_code == 200
    assert updated.json()["profile"]["display_name"] == "张三"

    second = register(client, "b@example.com")
    missing = client.get("/api/v1/resumes/1", headers=auth_header(second["access_token"]))
    assert missing.status_code == 404
