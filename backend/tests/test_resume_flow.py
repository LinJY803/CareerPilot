import asyncio
from io import BytesIO

from docx import Document

from app.core.database import SessionLocal
from app.models import AITask, ResumeAnalysisReport, ResumeProject, ResumeVersion
from app.services.tasks import task_runner

from tests.conftest import auth_header, register

RESUME_TEXT = """张三
邮箱 zhangsan@example.com
电话 13800000000
城市 上海
教育经历
复旦大学 计算机科学 本科 2018-2022
工作经历
星河科技 前端工程师 2022-2024
负责公司后台管理系统开发，使用 Vue3 完成页面开发。
项目经历
运营后台
基于 Vue3 和 TypeScript 开发运营后台，使用 Vite 完成构建。
技能
Vue3
TypeScript
"""

JD_TEXT = """岗位名称：前端工程师
负责后台系统页面开发。
必备 Vue3 和 TypeScript。
加分技能 React。
熟悉 Vite。
学历要求：本科
工作经验：应届
"""


def build_docx() -> bytes:
    document = Document()
    for line in RESUME_TEXT.splitlines():
        document.add_paragraph(line)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


async def fake_complete(self, system, user, task_id, user_id):
    if "维度 key" in system:
        return {
            "dimensions": [
                {"key": "basic", "score": 80, "summary": "联系方式完整"},
                {"key": "education", "score": 75, "summary": "教育信息完整"},
                {"key": "experience", "score": 70, "summary": "工作内容较具体"},
                {"key": "project", "score": 68, "summary": "项目技术栈清楚"},
                {"key": "skill", "score": 72, "summary": "技能有列出"},
                {"key": "expression", "score": 60, "summary": "表达可以更具体"},
                {"key": "achievement", "score": 40, "summary": "缺少量化成果"},
            ],
            "issues": [
                {
                    "dimension": "achievement",
                    "problem": "没有量化成果",
                    "evidence": "负责公司后台管理系统开发，使用 Vue3 完成页面开发。",
                    "suggestion": "请补充真实的业务结果，不要编造数字。",
                    "example": "使用 Vue3 完成后台页面开发。",
                }
            ],
        }
    if "招聘 JD" in system:
        return {
            "title": "前端工程师",
            "responsibilities": ["负责后台系统页面开发。"],
            "skills": [
                {"name": "Vue3", "type": "required", "evidence": "Vue3"},
                {"name": "TypeScript", "type": "required", "evidence": "TypeScript"},
                {"name": "React", "type": "bonus", "evidence": "React"},
                {"name": "Vite", "type": "engineering", "evidence": "Vite"},
            ],
            "experience_requirement": "应届",
            "education_requirement": "本科",
            "other_requirements": [],
            "uncertain_fields": [],
        }
    if "语义判断" in system:
        return {
            "skill_judgements": [
                {
                    "skill": "Vue3",
                    "status": "matched",
                    "evidence": "使用 Vue3 完成页面开发",
                    "reason": "项目和工作经历都写了 Vue3",
                }
            ],
            "dimension_scores": {"projects": 76, "experience": 70, "education": 88},
            "dimension_evidence": {
                "projects": "使用 Vite 完成构建",
                "experience": "应届",
                "education": "本科",
            },
            "suggestions": ["可以补充真实的项目结果。"],
            "summary": "简历已经体现 Vue3 和 Vite，React 没有写到。",
        }
    if "optimized_text" in system:
        return {
            "optimized_text": "基于 Vue3 和 TypeScript 参与运营后台开发，使用 Vite 完成构建。",
            "suggestions": ["突出个人职责，成果请用真实数据补充。"],
            "evidence_spans": ["使用 Vite 完成构建"],
        }
    return {
        "basic": {"name": "张三", "email": "zhangsan@example.com", "phone": "13800000000", "city": "上海"},
        "educations": [{"school": "复旦大学", "major": "计算机科学", "degree": "本科", "start_date": "2018", "end_date": "2022"}],
        "experiences": [
            {
                "company": "星河科技",
                "title": "前端工程师",
                "start_date": "2022",
                "end_date": "2024",
                "content": "负责公司后台管理系统开发，使用 Vue3 完成页面开发。",
            }
        ],
        "projects": [
            {
                "name": "运营后台",
                "background": "基于 Vue3 和 TypeScript 开发运营后台",
                "tech_stack": "Vue3、TypeScript、Vite",
                "responsibilities": "使用 Vite 完成构建",
                "achievements": "",
            }
        ],
        "skills": [
            {"name": "Vue3", "proficiency": "", "description": ""},
            {"name": "TypeScript", "proficiency": "", "description": ""},
        ],
    }


