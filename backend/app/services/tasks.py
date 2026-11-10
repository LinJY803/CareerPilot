import asyncio
import logging
from uuid import uuid4

from sqlalchemy.orm import Session, selectinload

from app.ai.client import get_llm_client
from app.ai.guard import (
    evidence_in_source,
    filter_match_judgements,
    ground_parsed_resume,
    has_new_numbers,
    sanitize_diagnosis,
    sanitize_job,
    sanitize_optimization,
)
from app.ai.prompts import diagnosis_prompt, job_prompt, match_prompt, optimize_prompt, parse_prompt
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.errors import AppError, LLMError, LLMNotConfigured
from app.core.time import utcnow
from app.models import (
    AITask,
    JobMatchReport,
    JobPosition,
    JobRequirement,
    Resume,
    ResumeAnalysisReport,
    ResumeOptimization,
    ResumeVersion,
)
from app.parsers.extract import extract_text
from pathlib import Path

from app.services.scoring import (
    DIMENSION_NAMES,
    DIMENSION_WEIGHTS,
    SKILL_WEIGHTS,
    STATUS_POINTS,
    apply_ai_adjustment,
    build_rule_match,
    normalize_skill,
    skill_score,
    weighted_overall,
)

logger = logging.getLogger(__name__)
MAX_RETRY = 3


def enqueue_task(db: Session, user_id: int, task_type: str, resource_type: str, resource_id: int, payload: dict | None = None) -> AITask:
    task = AITask(
        id=str(uuid4()),
        user_id=user_id,
        task_type=task_type,
        status="PENDING",
        resource_type=resource_type,
        resource_id=str(resource_id),
        payload_json=payload or {},
        idempotency_key=f"{user_id}:{task_type}:{resource_type}:{resource_id}",
    )
    db.add(task)
    db.flush()
    return task


def get_owned_task(db: Session, user_id: int, task_id: str) -> AITask:
    task = db.query(AITask).filter(AITask.id == task_id, AITask.user_id == user_id).first()
    if task is None:
        raise AppError("任务不存在", 404)
    return task


def retry_task(db: Session, user_id: int, task_id: str) -> AITask:
    task = get_owned_task(db, user_id, task_id)
    if task.status != "FAILED":
        raise AppError("只有失败的任务可以重试", 400)
    if task.retry_count >= MAX_RETRY:
        raise AppError("已达到重试次数上限", 400)
    task.retry_count += 1
    task.status = "PENDING"
    task.error_message = ""
    task.updated_at = utcnow()
    _reset_resource_pending(db, task)
    db.commit()
    db.refresh(task)
    return task


def _reset_resource_pending(db: Session, task: AITask) -> None:
    if task.task_type == "resume_parse":
        resume = db.get(Resume, int(task.resource_id))
        if resume:
            resume.parse_status = "pending"
            resume.parse_error = ""
    elif task.task_type == "resume_diagnosis":
        resume = db.get(Resume, int(task.resource_id))
        if resume:
            resume.diagnosis_status = "pending"
    elif task.task_type == "job_parse":
        job = db.get(JobPosition, int(task.resource_id))
        if job:
            job.parse_status = "pending"
            job.parse_error = ""
    elif task.task_type == "job_match":
        report = db.get(JobMatchReport, int(task.resource_id))
        if report:
            report.status = "pending"
            report.error_message = ""
    elif task.task_type == "resume_optimize":
        row = db.get(ResumeOptimization, int(task.resource_id))
        if row:
            row.status = "pending"
            row.error_message = ""


def _mark_resource_failed(db: Session, task: AITask) -> None:
    message = task.error_message or "任务执行失败"
    if task.task_type == "resume_parse":
        resume = db.get(Resume, int(task.resource_id))
        if resume:
            resume.parse_status = "failed"
            resume.parse_error = message
    elif task.task_type == "resume_diagnosis":
        resume = db.get(Resume, int(task.resource_id))
        if resume:
            resume.diagnosis_status = "failed"
    elif task.task_type == "job_parse":
        job = db.get(JobPosition, int(task.resource_id))
        if job:
            job.parse_status = "failed"
            job.parse_error = message
    elif task.task_type == "job_match":
        report = db.get(JobMatchReport, int(task.resource_id))
        if report:
            report.status = "failed"
            report.error_message = message
    elif task.task_type == "resume_optimize":
        row = db.get(ResumeOptimization, int(task.resource_id))
        if row:
            row.status = "failed"
            row.error_message = message


