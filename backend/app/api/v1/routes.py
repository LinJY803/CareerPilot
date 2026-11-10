from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import AITask, JobMatchReport, JobPosition, Resume, ResumeAnalysisReport, User
from app.schemas.api import JobIn, LoginIn, LogoutIn, MatchIn, OptimizeIn, ProfileIn, RefreshIn, RegisterIn
from app.services.auth_service import login_user, logout_user, refresh_session, register_user, update_profile
from app.services.jobs import create_job, latest_requirement, list_jobs, request_job_parse
from app.services.matches import create_match, get_match, list_matches
from app.services.optimizations import create_optimization, get_optimization, save_optimization
from app.services.resumes import create_resume, delete_resume, get_resume_detail, latest_analysis, list_resumes, request_parse
from app.services.serialize import (
    job_brief,
    optimization_out,
    report_out,
    requirement_out,
    resume_brief,
    task_out,
    user_out,
    version_out,
)
from app.services.tasks import get_owned_task, retry_task, task_runner
from app.api.deps import get_owned_job

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/auth/register")
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    user, tokens = register_user(db, body.email, body.password, request.headers.get("user-agent", ""))
    return {**tokens, "user": user_out(user)}


@router.post("/auth/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    user, tokens = login_user(db, body.email, body.password, request.headers.get("user-agent", ""))
    return {**tokens, "user": user_out(user)}


@router.post("/auth/refresh")
def refresh(body: RefreshIn, request: Request, db: Session = Depends(get_db)):
    return refresh_session(db, body.refresh_token, request.headers.get("user-agent", ""))


@router.post("/auth/logout")
def logout(body: LogoutIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logout_user(db, user, body.refresh_token)
    return {"success": True}


@router.get("/users/me")
def me(user: User = Depends(get_current_user)):
    return user_out(user)


@router.put("/users/me")
def update_me(body: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    updated = update_profile(db, user, body.model_dump())
    return user_out(updated)


@router.get("/dashboard/summary")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resumes = db.query(Resume).filter(Resume.user_id == user.id).order_by(Resume.created_at.desc()).all()
    jobs = db.query(JobPosition).filter(JobPosition.user_id == user.id).count()
    diagnosis_count = db.query(ResumeAnalysisReport).filter(ResumeAnalysisReport.user_id == user.id).count()
    matches = (
        db.query(JobMatchReport)
        .filter(JobMatchReport.user_id == user.id)
        .order_by(JobMatchReport.created_at.desc())
        .limit(5)
        .all()
    )
    return {
        "resume_count": len(resumes),
        "diagnosis_count": diagnosis_count,
        "job_count": jobs,
        "match_count": db.query(JobMatchReport).filter(JobMatchReport.user_id == user.id, JobMatchReport.status == "success").count(),
        "recent_resumes": [resume_brief(item) for item in resumes[:5]],
        "recent_matches": [
            {
                "id": item.id,
                "job_title": (item.job_snapshot_json or {}).get("title", ""),
                "company_name": (item.job_snapshot_json or {}).get("company_name", ""),
                "overall_score": item.overall_score,
                "status": item.status,
                "created_at": item.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if item.created_at else None,
            }
            for item in matches
        ],
    }


@router.post("/resumes")
async def upload_resume(
    file: UploadFile = File(...),
    title: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume, task_id = await create_resume(db, user, file, title.strip())
    await task_runner.submit(task_id)
    return {**resume_brief(resume), "task_id": task_id}


@router.get("/resumes")
def resumes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [resume_brief(item) for item in list_resumes(db, user.id)]


@router.get("/resumes/{resume_id}")
def resume_detail(resume_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume, version = get_resume_detail(db, user.id, resume_id)
    return {**resume_brief(resume), "version": version_out(version) if version else None}


@router.delete("/resumes/{resume_id}")
def remove_resume(resume_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    delete_resume(db, user, resume_id)
    return {"success": True}


@router.post("/resumes/{resume_id}/parse")
async def parse_resume(resume_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = request_parse(db, user, resume_id)
    if task.status in {"PENDING", "PROCESSING"}:
        await task_runner.submit(task.id)
    return task_out(task)


@router.get("/resumes/{resume_id}/analysis")
def resume_analysis(resume_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume, _version = get_resume_detail(db, user.id, resume_id)
    report = latest_analysis(db, user.id, resume_id)
    task = (
        db.query(AITask)
        .filter(AITask.user_id == user.id, AITask.task_type == "resume_diagnosis", AITask.resource_id == str(resume.id))
        .order_by(AITask.created_at.desc())
        .first()
    )
    return {
        "diagnosis_status": resume.diagnosis_status,
        "task": task_out(task) if task else None,
        "report": report_out(report) if report else None,
    }


@router.post("/jobs/match")
async def match_job(body: MatchIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = create_match(db, user, body.resume_id, body.job_id, body.resume_version_id)
    await task_runner.submit(report.task_id)
    return get_match(db, user.id, report.id)


@router.get("/jobs/match")
def match_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_matches(db, user.id)


@router.get("/jobs/match/{report_id}")
def match_detail(report_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_match(db, user.id, report_id)


@router.post("/jobs")
async def add_job(body: JobIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job, task_id = create_job(db, user, body.model_dump())
    await task_runner.submit(task_id)
    return {**job_brief(job), "raw_jd": job.raw_jd, "task_id": task_id}


@router.get("/jobs")
def jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [job_brief(item) for item in list_jobs(db, user.id)]


@router.get("/jobs/{job_id}")
def job_detail(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = get_owned_job(db, user.id, job_id)
    return {**job_brief(job), "raw_jd": job.raw_jd, "requirement": requirement_out(latest_requirement(db, job.id))}


@router.post("/jobs/{job_id}/parse")
async def parse_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = request_job_parse(db, user, job_id)
    if task.status in {"PENDING", "PROCESSING"}:
        await task_runner.submit(task.id)
    return task_out(task)


@router.post("/optimizations")
async def add_optimization(body: OptimizeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = create_optimization(db, user, body.model_dump())
    await task_runner.submit(row.task_id)
    return optimization_out(row)


@router.get("/optimizations/{optimization_id}")
def optimization_detail(optimization_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return optimization_out(get_optimization(db, user.id, optimization_id))


@router.post("/optimizations/{optimization_id}/save")
def save_opt(optimization_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    version = save_optimization(db, user, optimization_id)
    return {"saved_version_id": version.id, "version_no": version.version_no, "resume_id": version.resume_id}


@router.get("/tasks/{task_id}")
def task_detail(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return task_out(get_owned_task(db, user.id, task_id))


@router.post("/tasks/{task_id}/retry")
async def retry(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = retry_task(db, user.id, task_id)
    await task_runner.submit(task.id)
    return task_out(task)
