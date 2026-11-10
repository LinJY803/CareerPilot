from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.models.base import Base


class JobPosition(Base):
    __tablename__ = "job_positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    company_name: Mapped[str] = mapped_column(String(200), default="")
    title: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100), default="")
    raw_jd: Mapped[str] = mapped_column(Text)
    salary_range: Mapped[str] = mapped_column(String(100), default="")
    experience_requirement: Mapped[str] = mapped_column(String(100), default="")
    education_requirement: Mapped[str] = mapped_column(String(100), default="")
    parse_status: Mapped[str] = mapped_column(String(20), default="none")
    parse_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_positions.id", ondelete="CASCADE"), index=True)
    responsibilities_json: Mapped[list] = mapped_column(JSON, default=list)
    skills_json: Mapped[list] = mapped_column(JSON, default=list)
    experience_requirement: Mapped[str] = mapped_column(String(200), default="")
    education_requirement: Mapped[str] = mapped_column(String(200), default="")
    other_requirements_json: Mapped[list] = mapped_column(JSON, default=list)
    uncertain_fields_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class JobMatchReport(Base):
    __tablename__ = "job_match_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resume_id: Mapped[int] = mapped_column(Integer, index=True)
    resume_version_id: Mapped[int] = mapped_column(Integer, index=True)
    job_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    task_id: Mapped[str] = mapped_column(String(36), default="")
    job_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rule_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_adjustment: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    dimension_scores_json: Mapped[list] = mapped_column(JSON, default=list)
    skill_matches_json: Mapped[list] = mapped_column(JSON, default=list)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list)
    suggestions_json: Mapped[list] = mapped_column(JSON, default=list)
    score_breakdown_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ResumeOptimization(Base):
    __tablename__ = "resume_optimizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resume_id: Mapped[int] = mapped_column(Integer, index=True)
    resume_version_id: Mapped[int] = mapped_column(Integer, index=True)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    optimize_type: Mapped[str] = mapped_column(String(20), default="project")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    task_id: Mapped[str] = mapped_column(String(36), default="")
    original_text: Mapped[str] = mapped_column(Text, default="")
    optimized_text: Mapped[str] = mapped_column(Text, default="")
    suggestions_json: Mapped[list] = mapped_column(JSON, default=list)
    saved_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