def _load_version(db: Session, version_id: int) -> ResumeVersion | None:
    return (
        db.query(ResumeVersion)
        .options(
            selectinload(ResumeVersion.educations),
            selectinload(ResumeVersion.experiences),
            selectinload(ResumeVersion.projects),
            selectinload(ResumeVersion.skills),
        )
        .filter(ResumeVersion.id == version_id)
        .first()
    )


def _version_corpus(version: ResumeVersion) -> str:
    parts = [version.raw_text, version.summary, version.candidate_name, version.email, version.phone, version.city]
    for item in version.educations:
        parts.extend([item.school, item.major, item.degree, item.start_date, item.end_date])
    for item in version.experiences:
        parts.extend([item.company, item.title, item.content])
    for item in version.projects:
        parts.extend([item.name, item.background, item.tech_stack, item.responsibilities, item.achievements])
    for item in version.skills:
        parts.extend([item.name, item.proficiency, item.description])
    return "\n".join(part for part in parts if part)


async def run_resume_parse(db: Session, task: AITask) -> str | None:
    from app.services.resumes import save_parsed_version

    resume = db.get(Resume, int(task.resource_id))
    if resume is None or resume.user_id != task.user_id:
        raise AppError("简历不存在", 404)
    resume.parse_status = "processing"
    db.commit()
    absolute = Path(settings.upload_dir) / resume.file_path
    text = extract_text(absolute, resume.file_type)
    system, user = parse_prompt(text)
    raw = await get_llm_client().complete_json(system, user, task.id, task.user_id)
    parsed = ground_parsed_resume(raw, text)
    version = save_parsed_version(db, resume, text, parsed, "upload")
    resume.current_version_id = version.id
    resume.parse_status = "success"
    resume.parse_error = ""
    task.result_ref = str(version.id)
    diagnosis = enqueue_task(
        db,
        task.user_id,
        "resume_diagnosis",
        "resume",
        resume.id,
        payload={"resume_version_id": version.id},
    )
    resume.diagnosis_status = "pending"
    db.commit()
    return diagnosis.id


async def run_resume_diagnosis(db: Session, task: AITask) -> str | None:
    resume = db.get(Resume, int(task.resource_id))
    if resume is None or resume.user_id != task.user_id:
        raise AppError("简历不存在", 404)
    version_id = (task.payload_json or {}).get("resume_version_id") or resume.current_version_id
    version = _load_version(db, int(version_id)) if version_id else None
    if version is None or version.resume_id != resume.id:
        raise AppError("简历尚未解析", 400)
    resume.diagnosis_status = "processing"
    db.commit()
    source = _version_corpus(version)
    system, user = diagnosis_prompt(source)
    raw = await get_llm_client().complete_json(system, user, task.id, task.user_id)
    cleaned = sanitize_diagnosis(raw, source)
    report = ResumeAnalysisReport(
        user_id=task.user_id,
        resume_id=resume.id,
        resume_version_id=version.id,
        task_id=task.id,
        overall_score=cleaned["overall_score"],
        dimensions_json=cleaned["dimensions"],
        issues_json=cleaned["issues"],
        suggestions_json=cleaned["suggestions"],
    )
    db.add(report)
    db.flush()
    resume.diagnosis_status = "success"
    task.result_ref = str(report.id)
    db.commit()
    return None


async def run_job_parse(db: Session, task: AITask) -> str | None:
    job = db.get(JobPosition, int(task.resource_id))
    if job is None or job.user_id != task.user_id:
        raise AppError("岗位不存在", 404)
    job.parse_status = "processing"
    db.commit()
    system, user = job_prompt(job.raw_jd)
    raw = await get_llm_client().complete_json(system, user, task.id, task.user_id)
    cleaned = sanitize_job(raw, job.raw_jd)
    requirement = JobRequirement(
        job_id=job.id,
        responsibilities_json=cleaned["responsibilities"],
        skills_json=cleaned["skills"],
        experience_requirement=cleaned["experience_requirement"] or job.experience_requirement,
        education_requirement=cleaned["education_requirement"] or job.education_requirement,
        other_requirements_json=cleaned["other_requirements"],
        uncertain_fields_json=cleaned["uncertain_fields"],
    )
    db.add(requirement)
    db.flush()
    job.parse_status = "success"
    job.parse_error = ""
    task.result_ref = str(requirement.id)
    db.commit()
    return None


