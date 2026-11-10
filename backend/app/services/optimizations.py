from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_owned_job, get_owned_resume
from app.core.errors import AppError
from app.models import (
    JobPosition,
    Resume,
    ResumeEducation,
    ResumeExperience,
    ResumeOptimization,
    ResumeProject,
    ResumeSkill,
    ResumeVersion,
    User,
)
from app.services.tasks import enqueue_task


def _project_blob(project: ResumeProject) -> str:
    return "\n".join(
        part
        for part in [project.name, project.background, project.tech_stack, project.responsibilities, project.achievements]
        if part
    )


def create_optimization(db: Session, user: User, data: dict) -> ResumeOptimization:
    resume = get_owned_resume(db, user.id, data["resume_id"])
    version = (
        db.query(ResumeVersion)
        .options(selectinload(ResumeVersion.projects))
        .filter(ResumeVersion.id == resume.current_version_id)
        .first()
        if resume.current_version_id
        else None
    )
    if version is None:
        raise AppError("请先完成简历解析", 400)
    optimize_type = data.get("optimize_type") or "project"
    project = None
    if optimize_type == "project":
        if not data.get("project_id"):
            raise AppError("请选择要优化的项目经历", 400)
        project = next((item for item in version.projects if item.id == data["project_id"]), None)
        if project is None:
            raise AppError("项目经历不存在", 404)
        original = _project_blob(project)
    else:
        original = version.raw_text or version.summary
    if not original.strip():
        raise AppError("没有可优化的原文", 400)
    job_id = data.get("job_id")
    if job_id:
        get_owned_job(db, user.id, job_id)
    row = ResumeOptimization(
        user_id=user.id,
        resume_id=resume.id,
        resume_version_id=version.id,
        project_id=project.id if project else None,
        job_id=job_id,
        optimize_type=optimize_type,
        status="pending",
        original_text=original,
    )
    db.add(row)
    db.flush()
    task = enqueue_task(db, user.id, "resume_optimize", "optimization", row.id)
    row.task_id = task.id
    db.commit()
    db.refresh(row)
    return row


def get_optimization(db: Session, user_id: int, optimization_id: int) -> ResumeOptimization:
    row = (
        db.query(ResumeOptimization)
        .filter(ResumeOptimization.id == optimization_id, ResumeOptimization.user_id == user_id)
        .first()
    )
    if row is None:
        raise AppError("优化记录不存在", 404)
    return row


def save_optimization(db: Session, user: User, optimization_id: int) -> ResumeVersion:
    row = get_optimization(db, user.id, optimization_id)
    if row.status != "success":
        raise AppError("优化尚未完成", 400)
    if row.saved_version_id:
        existing = db.get(ResumeVersion, row.saved_version_id)
        if existing:
            return existing
    source = (
        db.query(ResumeVersion)
        .options(
            selectinload(ResumeVersion.educations),
            selectinload(ResumeVersion.experiences),
            selectinload(ResumeVersion.projects),
            selectinload(ResumeVersion.skills),
        )
        .filter(ResumeVersion.id == row.resume_version_id)
        .first()
    )
    if source is None:
        raise AppError("原始简历版本不存在", 404)
    resume = db.get(Resume, source.resume_id)
    if resume is None or resume.user_id != user.id:
        raise AppError("简历不存在", 404)
    max_no = db.query(func.max(ResumeVersion.version_no)).filter(ResumeVersion.resume_id == resume.id).scalar() or 0
    version = ResumeVersion(
        resume_id=resume.id,
        version_no=int(max_no) + 1,
        source="optimization",
        summary=row.optimized_text if row.optimize_type == "expression" else source.summary,
        raw_text=source.raw_text,
        candidate_name=source.candidate_name,
        email=source.email,
        phone=source.phone,
        city=source.city,
    )
    db.add(version)
    db.flush()
    for item in source.educations:
        db.add(
            ResumeEducation(
                version_id=version.id,
                school=item.school,
                major=item.major,
                degree=item.degree,
                start_date=item.start_date,
                end_date=item.end_date,
            )
        )
    for item in source.experiences:
        db.add(
            ResumeExperience(
                version_id=version.id,
                company=item.company,
                title=item.title,
                start_date=item.start_date,
                end_date=item.end_date,
                content=item.content,
            )
        )
    source_project = db.get(ResumeProject, row.project_id) if row.project_id else None
    for item in source.projects:
        responsibilities = item.responsibilities
        if (
            row.optimize_type == "project"
            and source_project is not None
            and item.name == source_project.name
            and item.background == source_project.background
            and item.responsibilities == source_project.responsibilities
            and item.achievements == source_project.achievements
        ):
            responsibilities = row.optimized_text
        db.add(
            ResumeProject(
                version_id=version.id,
                name=item.name,
                background=item.background,
                tech_stack=item.tech_stack,
                responsibilities=responsibilities,
                achievements=item.achievements,
            )
        )
    for item in source.skills:
        db.add(
            ResumeSkill(
                version_id=version.id,
                name=item.name,
                proficiency=item.proficiency,
                description=item.description,
            )
        )
    row.saved_version_id = version.id
    resume.current_version_id = version.id
    db.commit()
    db.refresh(version)
    return version


def job_context(db: Session, job_id: int | None) -> str:
    if not job_id:
        return ""
    job = db.get(JobPosition, job_id)
    if job is None:
        return ""
    return job.raw_jd or ""