def test_rename_resume_does_not_reparse(client):
    token = register(client, "a@example.com")["access_token"]
    uploaded = client.post(
        "/api/v1/resumes",
        headers=auth_header(token),
        files={"file": ("resume.docx", build_docx(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"title": "我的简历"},
    )
    assert uploaded.status_code == 200
    resume_id = uploaded.json()["id"]
    db = SessionLocal()
    try:
        tasks_before = db.query(AITask).count()
    finally:
        db.close()

    renamed = client.patch(
        f"/api/v1/resumes/{resume_id}",
        headers=auth_header(token),
        json={"title": " 新标题 "},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "新标题"
    assert renamed.json()["parse_status"] == uploaded.json()["parse_status"]

    detail = client.get(f"/api/v1/resumes/{resume_id}", headers=auth_header(token))
    assert detail.status_code == 200
    assert detail.json()["title"] == "新标题"
    db = SessionLocal()
    try:
        assert db.query(AITask).count() == tasks_before
    finally:
        db.close()

    other = register(client, "b@example.com")["access_token"]
    missing = client.patch(
        f"/api/v1/resumes/{resume_id}",
        headers=auth_header(other),
        json={"title": "别人的标题"},
    )
    assert missing.status_code == 404


def test_invalid_file_is_rejected(client):
    token = register(client)["access_token"]
    response = client.post(
        "/api/v1/resumes",
        headers=auth_header(token),
        files={"file": ("resume.pdf", b"not a pdf", "application/pdf")},
        data={"title": "坏文件"},
    )
    assert response.status_code == 400


def test_parse_without_api_key_fails_clearly(client):
    token = register(client)["access_token"]
    response = client.post(
        "/api/v1/resumes",
        headers=auth_header(token),
        files={"file": ("resume.docx", build_docx(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"title": "我的简历"},
    )
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    asyncio.run(task_runner.execute(task_id))
    task = client.get(f"/api/v1/tasks/{task_id}", headers=auth_header(token))
    assert task.status_code == 200
    assert task.json()["status"] == "FAILED"
    assert "LLM_API_KEY" in task.json()["error_message"]


def test_resume_job_match_and_history(client, monkeypatch):
    from app.ai.client import LLMClient

    monkeypatch.setattr(LLMClient, "complete_json", fake_complete)
    token = register(client)["access_token"]
    headers = auth_header(token)
    uploaded = client.post(
        "/api/v1/resumes",
        headers=headers,
        files={"file": ("resume.docx", build_docx(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"title": "我的简历"},
    )
    assert uploaded.status_code == 200
    resume_id = uploaded.json()["id"]
    again = client.post(f"/api/v1/resumes/{resume_id}/parse", headers=headers)
    assert again.json()["id"] == uploaded.json()["task_id"]

    asyncio.run(task_runner.execute(uploaded.json()["task_id"]))
    db = SessionLocal()
    try:
        diagnosis = db.query(AITask).filter(AITask.task_type == "resume_diagnosis").one()
        diagnosis_id = diagnosis.id
    finally:
        db.close()
    asyncio.run(task_runner.execute(diagnosis_id))

    detail = client.get(f"/api/v1/resumes/{resume_id}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["parse_status"] == "success"
    assert body["version"]["basic"]["name"] == "张三"
    assert body["version"]["projects"][0]["name"] == "运营后台"
    analysis = client.get(f"/api/v1/resumes/{resume_id}/analysis", headers=headers)
    assert analysis.json()["report"]["overall_score"] > 0
    assert analysis.json()["report"]["issues"][0]["evidence"].startswith("负责公司后台管理系统开发")

    other = register(client, "other@example.com")
    hidden = client.get(f"/api/v1/resumes/{resume_id}", headers=auth_header(other["access_token"]))
    assert hidden.status_code == 404

    job = client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"title": "前端工程师", "company_name": "星河科技", "raw_jd": JD_TEXT, "city": "上海", "experience_requirement": "应届", "education_requirement": "本科"},
    )
    assert job.status_code == 200
    asyncio.run(task_runner.execute(job.json()["task_id"]))
    job_detail = client.get(f"/api/v1/jobs/{job.json()['id']}", headers=headers)
    skill_names = [item["name"] for item in job_detail.json()["requirement"]["skills"]]
    assert "Vue3" in skill_names
    assert "React" in skill_names

    matched = client.post("/api/v1/jobs/match", headers=headers, json={"resume_id": resume_id, "job_id": job.json()["id"]})
    assert matched.status_code == 200
    asyncio.run(task_runner.execute(matched.json()["task_id"]))
    report = client.get(f"/api/v1/jobs/match/{matched.json()['id']}", headers=headers)
    assert report.status_code == 200
    payload = report.json()
    assert payload["status"] == "success"
    assert payload["rule_score"] is not None
    assert payload["score_breakdown"]["weights"]["skills"] == 0.4
    assert payload["ai_adjustment"] <= 8
    vue = next(item for item in payload["skills"] if item["name"] == "Vue3")
    assert vue["status"] == "matched"
    react = next(item for item in payload["skills"] if item["name"] == "React")
    assert react["status"] == "missing"

    project_id = body["version"]["projects"][0]["id"]
    version_id = body["version"]["id"]
    optimization = client.post(
        "/api/v1/optimizations",
        headers=headers,
        json={"resume_id": resume_id, "project_id": project_id, "job_id": job.json()["id"], "optimize_type": "project"},
    )
    assert optimization.status_code == 200
    asyncio.run(task_runner.execute(optimization.json()["task_id"]))
    optimized = client.get(f"/api/v1/optimizations/{optimization.json()['id']}", headers=headers).json()
    assert "Vite" in optimized["optimized_text"]
    assert "30%" not in optimized["optimized_text"]
    saved = client.post(f"/api/v1/optimizations/{optimization.json()['id']}/save", headers=headers)
    assert saved.status_code == 200
    assert saved.json()["version_no"] == 2

    db = SessionLocal()
    try:
        old_report = db.query(ResumeAnalysisReport).filter(ResumeAnalysisReport.resume_version_id == version_id).one()
        old_score = old_report.overall_score
        old_version = db.get(ResumeVersion, version_id)
        assert old_version.version_no == 1
        old_project = db.query(ResumeProject).filter(ResumeProject.version_id == version_id).one()
        assert old_project.responsibilities == "使用 Vite 完成构建"
        assert old_report.overall_score == old_score
    finally:
        db.close()

    summary = client.get("/api/v1/dashboard/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["resume_count"] == 1
    assert summary.json()["match_count"] == 1
