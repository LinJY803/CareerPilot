from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.core.time import utcnow
from app.models import JobPosition, Resume, User, UserSession

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AppError("未登录", 401)
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
        session_id = int(payload["sid"])
    except (ValueError, KeyError, TypeError) as exc:
        raise AppError("登录已失效", 401) from exc
    user = db.get(User, user_id)
    session = db.get(UserSession, session_id)
    if user is None or user.status != "active":
        raise AppError("账号不可用", 401)
    if session is None or session.user_id != user.id or session.revoked_at is not None or session.expires_at < utcnow():
        raise AppError("会话已失效", 401)
    return user


def get_owned_resume(db: Session, user_id: int, resume_id: int) -> Resume:
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
    if resume is None:
        raise AppError("简历不存在", 404)
    return resume


def get_owned_job(db: Session, user_id: int, job_id: int) -> JobPosition:
    job = db.query(JobPosition).filter(JobPosition.id == job_id, JobPosition.user_id == user_id).first()
    if job is None:
        raise AppError("岗位不存在", 404)
    return job
