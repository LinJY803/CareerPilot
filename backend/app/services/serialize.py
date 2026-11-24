from app.core.time import utcnow
from app.models import (
    JobMatchReport,
    JobPosition,
    JobRequirement,
    Resume,
    ResumeAnalysisReport,
    ResumeOptimization,
    ResumeVersion,
    User,
    UserSession,
)


def iso(value) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def user_out(user: User) -> dict:
    profile = user.profile
    return {
        "id": user.id,
        "email": user.email,
        "status": user.status,
        "profile": {
            "display_name": profile.display_name if profile else "",
            "phone": profile.phone if profile else "",
            "city": profile.city if profile else "",
            "target_role": profile.target_role if profile else "",
            "years_experience": profile.years_experience if profile else "",
            "bio": profile.bio if profile else "",
        },
    }


def session_out(session: UserSession, current_session_id: int) -> dict:
    return {
        "id": session.id,
        "created_at": iso(session.created_at),
        "expires_at": iso(session.expires_at),
        "revoked": session.revoked_at is not None,
        "user_agent": session.user_agent,
        "current": session.id == current_session_id,
    }


def resume_brief(resume: Resume) -> dict:
    return {
        "id": resume.id,
        "title": resume.title,
        "original_filename": resume.original_filename,
        "file_type": resume.file_type,
        "file_size": resume.file_size,
        "parse_status": resume.parse_status,
        "diagnosis_status": resume.diagnosis_status,
        "parse_error": resume.parse_error,
        "current_version_id": resume.current_version_id,
        "created_at": iso(resume.created_at),
    }


def version_out(version: ResumeVersion) -> dict:
    return {
        "id": version.id,
        "version_no": version.version_no,
        "source": version.source,
        "summary": version.summary,
        "raw_text": version.raw_text,
        "basic": {
            "name": version.candidate_name,
            "email": version.email,
            "phone": version.phone,
            "city": version.city,
        },
        "educations": [
            {
                "id": item.id,
                "school": item.school,
                "major": item.major,
                "degree": item.degree,
                "start_date": item.start_date,
                "end_date": item.end_date,
            }
            for item in version.educations
        ],
        "experiences": [
            {
                "id": item.id,
                "company": item.company,
                "title": item.title,
                "start_date": item.start_date,
                "end_date": item.end_date,
                "content": item.content,
            }
            for item in version.experiences
        ],
        "projects": [
            {
                "id": item.id,
                "name": item.name,
                "background": item.background,
                "tech_stack": item.tech_stack,
                "responsibilities": item.responsibilities,
                "achievements": item.achievements,
            }
            for item in version.projects
        ],
        "skills": [
            {"id": item.id, "name": item.name, "proficiency": item.proficiency, "description": item.description}
            for item in version.skills
        ],
        "created_at": iso(version.created_at),
    }


def report_out(report: ResumeAnalysisReport) -> dict:
    return {
        "id": report.id,
        "resume_id": report.resume_id,
        "resume_version_id": report.resume_version_id,
        "task_id": report.task_id,
        "overall_score": report.overall_score,
        "dimensions": report.dimensions_json or [],
        "issues": report.issues_json or [],
        "suggestions": report.suggestions_json or [],
        "created_at": iso(report.created_at),
    }


def job_brief(job: JobPosition) -> dict:
    return {
        "id": job.id,
        "company_name": job.company_name,
        "title": job.title,
        "city": job.city,
        "salary_range": job.salary_range,
        "experience_requirement": job.experience_requirement,
        "education_requirement": job.education_requirement,
        "parse_status": job.parse_status,
        "parse_error": job.parse_error,
        "created_at": iso(job.created_at),
    }


def requirement_out(requirement: JobRequirement | None) -> dict | None:
    if requirement is None:
        return None
    return {
        "id": requirement.id,
        "responsibilities": requirement.responsibilities_json or [],
        "skills": requirement.skills_json or [],
        "experience_requirement": requirement.experience_requirement,
        "education_requirement": requirement.education_requirement,
        "other_requirements": requirement.other_requirements_json or [],
        "uncertain_fields": requirement.uncertain_fields_json or [],
        "created_at": iso(requirement.created_at),
    }


def match_out(report: JobMatchReport, job_title: str = "", company_name: str = "") -> dict:
    return {
        "id": report.id,
        "resume_id": report.resume_id,
        "resume_version_id": report.resume_version_id,
        "job_id": report.job_id,
        "job_title": job_title or (report.job_snapshot_json or {}).get("title", ""),
        "company_name": company_name or (report.job_snapshot_json or {}).get("company_name", ""),
        "status": report.status,
        "task_id": report.task_id,
        "overall_score": report.overall_score,
        "rule_score": report.rule_score,
        "ai_adjustment": report.ai_adjustment,
        "ai_validated": report.ai_validated,
        "summary": report.summary,
        "dimensions": report.dimension_scores_json or [],
        "skills": report.skill_matches_json or [],
        "evidence": report.evidence_json or [],
        "suggestions": report.suggestions_json or [],
        "score_breakdown": report.score_breakdown_json or {},
        "error_message": report.error_message,
        "created_at": iso(report.created_at),
    }


def optimization_out(row: ResumeOptimization) -> dict:
    return {
        "id": row.id,
        "resume_id": row.resume_id,
        "resume_version_id": row.resume_version_id,
        "project_id": row.project_id,
        "job_id": row.job_id,
        "optimize_type": row.optimize_type,
        "status": row.status,
        "task_id": row.task_id,
        "original_text": row.original_text,
        "optimized_text": row.optimized_text,
        "suggestions": row.suggestions_json or [],
        "saved_version_id": row.saved_version_id,
        "error_message": row.error_message,
        "created_at": iso(row.created_at),
    }


def task_out(task) -> dict:
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "resource_type": task.resource_type,
        "resource_id": task.resource_id,
        "result_ref": task.result_ref,
        "error_message": task.error_message,
        "retry_count": task.retry_count,
        "created_at": iso(task.created_at),
        "updated_at": iso(task.updated_at),
    }


def touch(entity) -> None:
    entity.updated_at = utcnow()
