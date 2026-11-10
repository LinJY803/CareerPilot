from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    validate_password,
    verify_password,
)
from app.core.time import utcnow
from app.models import User, UserProfile, UserSession


def _issue_session(db: Session, user: User, user_agent: str) -> dict:
    refresh = new_refresh_token()
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_token(refresh),
        expires_at=utcnow() + timedelta(days=settings.jwt_refresh_days),
        user_agent=(user_agent or "")[:255],
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    access = create_access_token(user.id, session.id)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


def register_user(db: Session, email: str, password: str, user_agent: str) -> tuple[User, dict]:
    validate_password(password)
    email = email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise AppError("该邮箱已注册", 400)
    user = User(email=email, password_hash=hash_password(password), status="active")
    user.profile = UserProfile()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, _issue_session(db, user, user_agent)


def login_user(db: Session, email: str, password: str, user_agent: str) -> tuple[User, dict]:
    email = email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.password_hash):
        raise AppError("邮箱或密码错误", 400)
    if user.status != "active":
        raise AppError("账号已被禁用", 403)
    return user, _issue_session(db, user, user_agent)


def refresh_session(db: Session, refresh_token: str, user_agent: str) -> dict:
    token_hash = hash_token(refresh_token)
    session = db.query(UserSession).filter(UserSession.refresh_token_hash == token_hash).first()
    if session is None or session.revoked_at is not None or session.expires_at < utcnow():
        raise AppError("刷新令牌已失效", 401)
    user = db.get(User, session.user_id)
    if user is None or user.status != "active":
        raise AppError("账号不可用", 401)
    session.revoked_at = utcnow()
    db.commit()
    return _issue_session(db, user, user_agent)


def logout_user(db: Session, user: User, refresh_token: str | None) -> None:
    query = db.query(UserSession).filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
    if refresh_token:
        query = query.filter(UserSession.refresh_token_hash == hash_token(refresh_token))
    now = utcnow()
    for session in query.all():
        session.revoked_at = now
    db.commit()


def update_profile(db: Session, user: User, data: dict) -> User:
    profile = user.profile or UserProfile(user_id=user.id)
    for key in ("display_name", "phone", "city", "target_role", "years_experience", "bio"):
        if key in data and data[key] is not None:
            setattr(profile, key, str(data[key]).strip())
    user.profile = profile
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user
