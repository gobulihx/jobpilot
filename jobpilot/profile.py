"""首建：只问筛岗需要的 12 个字段。

姓名、身份证、手机号这些，等第一次填网申再问——那时才有用，也少暴露一会儿。
"""

from __future__ import annotations

from pathlib import Path

from . import home, schema, values

# jobpilot-privacy-allow：下面全是演示用假数据，不是真人信息
DEMO_PROFILE = {
    "person": {
        "name": "张三", "id_no": "110101199901011234", "birth_date": "1999-01-01",
        "english_level": "CET6",
    },
    "contact": {"phone": "13800000000", "email": "zhangsan@example.com"},
    "education": [{"level": "硕士", "school": "示例大学", "major": "金融科技",
                   "grad_date": "2026-11"}],
    "intent": {
        "directions": ["数据分析", "风险"], "cities": ["杭州", "上海"],
        "salary_min": "20", "employer_types": ["银行", "券商"],
        "exclude": [], "available_from": "2027-07",
    },
    "flags": {"fresh_grad": True},
    "prefs": {"resume": "材料/中文简历.pdf", "submit": "dry_run"},
}

# 首建演示：只有筛岗字段，没有身份信息
DEMO_SCREENING = {
    "person": {"english_level": "CET6"},
    "education": [{"level": "硕士", "school": "示例大学", "major": "金融科技",
                   "grad_date": "2026-11"}],
    "intent": {
        "directions": ["数据分析", "风险"], "cities": ["杭州", "上海"],
        "salary_min": "20", "employer_types": ["银行", "券商"],
        "exclude": [], "available_from": "2027-07",
    },
    "flags": {"fresh_grad": True},
    "prefs": {"submit": "dry_run"},
}

# (问题, 字段路径) —— 全部用于找岗/筛岗
QUESTIONS = (
    ("学历（本科/硕士/博士）", "education.0.level"),
    ("学校", "education.0.school"),
    ("专业", "education.0.major"),
    ("毕业时间（2027-06）", "education.0.grad_date"),
    ("求职方向（逗号分隔）", "intent.directions"),
    ("意向城市（逗号分隔）", "intent.cities"),
    ("薪资下限（千元/月，如 20）", "intent.salary_min"),
    ("英语水平（无/CET4/CET6/雅思/托福）", "person.english_level"),
    ("是否应届（是/否）", "flags.fresh_grad"),
    ("目标机构类型（银行/券商/消金/基金，逗号分隔）", "intent.employer_types"),
    ("排除项（不投的公司或行业，没有就回车）", "intent.exclude"),
    ("可到岗时间（2027-07）", "intent.available_from"),
)

ROUNDS = [QUESTIONS[i:i + 3] for i in range(0, len(QUESTIONS), 3)]


def _as_value(field_path: str, raw):
    f = schema.field_for(field_path)
    if f and f.type == "list":
        if isinstance(raw, list):
            return raw
        return [x.strip() for x in str(raw).replace("，", ",").split(",") if x.strip()]
    if f and f.type == "bool":
        if isinstance(raw, bool):
            return raw
        return str(raw).strip() in ("是", "有", "true", "1")
    return raw


def _seed_values(profile: dict) -> dict:
    v = values.empty()
    person = profile.get("person", {})
    contact = profile.get("contact", {})
    values.set_value(v, "person.name", person.get("name", ""))
    values.set_value(v, "contact.phone", contact.get("phone", ""))
    values.set_value(v, "contact.email", contact.get("email", ""))
    values.set_value(v, "person.id_no", person.get("id_no", ""), type_="text")
    values.set_value(v, "person.birth_date", person.get("birth_date", ""), type_="date")
    values.set_value(v, "person.english_level", person.get("english_level", ""))
    if profile.get("education"):
        edu = profile.get("education", [{}])[0]
        for key in ("level", "school", "major", "grad_date"):
            if edu.get(key):
                values.set_value(v, f"education.0.{key}", edu[key])
    intent = profile.get("intent", {})
    for key in ("directions", "cities", "salary_min", "employer_types", "exclude",
                "available_from"):
        path = f"intent.{key}"
        val = intent.get(key)
        if val not in (None, "", []) or (path in schema.ALLOW_EMPTY and key in intent):
            values.set_value(v, path, val)
    flags = profile.get("flags", {})
    if "fresh_grad" in flags:
        values.set_value(v, "flags.fresh_grad", flags["fresh_grad"], type_="bool")
    values.set_value(v, "prefs.resume", profile.get("prefs", {}).get("resume", ""))
    values.set_value(v, "prefs.submit", profile.get("prefs", {}).get("submit", "dry_run"))
    return v


def create(path: Path | None = None, demo: bool = False, answers: dict | None = None,
           full: bool = False) -> dict:
    """生成 profile.json 与 values.json；demo 默认只给筛岗字段，full 才带身份信息。"""
    path = Path(path) if path else home.ensure_layout() / "profile.json"
    if demo:
        profile_doc = DEMO_PROFILE if full else DEMO_SCREENING
        values_doc = _seed_values(profile_doc)
    else:
        answers = answers or {}
        values_doc = values.empty()
        for _, field_path in QUESTIONS:
            raw = answers.get(field_path)
            if raw in (None, ""):
                if field_path in schema.ALLOW_EMPTY:
                    values.set_value(values_doc, field_path, [])
                continue
            values.set_value(values_doc, field_path, _as_value(field_path, raw))
        values.set_value(values_doc, "prefs.submit", "dry_run")
        profile_doc = {"answers": {k: v for k, v in answers.items() if v not in (None, "")},
                       "prefs": {"submit": "dry_run"}}

    home.write_json(path, profile_doc, mode=0o600)
    home.write_json(path.parent / "values.json", values_doc, mode=0o600)
    return {"profile": profile_doc, "values": values_doc}


def load(path: Path | None = None) -> dict:
    p = Path(path) if path else home.home() / "profile.json"
    return home.read_json(p, {}) or {}


def rounds() -> list[list[tuple[str, str]]]:
    return ROUNDS


def questions_json() -> list[list[dict]]:
    return [[{"label": label, "path": path} for label, path in round_] for round_ in ROUNDS]
