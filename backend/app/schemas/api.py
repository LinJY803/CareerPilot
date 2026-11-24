from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.security import validate_password


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower().strip()

    @model_validator(mode="after")
    def check_password(self):
        if self.password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        try:
            validate_password(self.password)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        return self


class LoginIn(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower().strip()


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=10)


class LogoutIn(BaseModel):
    refresh_token: str | None = None


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str

    @model_validator(mode="after")
    def check_password(self):
        if self.new_password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        try:
            validate_password(self.new_password)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        return self


class ResumeTitleIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("不能为空")
        return text


class ProfileIn(BaseModel):
    display_name: str = ""
    phone: str = ""
    city: str = ""
    target_role: str = ""
    years_experience: str = ""
    bio: str = ""


class JobIn(BaseModel):
    company_name: str = ""
    title: str
    city: str = ""
    raw_jd: str
    salary_range: str = ""
    experience_requirement: str = ""
    education_requirement: str = ""

    @field_validator("title", "raw_jd")
    @classmethod
    def required_text(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("不能为空")
        return text


class MatchIn(BaseModel):
    resume_id: int
    resume_version_id: int | None = None
    job_id: int


class OptimizeIn(BaseModel):
    resume_id: int
    project_id: int | None = None
    job_id: int | None = None
    optimize_type: Literal["project", "expression"] = "project"
