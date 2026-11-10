import asyncio

import pytest

from app.ai.client import LLMClient
from app.ai.guard import ground_parsed_resume, has_new_numbers, sanitize_diagnosis, sanitize_job, sanitize_optimization
from app.core.errors import LLMNotConfigured
from app.services.scoring import (
    apply_ai_adjustment,
    classify_skill,
    education_score,
    experience_score,
    skill_score,
    weighted_overall,
)


def test_skill_score_and_adjustment():
    score = skill_score(
        [
            {"type": "required", "status": "matched"},
            {"type": "bonus", "status": "missing"},
            {"type": "engineering", "status": "partial"},
            {"type": "required", "status": "unknown"},
        ]
    )
    assert score == 65.0
    overall = weighted_overall({"skills": 65, "projects": 80, "experience": 70, "education": 90, "engineering": 50})
    assert overall == 70.5
    final, delta = apply_ai_adjustment(overall, 90)
    assert delta == 8
    assert final == 78.5
    down, down_delta = apply_ai_adjustment(overall, 50)
    assert down_delta == -8
    assert down == 62.5


def test_experience_and_education_rules():
    assert experience_score("应届", 0, 1)[0] == 85
    assert education_score("本科", ["硕士"])[0] == 90
    assert education_score("硕士", ["本科"])[0] == 45


def test_skill_classification():
    assert classify_skill("Vue3", "required", ["Vue 3"], "", "") == "matched"
    assert classify_skill("Vite", "engineering", [], "", "使用 Vite 完成构建") == "partial"
    assert classify_skill("React", "bonus", [], "", "没有相关内容") == "missing"


def test_guard_rejects_invention():
    parsed = ground_parsed_resume(
        {
            "basic": {"name": "张三"},
            "educations": [],
            "experiences": [{"company": "虚构公司", "title": "架构师", "content": "不存在的经历"}],
            "projects": [],
            "skills": [{"name": "Kubernetes", "proficiency": "", "description": ""}],
        },
        "张三在星河科技负责页面开发",
    )
    assert parsed["basic"]["name"] == "张三"
    assert parsed["experiences"] == []
    assert parsed["skills"] == []

    diagnosis = sanitize_diagnosis(
        {
            "dimensions": [{"key": "project", "score": 150, "summary": "一般"}],
            "issues": [
                {
                    "dimension": "project",
                    "problem": "缺少数据",
                    "evidence": "这段不在简历里",
                    "suggestion": "补充 30% 的提升",
                    "example": "提升 30%",
                }
            ],
        },
        "负责页面开发",
    )
    assert diagnosis["dimensions"][2]["key"] == "experience"
    assert diagnosis["issues"] == []
    project = next(item for item in diagnosis["dimensions"] if item["key"] == "project")
    assert project["score"] == 100

    job = sanitize_job(
        {"title": "不存在的岗位", "skills": [{"name": "Go", "type": "required", "evidence": "Go"}], "responsibilities": ["发明需求"]},
        "负责 Vue3 页面开发",
    )
    assert job["skills"] == []
    assert job["title"] == ""

    optimized = sanitize_optimization(
        {"optimized_text": "负责页面开发，性能提升 30%", "suggestions": ["写得更具体"], "evidence_spans": ["负责页面开发"]},
        "负责页面开发",
    )
    assert optimized["accepted"] is False
    assert has_new_numbers("负责页面开发", "提升 30%")
    assert "30%" not in optimized["optimized_text"]


def test_llm_client_requires_api_key():
    with pytest.raises(LLMNotConfigured):
        asyncio.run(LLMClient().complete_json("system", "user", "task", 1))
