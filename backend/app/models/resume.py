from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.models.base import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(10))
    file_path: Mapped[str] = mapped_column(String(500), default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    parse_status: Mapped[str] = mapped_column(String(20), default="pending")
    diagnosis_status: Mapped[str] = mapped_column(String(20), default="none")
    parse_error: Mapped[str] = mapped_column(Text, default="")
    current_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    versions: Mapped[list["ResumeVersion"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", order_by="ResumeVersion.version_no"
    )


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(30), default="upload")
    summary: Mapped[str] = mapped_column(Text, default="")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    candidate_name: Mapped[str] = mapped_column(String(100), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    resume: Mapped[Resume] = relationship(back_populates="versions")
    educations: Mapped[list["ResumeEducation"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )
    experiences: Mapped[list["ResumeExperience"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )
    projects: Mapped[list["ResumeProject"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )
    skills: Mapped[list["ResumeSkill"]] = relationship(back_populates="version", cascade="all, delete-orphan")


class ResumeEducation(Base):
    __tablename__ = "resume_educations"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True)
    school: Mapped[str] = mapped_column(String(200), default="")
    major: Mapped[str] = mapped_column(String(200), default="")
    degree: Mapped[str] = mapped_column(String(50), default="")
    start_date: Mapped[str] = mapped_column(String(50), default="")
    end_date: Mapped[str] = mapped_column(String(50), default="")

    version: Mapped[ResumeVersion] = relationship(back_populates="educations")


class ResumeExperience(Base):
    __tablename__ = "resume_experiences"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True)
    company: Mapped[str] = mapped_column(String(200), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    start_date: Mapped[str] = mapped_column(String(50), default="")
    end_date: Mapped[str] = mapped_column(String(50), default="")
    content: Mapped[str] = mapped_column(Text, default="")

    version: Mapped[ResumeVersion] = relationship(back_populates="experiences")


class ResumeProject(Base):
    __tablename__ = "resume_projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    background: Mapped[str] = mapped_column(Text, default="")
    tech_stack: Mapped[str] = mapped_column(Text, default="")
    responsibilities: Mapped[str] = mapped_column(Text, default="")
    achievements: Mapped[str] = mapped_column(Text, default="")

    version: Mapped[ResumeVersion] = relationship(back_populates="projects")


class ResumeSkill(Base):
    __tablename__ = "resume_skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    proficiency: Mapped[str] = mapped_column(String(50), default="")
    description: Mapped[str] = mapped_column(Text, default="")

    version: Mapped[ResumeVersion] = relationship(back_populates="skills")


class ResumeAnalysisReport(Base):
    __tablename__ = "resume_analysis_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    resume_version_id: Mapped[int] = mapped_column(Integer, index=True)
    task_id: Mapped[str] = mapped_column(String(36), default="")
    overall_score: Mapped[float] = mapped_column(Float, default=0)
    dimensions_json: Mapped[list] = mapped_column(JSON, default=list)
    issues_json: Mapped[list] = mapped_column(JSON, default=list)
    suggestions_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