def _apply_match_ai(rule: dict, raw: dict | None, resume_text: str, job_text: str) -> dict:
    skill_items = [dict(item) for item in rule["skills"]]
    dimensions = dict(rule["dimension_map"])
    notes = dict(rule["notes"])
    ignored = 0
    if raw:
        judgements = filter_match_judgements(raw.get("skill_judgements") or [], resume_text)
        incoming = raw.get("skill_judgements") or []
        ignored = max(0, len([item for item in incoming if isinstance(item, dict)]) - len(judgements))
        by_name = {normalize_skill(item["skill"]): item for item in judgements if item.get("skill")}
        for item in skill_items:
            judged = by_name.get(normalize_skill(item["name"]))
            if not judged:
                continue
            item["status"] = judged["status"]
            if judged.get("evidence"):
                item["evidence"] = judged["evidence"]
            if judged.get("reason"):
                item["reason"] = judged["reason"]
        dimensions["skills"] = skill_score(skill_items)
        engineering_items = [item for item in skill_items if item["type"] == "engineering"]
        if engineering_items:
            dimensions["engineering"] = skill_score(engineering_items)
        evidence_map = raw.get("dimension_evidence") or {}
        score_map = raw.get("dimension_scores") or {}
        for key in ("projects", "experience", "education"):
            quote = str(evidence_map.get(key) or "")
            if key not in score_map:
                continue
            if evidence_in_source(quote, resume_text) or evidence_in_source(quote, job_text):
                try:
                    dimensions[key] = round(max(0.0, min(100.0, float(score_map[key]))), 2)
                except (TypeError, ValueError):
                    continue
                if quote:
                    notes[key] = f"{notes.get(key, '')} 依据：{quote}".strip()
    original_rule = rule["rule_score"]
    revised = weighted_overall(dimensions)
    if raw:
        final, delta = apply_ai_adjustment(original_rule, revised)
        ai_validated = True
    else:
        final, delta = original_rule, 0.0
        ai_validated = False
    suggestions = []
    summary = f"规则匹配分为 {original_rule}，综合分为 {final}。"
    if raw:
        for item in raw.get("suggestions") or []:
            text = str(item).strip()
            if not text:
                continue
            if has_new_numbers(resume_text, text):
                suggestions.append("请根据真实经历补充成果数据，系统不会编造指标。")
            else:
                suggestions.append(text)
        model_summary = str(raw.get("summary") or "").strip()
        if model_summary and not has_new_numbers(resume_text + job_text, model_summary):
            summary = model_summary
    if ignored:
        notes["ignored_judgements"] = f"已忽略 {ignored} 条缺少原文依据的判断"
    dimension_rows = [
        {"key": key, "name": DIMENSION_NAMES[key], "score": dimensions[key], "summary": notes.get(key, "")}
        for key in DIMENSION_WEIGHTS
    ]
    evidence = [
        {"skill": item["name"], "quote": item.get("evidence") or "", "status": item["status"]}
        for item in skill_items
        if item.get("evidence")
    ]
    return {
        "skills": skill_items,
        "dimensions": dimension_rows,
        "overall_score": final,
        "rule_score": original_rule,
        "ai_adjustment": delta,
        "ai_validated": ai_validated,
        "summary": summary,
        "suggestions": list(dict.fromkeys(suggestions)),
        "evidence": evidence,
        "breakdown": {
            "weights": DIMENSION_WEIGHTS,
            "skill_weights": SKILL_WEIGHTS,
            "status_points": STATUS_POINTS,
            "rule_score": original_rule,
            "revised_score": revised,
            "ai_adjustment": delta,
            "final_score": final,
            "ai_validated": ai_validated,
            "notes": notes,
        },
    }


