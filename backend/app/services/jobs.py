from sqlalchemy.orm import Session

from app.api.deps import get_owned_job
from app.models import JobPosition, JobRequirement, User
from app.services.tasks import enqueue_task


def list_jobs(db: Session, user_id: int) -> list[JobPosition]:
    return db.query(JobPosition).filter(JobPosition.user_id == user_id).order_by(JobPosition.created_at.desc()).all()


def create_job(db: Session, user: User, data: dict) -> tuple[JobPosition, str]:
    job = JobPosition(
        user_id=user.id,
        company_name=(data.get("company_name") or "").strip(),
        title=data["title"].strip(),
        city=(data.get("city") or "").strip(),
        raw_jd=data["raw_jd"].strip(),
        salary_range=(data.get("salary_range") or "").strip(),
        experience_requirement=(data.get("experience_requirement") or "").strip(),
        education_requirement=(data.get("education_requirement") or "").strip(),
        parse_status="pending",
    )
    db.add(job)
    db.flush()
    task = enqueue_task(db, user.id, "job_parse", "job", job.id)
    db.commit()
    db.refresh(job)
    return job, task.id


def request_job_parse(db: Session, user: User, job_id: int):
    job = get_owned_job(db, user.id, job_id)
    from app.models import AITask

    inflight = (
        db.query(AITask)
        .filter(
            AITask.user_id == user.id,
            AITask.task_type == "job_parse",
            AITask.resource_id == str(job.id),
            AITask.status.in_(["PENDING", "PROCESSING"]),
        )
        .first()
    )
    if inflight:
        return inflight
    job.parse_status = "pending"
    job.parse_error = ""
    task = enqueue_task(db, user.id, "job_parse", "job", job.id)
    db.commit()
    return task


def latest_requirement(db: Session, job_id: int) -> JobRequirement | None:
    return (
        db.query(JobRequirement)
        .filter(JobRequirement.job_id == job_id)
        .order_by(JobRequirement.created_at.desc(), JobRequirement.id.desc())
        .first()
    )
