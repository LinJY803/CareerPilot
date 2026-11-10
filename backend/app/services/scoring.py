import re

SKILL_WEIGHTS = {
    "required": 1.0,
    "engineering": 0.6,
    "bonus": 0.4,
    "business": 0.4,
}

STATUS_POINTS = {
    "matched": 1.0,
    "partial": 0.5,
    "missing": 0.0,
}

DIMENSION_WEIGHTS = {
    "skills": 0.40,
    "projects": 0.25,
    "experience": 0.15,
    "education": 0.10,
    "engineering": 0.10,
}

DIMENSION_NAMES = {
    "skills": "技能匹配",
    "projects": "项目匹配",
    "experience": "工作经验",
    "education": "教育背景",
    "engineering": "工程能力",
}

SKILL_ALIASES = {
    "js": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "typescript": "typescript",
    "nodejs": "nodejs",
    "node": "nodejs",
    "vue": "vue",
    "vue2": "vue",
    "vue3": "vue",
    "reactjs": "react",
    "react": "react",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "cicd": "cicd",
    "ci/cd": "cicd",
}

EDU_LEVELS = ["博士", "硕士", "研究生", "本科", "学士", "大专", "专科", "高中"]


def normalize_skill(name: str) -> str:
    compact = re.sub(r"[\s._+\-/#]", "", (name or "").strip().lower())
    return SKILL_ALIASES.get(compact, compact)


def text_tokens(text: str) -> set[str]:
    found: set[str] = set()
    for token in re.findall(r"[A-Za-z0-9#+./-]{2,}", text or ""):
        found.add(normalize_skill(token))
    for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", text or ""):
        found.add(chunk.lower())
    return found


def skill_mentioned(skill: str, text: str) -> bool:
    normalized = normalize_skill(skill)
    if len(normalized) < 2:
        return False
    tokens = text_tokens(text)
    if normalized in tokens:
        return True
    if len(normalized) > 3 and normalized in re.sub(r"[\s._+\-/#]", "", (text or "").lower()):
        return True
    return False


def classify_skill(skill_name: str, skill_type: str, resume_skill_names: list[str], tech_text: str, body_text: str) -> str:
    normalized = normalize_skill(skill_name)
    if any(normalize_skill(item) == normalized for item in resume_skill_names):
        return "matched"
    if skill_mentioned(skill_name, tech_text):
        return "matched"
    if skill_mentioned(skill_name, body_text):
        return "partial"
    return "missing"


def skill_score(items: list[dict]) -> float:
    numerator = 0.0
    denominator = 0.0
    for item in items:
        status = item.get("status")
        if status not in STATUS_POINTS:
            continue
        weight = SKILL_WEIGHTS.get(item.get("type") or "required", 0.4)
        numerator += weight * STATUS_POINTS[status]
        denominator += weight
    if denominator == 0:
        return 0.0
    return round(numerator / denominator * 100, 2)


def weighted_overall(dimensions: dict[str, float]) -> float:
    total = 0.0
    for key, weight in DIMENSION_WEIGHTS.items():
        total += float(dimensions.get(key, 0)) * weight
    return round(total, 2)


def apply_ai_adjustment(rule_score: float, ai_score: float) -> tuple[float, float]:
    delta = max(-8.0, min(8.0, float(ai_score) - float(rule_score)))
    return round(float(rule_score) + delta, 2), round(delta, 2)


def _education_rank(text: str) -> int | None:
    for index, level in enumerate(EDU_LEVELS):
        if level in (text or ""):
            if level == "研究生":
                return EDU_LEVELS.index("硕士")
            if level == "学士":
                return EDU_LEVELS.index("本科")
            if level == "专科":
                return EDU_LEVELS.index("大专")
            return index
    return None


def experience_score(requirement: str, experience_count: int, project_count: int) -> tuple[float, str]:
    text = requirement or ""
    if not text.strip() or "不限" in text:
        score = 80.0 if experience_count or project_count else 60.0
        return score, "岗位未限定工作年限" if not text.strip() or "不限" in text else ""
    if any(word in text for word in ("应届", "实习", "在校", "无需经验")):
        return (85.0 if project_count else 55.0), "按应届或实习要求，依据项目经历判断"
    match = re.search(r"(\d+)\s*年", text)
    if match:
        years = int(match.group(1))
        if experience_count >= years:
            return 85.0, f"工作经历条数不少于岗位要求的 {years} 年"
        if experience_count > 0:
            return 55.0, "有工作经历，但条数少于岗位年限要求，仅作粗略估计"
        return 35.0, "简历未体现工作经历"
    return (70.0 if experience_count else 50.0), "岗位年限无法精确换算，按是否写明经历估计"