async def run_job_match(db: Session, task: AITask) -> str | None:
    report = db.get(JobMatchReport, int(task.resource_id))
    if report is None or report.user_id != task.user_id:
        raise AppError("匹配报告不存在", 404)
    version = _load_version(db, report.resume_version_id)
    if version is None:
        raise AppError("简历版本不存在", 404)
    report.status = "processing"
    db.commit()
    snapshot = report.job_snapshot_json or {}
    resume_text = _version_corpus(version)
    skill_names = [item.name for item in version.skills]
    tech_text = "\n".join(item.tech_stack for item in version.projects if item.tech_stack)
    project_text = "\n".join(
        "\n".join(filter(None, [item.name, item.background, item.tech_stack, item.responsibilities, item.achievements]))
        for item in version.projects
    )
    body_text = "\n".join(
        [project_text]
        + [item.content for item in version.experiences]
        + [f"{item.name} {item.description}" for item in version.skills]
    )
    degrees = [item.degree for item in version.educations if item.degree]
    rule = build_rule_match(
        job_skills=snapshot.get("skills") or [],
        resume_skills=skill_names,
        tech_text=tech_text,
        body_text=body_text,
        project_text=project_text,
        experience_count=len(version.experiences),
        project_count=len(version.projects),
        experience_requirement=snapshot.get("experience_requirement") or "",
        education_requirement=snapshot.get("education_requirement") or "",
        degrees=degrees,
    )
    raw = None
    try:
        system, user = match_prompt(resume_text, snapshot.get("raw_jd") or "", str(rule["rule_score"]))
        raw = await get_llm_client().complete_json(system, user, task.id, task.user_id)
    except LLMNotConfigured:
        raise
    except (LLMError, ValueError, TypeError):
        raw = None
    merged = _apply_match_ai(rule, raw, resume_text, snapshot.get("raw_jd") or "")
    report.status = "success"
    report.overall_score = merged["overall_score"]
    report.rule_score = merged["rule_score"]
    report.ai_adjustment = merged["ai_adjustment"]
    report.ai_validated = merged["ai_validated"]
    report.summary = merged["summary"]
    report.dimension_scores_json = merged["dimensions"]
    report.skill_matches_json = merged["skills"]
    report.evidence_json = merged["evidence"]
    report.suggestions_json = merged["suggestions"]
    report.score_breakdown_json = merged["breakdown"]
    report.error_message = ""
    task.result_ref = str(report.id)
    db.commit()
    return None


async def run_resume_optimize(db: Session, task: AITask) -> str | None:
    from app.services.optimizations import job_context

    row = db.get(ResumeOptimization, int(task.resource_id))
    if row is None or row.user_id != task.user_id:
        raise AppError("优化记录不存在", 404)
    row.status = "processing"
    db.commit()
    system, user = optimize_prompt(row.original_text, job_context(db, row.job_id), row.optimize_type)
    raw = await get_llm_client().complete_json(system, user, task.id, task.user_id)
    cleaned = sanitize_optimization(raw, row.original_text)
    row.optimized_text = cleaned["optimized_text"]
    row.suggestions_json = cleaned["suggestions"]
    row.status = "success"
    row.error_message = ""
    task.result_ref = str(row.id)
    db.commit()
    return None


HANDLERS = {
    "resume_parse": run_resume_parse,
    "resume_diagnosis": run_resume_diagnosis,
    "job_parse": run_job_parse,
    "job_match": run_job_match,
    "resume_optimize": run_resume_optimize,
}


class TaskRunner:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker: asyncio.Task | None = None
        self._running = False
        self._inflight: set[str] = set()

    def start(self) -> None:
        self._running = True
        self._worker = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass

    async def recover(self) -> None:
        db = SessionLocal()
        try:
            rows = db.query(AITask).filter(AITask.status.in_(["PENDING", "PROCESSING"])).all()
            ids = []
            for row in rows:
                if row.status == "PROCESSING":
                    row.status = "PENDING"
                    row.updated_at = utcnow()
                ids.append(row.id)
            db.commit()
        finally:
            db.close()
        for task_id in ids:
            await self.queue.put(task_id)

    async def submit(self, task_id: str) -> None:
        await self.queue.put(task_id)

    async def _loop(self) -> None:
        while self._running:
            task_id = await self.queue.get()
            try:
                await self.execute(task_id)
            finally:
                self.queue.task_done()

    async def execute(self, task_id: str) -> None:
        if task_id in self._inflight:
            return
        self._inflight.add(task_id)
        follow_id = None
        db = SessionLocal()
        try:
            task = db.get(AITask, task_id)
            if task is None or task.status in {"SUCCESS", "CANCELLED"}:
                return
            task.status = "PROCESSING"
            task.updated_at = utcnow()
            db.commit()
            logger.info("task start id=%s type=%s", task.id, task.task_type)
            try:
                follow_id = await HANDLERS[task.task_type](db, task)
                db.refresh(task)
                if task.status != "FAILED":
                    task.status = "SUCCESS"
                    task.error_message = ""
                    task.updated_at = utcnow()
                    db.commit()
                logger.info("task done id=%s type=%s", task_id, task.task_type)
            except Exception as exc:
                db.rollback()
                failed = db.get(AITask, task_id)
                message = exc.message if isinstance(exc, AppError) else "任务执行失败"
                if failed is not None:
                    failed.status = "FAILED"
                    failed.error_message = message
                    failed.updated_at = utcnow()
                    _mark_resource_failed(db, failed)
                    db.commit()
                logger.exception("task failed id=%s", task_id)
                follow_id = None
        finally:
            db.close()
            self._inflight.discard(task_id)
        if follow_id:
            await self.submit(follow_id)


task_runner = TaskRunner()
