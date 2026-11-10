import hashlib
import re
import secrets
from datetime import timedelta

import bcrypt
import jwt

from app.core.config import settings
from app.core.time import utcnow

PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,64}$")


def validate_password(password: str) -> None:
    if not PASSWORD_PATTERN.fullmatch(password or ""):
        raise ValueError("密码至少 8 位，且必须同时包含字母和数字")


def hash_password(password: str) -> str:
    rounds = 4 if settings.careerpilot_testing else 12
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds))
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(user_id: int, session_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "sid": session_id,
        "type": "access",
        "exp": utcnow() + timedelta(minutes=settings.jwt_access_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise ValueError("登录已失效") from exc
    if payload.get("type") != "access":
        raise ValueError("登录已失效")
    return payload