def education_score(requirement: str, degrees: list[str]) -> tuple[float, str]:
    text = requirement or ""
    if not text.strip() or "不限" in text:
        return (85.0 if degrees else 60.0), "岗位未限定学历" if text.strip() else "岗位学历要求为空"
    required_rank = _education_rank(text)
    user_ranks = [rank for rank in (_education_rank(item) for item in degrees) if rank is not None]
    if required_rank is None or not user_ranks:
        return 60.0, "学历信息不足以精确判断"
    if min(user_ranks) <= required_rank:
        return 90.0, "学历不低于岗位要求"
    return 45.0, "学历低于岗位要求"


def project_score(required_skills: list[str], project_count: int, project_text: str) -> tuple[float, str]:
    if not required_skills:
        return (70.0 if project_count else 40.0), "岗位没有必备技能时，仅根据是否有项目经历估计"
    if project_count == 0:
        return 30.0, "简历没有项目经历"
    hit = sum(1 for skill in required_skills if skill_mentioned(skill, project_text))
    score = round(hit / len(required_skills) * 100, 2)
    return score, f"{hit}/{len(required_skills)} 项必备技能在项目经历中有出现"


def engineering_score(engineering_skills: list[dict]) -> tuple[float, str]:
    if not engineering_skills:
        return 80.0, "岗位未单独列出工程能力要求"
    return skill_score(engineering_skills), "按工程类技能的匹配状态计算"


def build_rule_match(job_skills: list[dict], resume_skills: list[str], tech_text: str, body_text: str, project_text: str, experience_count: int, project_count: int, experience_requirement: str, education_requirement: str, degrees: list[str]) -> dict:
    skill_items = []
    for skill in job_skills:
        name = (skill.get("name") or "").strip()
        skill_type = skill.get("type") or "required"
        if skill_type not in SKILL_WEIGHTS:
            skill_type = "required"
        if not name:
            continue
        status = classify_skill(name, skill_type, resume_skills, tech_text, body_text)
        evidence = ""
        if status in {"matched", "partial"}:
            evidence = _find_quote(name, tech_text if status == "matched" else body_text) or _find_quote(name, body_text)
        skill_items.append(
            {
                "name": name,
                "type": skill_type,
                "status": status,
                "evidence": evidence,
                "reason": "根据简历中的技能列表、技术栈和经历文本做规则匹配",
            }
        )
    skills_value = skill_score(skill_items)
    required_names = [item["name"] for item in skill_items if item["type"] == "required"]
    projects_value, projects_note = project_score(required_names, project_count, project_text)
    experience_value, experience_note = experience_score(experience_requirement, experience_count, project_count)
    education_value, education_note = education_score(education_requirement, degrees)
    engineering_items = [item for item in skill_items if item["type"] == "engineering"]
    engineering_value, engineering_note = engineering_score(engineering_items)
    dimensions = {
        "skills": skills_value,
        "projects": projects_value,
        "experience": experience_value,
        "education": education_value,
        "engineering": engineering_value,
    }
    notes = {
        "projects": projects_note,
        "experience": experience_note,
        "education": education_note,
        "engineering": engineering_note,
        "skills": "必备技能权重 1.0，工程能力 0.6，加分和业务能力 0.4；无法判断不进入分母",
    }
    dimension_rows = [
        {"key": key, "name": DIMENSION_NAMES[key], "score": dimensions[key], "summary": notes[key]}
        for key in DIMENSION_WEIGHTS
    ]
    return {
        "skills": skill_items,
        "dimensions": dimension_rows,
        "dimension_map": dimensions,
        "rule_score": weighted_overall(dimensions),
        "notes": notes,
    }


def _find_quote(skill: str, text: str) -> str:
    if not text:
        return ""
    normalized = normalize_skill(skill)
    for token in re.findall(r"[A-Za-z0-9#+./-]{2,}|[\u4e00-\u9fff]{2,}", text):
        if normalize_skill(token) == normalized or normalized in normalize_skill(token):
            return token
    return ""
