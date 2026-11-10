from sqlalchemy.orm import Session

from app.api.deps import get_owned_job, get_owned_resume
from app.core.errors import AppError
from app.models import JobMatchReport, ResumeVersion, User
from app.services.jobs import latest_requirement
from app.services.serialize import match_out
from app.services.tasks import enqueue_task


def create_match(db: Session, user: User, resume_id: int, job_id: int, resume_version_id: int | None) -> JobMatchReport:
    resume = get_owned_resume(db, user.id, resume_id)
    job = get_owned_job(db, user.id, job_id)
    version_id = resume_version_id or resume.current_version_id
    version = db.get(ResumeVersion, version_id) if version_id else None
    if version is None or version.resume_id != resume.id:
        raise AppError("请先完成简历解析，再发起匹配", 400)
    requirement = latest_requirement(db, job.id)
    if requirement is None:
        raise AppError("请先完成岗位解析，再发起匹配", 400)
    snapshot = {
        "title": job.title,
        "company_name": job.company_name,
        "city": job.city,
        "raw_jd": job.raw_jd,
        "salary_range": job.salary_range,
        "experience_requirement": requirement.experience_requirement or job.experience_requirement,
        "education_requirement": requirement.education_requirement or job.education_requirement,
        "responsibilities": requirement.responsibilities_json or [],
        "skills": requirement.skills_json or [],
        "other_requirements": requirement.other_requirements_json or [],
        "uncertain_fields": requirement.uncertain_fields_json or [],
        "requirement_id": requirement.id,
    }
    report = JobMatchReport(
        user_id=user.id,
        resume_id=resume.id,
        resume_version_id=version.id,
        job_id=job.id,
        status="pending",
        job_snapshot_json=snapshot,
    )
    db.add(report)
    db.flush()
    task = enqueue_task(db, user.id, "job_match", "match", report.id, payload={"report_id": report.id})
    report.task_id = task.id
    db.commit()
    db.refresh(report)
    return report


def get_match(db: Session, user_id: int, report_id: int) -> dict:
    report = db.query(JobMatchReport).filter(JobMatchReport.id == report_id, JobMatchReport.user_id == user_id).first()
    if report is None:
        raise AppError("匹配报告不存在", 404)
    snapshot = report.job_snapshot_json or {}
    return match_out(report, snapshot.get("title", ""), snapshot.get("company_name", ""))


def list_matches(db: Session, user_id: int) -> list[dict]:
    rows = (
        db.query(JobMatchReport)
        .filter(JobMatchReport.user_id == user_id)
        .order_by(JobMatchReport.created_at.desc())
        .limit(50)
        .all()
    )
    result = []
    for report in rows:
        snapshot = report.job_snapshot_json or {}
        result.append(match_out(report, snapshot.get("title", ""), snapshot.get("company_name", "")))
    return result
