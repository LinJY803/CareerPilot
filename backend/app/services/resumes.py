import re
import shutil
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_owned_resume
from app.core.config import settings
from app.core.errors import AppError
from app.models import (
    Resume,
    ResumeAnalysisReport,
    ResumeEducation,
    ResumeExperience,
    ResumeProject,
    ResumeSkill,
    ResumeVersion,
    User,
)
from app.parsers.extract import validate_resume_file
from app.services.tasks import enqueue_task


def _safe_filename(name: str) -> str:
    base = Path(name or "resume").name
    cleaned = re.sub(r"[^\w.\-\u4e00-\u9fff]", "_", base)
    return (cleaned or "resume")[:180]


def list_resumes(db: Session, user_id: int) -> list[Resume]:
    return db.query(Resume).filter(Resume.user_id == user_id).order_by(Resume.created_at.desc()).all()


def get_resume_detail(db: Session, user_id: int, resume_id: int) -> tuple[Resume, ResumeVersion | None]:
    resume = get_owned_resume(db, user_id, resume_id)
    version = None
    if resume.current_version_id:
        version = (
            db.query(ResumeVersion)
            .options(
                selectinload(ResumeVersion.educations),
                selectinload(ResumeVersion.experiences),
                selectinload(ResumeVersion.projects),
                selectinload(ResumeVersion.skills),
            )
            .filter(ResumeVersion.id == resume.current_version_id)
            .first()
        )
    return resume, version


async def create_resume(db: Session, user: User, upload: UploadFile, title: str) -> tuple[Resume, str]:
    filename = _safe_filename(upload.filename or "")
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        file_type = "pdf"
    elif suffix == ".docx":
        file_type = "docx"
    else:
        raise AppError("只支持 PDF 和 DOCX", 400)
    content = await upload.read()
    if not content:
        raise AppError("文件为空", 400)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise AppError(f"文件不能超过 {settings.max_upload_mb} MB", 400)
    resume = Resume(
        user_id=user.id,
        title=(title or Path(filename).stem or "未命名简历")[:255],
        original_filename=filename,
        file_type=file_type,
        file_size=len(content),
        parse_status="pending",
        diagnosis_status="none",
    )
    db.add(resume)
    db.flush()
    relative = Path("resumes") / str(user.id) / str(resume.id) / f"original.{file_type}"
    absolute = Path(settings.upload_dir) / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_bytes(content)
    try:
        validate_resume_file(absolute, file_type)
    except Exception:
        shutil.rmtree(absolute.parent, ignore_errors=True)
        db.rollback()
        raise
    resume.file_path = relative.as_posix()
    task = enqueue_task(db, user.id, "resume_parse", "resume", resume.id)
    db.commit()
    db.refresh(resume)
    return resume, task.id


def request_parse(db: Session, user: User, resume_id: int):
    from app.models import AITask

    resume = get_owned_resume(db, user.id, resume_id)
    inflight = (
        db.query(AITask)
        .filter(
            AITask.user_id == user.id,
            AITask.task_type == "resume_parse",
            AITask.resource_id == str(resume.id),
            AITask.status.in_(["PENDING", "PROCESSING"]),
        )
        .order_by(AITask.created_at.desc())
        .first()
    )
    if inflight:
        return inflight
    resume.parse_status = "pending"
    resume.parse_error = ""
    task = enqueue_task(db, user.id, "resume_parse", "resume", resume.id)
    db.commit()
    return task


def update_resume_title(db: Session, user: User, resume_id: int, title: str) -> Resume:
    resume = get_owned_resume(db, user.id, resume_id)
    resume.title = title
    db.commit()
    db.refresh(resume)
    return resume


def delete_resume(db: Session, user: User, resume_id: int) -> None:
    resume = get_owned_resume(db, user.id, resume_id)
    folder = Path(settings.upload_dir) / "resumes" / str(user.id) / str(resume.id)
    db.query(ResumeAnalysisReport).filter(ResumeAnalysisReport.resume_id == resume.id).delete()
    from app.models import JobMatchReport, ResumeOptimization

    db.query(JobMatchReport).filter(JobMatchReport.resume_id == resume.id, JobMatchReport.user_id == user.id).delete()
    db.query(ResumeOptimization).filter(
        ResumeOptimization.resume_id == resume.id, ResumeOptimization.user_id == user.id
    ).delete()
    db.delete(resume)
    db.commit()
    shutil.rmtree(folder, ignore_errors=True)


def latest_analysis(db: Session, user_id: int, resume_id: int) -> ResumeAnalysisReport | None:
    get_owned_resume(db, user_id, resume_id)
    return (
        db.query(ResumeAnalysisReport)
        .filter(ResumeAnalysisReport.user_id == user_id, ResumeAnalysisReport.resume_id == resume_id)
        .order_by(ResumeAnalysisReport.created_at.desc())
        .first()
    )


def save_parsed_version(db: Session, resume: Resume, raw_text: str, parsed: dict, source: str) -> ResumeVersion:
    from sqlalchemy import func

    max_no = db.query(func.max(ResumeVersion.version_no)).filter(ResumeVersion.resume_id == resume.id).scalar() or 0
    basic = parsed.get("basic") or {}
    version = ResumeVersion(
        resume_id=resume.id,
        version_no=int(max_no) + 1,
        source=source,
        raw_text=raw_text,
        candidate_name=basic.get("name") or "",
        email=basic.get("email") or "",
        phone=basic.get("phone") or "",
        city=basic.get("city") or "",
    )
    db.add(version)
    db.flush()
    for item in parsed.get("educations") or []:
        db.add(
            ResumeEducation(
                version_id=version.id,
                school=item.get("school") or "",
                major=item.get("major") or "",
                degree=item.get("degree") or "",
                start_date=item.get("start_date") or "",
                end_date=item.get("end_date") or "",
            )
        )
    for item in parsed.get("experiences") or []:
        db.add(
            ResumeExperience(
                version_id=version.id,
                company=item.get("company") or "",
                title=item.get("title") or "",
                start_date=item.get("start_date") or "",
                end_date=item.get("end_date") or "",
                content=item.get("content") or "",
            )
        )
    for item in parsed.get("projects") or []:
        db.add(
            ResumeProject(
                version_id=version.id,
                name=item.get("name") or "",
                background=item.get("background") or "",
                tech_stack=item.get("tech_stack") or "",
                responsibilities=item.get("responsibilities") or "",
                achievements=item.get("achievements") or "",
            )
        )
    for item in parsed.get("skills") or []:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        db.add(
            ResumeSkill(
                version_id=version.id,
                name=name[:100],
                proficiency=item.get("proficiency") or "",
                description=item.get("description") or "",
            )
        )
    db.flush()
    return version
