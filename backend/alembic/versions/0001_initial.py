"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("target_role", sa.String(100), nullable=False),
        sa.Column("years_experience", sa.String(50), nullable=False),
        sa.Column("bio", sa.Text(), nullable=False),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_refresh_token_hash", "user_sessions", ["refresh_token_hash"])
    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("parse_status", sa.String(20), nullable=False),
        sa.Column("diagnosis_status", sa.String(20), nullable=False),
        sa.Column("parse_error", sa.Text(), nullable=False),
        sa.Column("current_version_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])
    op.create_table(
        "resume_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("candidate_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_resume_versions_resume_id", "resume_versions", ["resume_id"])
    op.create_table(
        "resume_educations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version_id", sa.Integer(), sa.ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("school", sa.String(200), nullable=False),
        sa.Column("major", sa.String(200), nullable=False),
        sa.Column("degree", sa.String(50), nullable=False),
        sa.Column("start_date", sa.String(50), nullable=False),
        sa.Column("end_date", sa.String(50), nullable=False),
    )
    op.create_table(
        "resume_experiences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version_id", sa.Integer(), sa.ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company", sa.String(200), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("start_date", sa.String(50), nullable=False),
        sa.Column("end_date", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
    )
    op.create_table(
        "resume_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version_id", sa.Integer(), sa.ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("background", sa.Text(), nullable=False),
        sa.Column("tech_stack", sa.Text(), nullable=False),
        sa.Column("responsibilities", sa.Text(), nullable=False),
        sa.Column("achievements", sa.Text(), nullable=False),
    )
    op.create_table(
        "resume_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version_id", sa.Integer(), sa.ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("proficiency", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
    )
    op.create_table(
        "resume_analysis_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_version_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("dimensions_json", sa.JSON(), nullable=False),
        sa.Column("issues_json", sa.JSON(), nullable=False),
        sa.Column("suggestions_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "job_positions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("raw_jd", sa.Text(), nullable=False),
        sa.Column("salary_range", sa.String(100), nullable=False),
        sa.Column("experience_requirement", sa.String(100), nullable=False),
        sa.Column("education_requirement", sa.String(100), nullable=False),
        sa.Column("parse_status", sa.String(20), nullable=False),
        sa.Column("parse_error", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "job_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("job_positions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("responsibilities_json", sa.JSON(), nullable=False),
        sa.Column("skills_json", sa.JSON(), nullable=False),
        sa.Column("experience_requirement", sa.String(200), nullable=False),
        sa.Column("education_requirement", sa.String(200), nullable=False),
        sa.Column("other_requirements_json", sa.JSON(), nullable=False),
        sa.Column("uncertain_fields_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "job_match_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("resume_version_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("job_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("rule_score", sa.Float(), nullable=True),
        sa.Column("ai_adjustment", sa.Float(), nullable=True),
        sa.Column("ai_validated", sa.Boolean(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("dimension_scores_json", sa.JSON(), nullable=False),
        sa.Column("skill_matches_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("suggestions_json", sa.JSON(), nullable=False),
        sa.Column("score_breakdown_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "resume_optimizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("resume_version_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("optimize_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("optimized_text", sa.Text(), nullable=False),
        sa.Column("suggestions_json", sa.JSON(), nullable=False),
        sa.Column("saved_version_id", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "ai_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("resource_type", sa.String(40), nullable=False),
        sa.Column("resource_id", sa.String(40), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("result_ref", sa.String(40), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_tasks_user_id", "ai_tasks", ["user_id"])
    op.create_index("ix_ai_tasks_status", "ai_tasks", ["status"])
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    for name in [
        "ai_usage_logs",
        "ai_tasks",
        "resume_optimizations",
        "job_match_reports",
        "job_requirements",
        "job_positions",
        "resume_analysis_reports",
        "resume_skills",
        "resume_projects",
        "resume_experiences",
        "resume_educations",
        "resume_versions",
        "resumes",
        "user_sessions",
        "user_profiles",
        "users",
    ]:
        op.drop_table(name)
