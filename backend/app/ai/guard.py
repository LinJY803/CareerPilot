import re

DIAGNOSIS_DIMENSIONS = [
    ("basic", "基础信息"),
    ("education", "教育经历"),
    ("experience", "工作经历"),
    ("project", "项目经历"),
    ("skill", "技能描述"),
    ("expression", "表达质量"),
    ("achievement", "成果展示"),
]


def compact_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "").lower()


def evidence_in_source(evidence: str, source: str) -> bool:
    quote = (evidence or "").strip()
    if len(quote) < 2:
        return False
    return compact_text(quote) in compact_text(source)


def extract_numbers(value: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?%?", value or ""))


def has_new_numbers(original: str, updated: str) -> bool:
    return not extract_numbers(updated) <= extract_numbers(original)


def _tokens(value: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.]{1,}", value or "")
    chunks = re.findall(r"[\u4e00-\u9fff]{2,}", value or "")
    return [item.lower() for item in words + chunks]


def field_grounded(value: str, source: str) -> bool:
    text = (value or "").strip()
    if not text:
        return True
    if len(text) <= 6 or not _tokens(text):
        return compact_text(text) in compact_text(source)
    tokens = _tokens(text)
    source_compact = compact_text(source)
    hits = sum(1 for token in tokens if compact_text(token) in source_compact)
    return hits / len(tokens) >= 0.7


def _clear_ungrounded(entry: dict, keys: list[str], source: str) -> bool:
    for key in keys:
        value = str(entry.get(key) or "").strip()
        if value and not field_grounded(value, source):
            entry[key] = ""
        else:
            entry[key] = value
    return any(str(entry.get(key) or "").strip() for key in keys)


def ground_parsed_resume(data: dict, source: str) -> dict:
    basic = dict(data.get("basic") or {})
    for key in ("name", "email", "phone", "city"):
        value = str(basic.get(key) or "").strip()
        basic[key] = value if field_grounded(value, source) else ""
    educations = []
    for item in data.get("educations") or []:
        row = dict(item)
        if _clear_ungrounded(row, ["school", "major", "degree", "start_date", "end_date"], source):
            educations.append(row)
    experiences = []
    for item in data.get("experiences") or []:
        row = dict(item)
        if _clear_ungrounded(row, ["company", "title", "start_date", "end_date", "content"], source):
            experiences.append(row)
    projects = []
    for item in data.get("projects") or []:
        row = dict(item)
        if _clear_ungrounded(row, ["name", "background", "tech_stack", "responsibilities", "achievements"], source):
            projects.append(row)
    skills = []
    for item in data.get("skills") or []:
        row = dict(item)
        name = str(row.get("name") or "").strip()
        if not name or not field_grounded(name, source):
            continue
        proficiency = str(row.get("proficiency") or "").strip()
        description = str(row.get("description") or "").strip()
        skills.append(
            {
                "name": name,
                "proficiency": proficiency if field_grounded(proficiency, source) else "",
                "description": description if field_grounded(description, source) else "",
            }
        )
    return {
        "basic": basic,
        "educations": educations,
        "experiences": experiences,
        "projects": projects,
        "skills": skills,
    }


def _clamp_score(value) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 60.0
    return round(max(0.0, min(100.0, score)), 2)


def sanitize_diagnosis(payload: dict, source: str) -> dict:
    raw_dimensions = {item.get("key"): item for item in payload.get("dimensions") or [] if isinstance(item, dict)}
    dimensions = []
    for key, name in DIAGNOSIS_DIMENSIONS:
        item = raw_dimensions.get(key) or {}
        summary = str(item.get("summary") or "").strip() or "信息不足，无法给出更具体的判断"
        dimensions.append({"key": key, "name": name, "score": _clamp_score(item.get("score", 60)), "summary": summary})
    issues = []
    for item in payload.get("issues") or []:
        if not isinstance(item, dict):
            continue
        evidence = str(item.get("evidence") or "").strip()
        if not evidence_in_source(evidence, source):
            continue
        suggestion = str(item.get("suggestion") or "").strip()
        example = str(item.get("example") or "").strip()
        if has_new_numbers(source, suggestion):
            suggestion = "请根据真实经历补充具体数据，系统不会编造指标。"
        if has_new_numbers(source, example):
            example = ""
        issues.append(
            {
                "dimension": str(item.get("dimension") or ""),
                "problem": str(item.get("problem") or "").strip(),
                "evidence": evidence,
                "suggestion": suggestion,
                "example": example,
            }
        )
    overall = round(sum(item["score"] for item in dimensions) / len(dimensions), 2)
    suggestions = [issue["suggestion"] for issue in issues if issue["suggestion"]]
    return {"overall_score": overall, "dimensions": dimensions, "issues": issues, "suggestions": suggestions}


def _grounded_text(value: str, source: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if evidence_in_source(text, source) or field_grounded(text, source):
        return text
    return ""


def sanitize_job(payload: dict, source: str) -> dict:
    responsibilities = []
    for item in payload.get("responsibilities") or []:
        text = _grounded_text(str(item), source)
        if text:
            responsibilities.append(text)
    skills = []
    allowed = {"required", "bonus", "engineering", "business"}
    for item in payload.get("skills") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        evidence = str(item.get("evidence") or "").strip()
        skill_type = item.get("type") if item.get("type") in allowed else "required"
        if not name or not evidence_in_source(evidence, source) or not field_grounded(name, source):
            continue
        skills.append({"name": name, "type": skill_type, "evidence": evidence})
    experience = str(payload.get("experience_requirement") or "").strip()
    education = str(payload.get("education_requirement") or "").strip()
    uncertain = [str(item).strip() for item in payload.get("uncertain_fields") or [] if str(item).strip()]
    if experience and not _grounded_text(experience, source):
        uncertain.append("工作经验要求")
        experience = ""
    if education and not _grounded_text(education, source):
        uncertain.append("学历要求")
        education = ""
    others = []
    for item in payload.get("other_requirements") or []:
        text = str(item).strip()
        grounded = _grounded_text(text, source)
        if grounded:
            others.append(grounded)
        elif text:
            uncertain.append("其他要求")
    title = _grounded_text(str(payload.get("title") or ""), source)
    return {
        "title": title,
        "responsibilities": responsibilities,
        "skills": skills,
        "experience_requirement": experience,
        "education_requirement": education,
        "other_requirements": others,
        "uncertain_fields": list(dict.fromkeys(uncertain)),
    }


def sanitize_optimization(payload: dict, original: str) -> dict:
    optimized = str(payload.get("optimized_text") or "").strip()
    suggestions = [str(item).strip() for item in payload.get("suggestions") or [] if str(item).strip()]
    evidence_spans = [str(item).strip() for item in payload.get("evidence_spans") or [] if str(item).strip()]
    valid_spans = [item for item in evidence_spans if evidence_in_source(item, original)]
    safe_suggestions = []
    for item in suggestions:
        if has_new_numbers(original, item):
            safe_suggestions.append("请补充真实数据后再写入简历，系统不会编造指标。")
        else:
            safe_suggestions.append(item)
    if not valid_spans or has_new_numbers(original, optimized):
        if not any("不会编造" in item for item in safe_suggestions):
            safe_suggestions.append("当前优化缺少可追溯原文，或引入了原文没有的数字。请补充真实成果，系统不会代为编造。")
        return {"optimized_text": original, "suggestions": list(dict.fromkeys(safe_suggestions)), "accepted": False}
    return {"optimized_text": optimized or original, "suggestions": list(dict.fromkeys(safe_suggestions)), "accepted": True}


def filter_match_judgements(judgements: list, source: str) -> list[dict]:
    cleaned = []
    for item in judgements or []:
        if not isinstance(item, dict):
            continue
        status = item.get("status")
        if status not in {"matched", "partial", "missing", "unknown"}:
            continue
        evidence = str(item.get("evidence") or "").strip()
        if status in {"matched", "partial"} and not evidence_in_source(evidence, source):
            continue
        cleaned.append(
            {
                "skill": str(item.get("skill") or "").strip(),
                "status": status,
                "evidence": evidence if evidence_in_source(evidence, source) else "",
                "reason": str(item.get("reason") or "").strip(),
            }
        )
    return cleaned
