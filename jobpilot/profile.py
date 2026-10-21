"""首建：4 轮 × 3 问，只收 12 个 L0 字段。"""

from __future__ import annotations

from pathlib import Path

from . import home, values

# jobpilot-privacy-allow：下面全是演示用假数据，不是真人信息
DEMO_PROFILE = {
    "person": {"name": "张三", "id_no": "110101199901011234", "birth_date": "1999-01-01"},
    "contact": {"phone": "13800000000", "email": "zhangsan@example.com"},
    "education": [{"level": "硕士", "school": "示例大学", "major": "金融科技",
                   "grad_date": "2026-11"}],
    "intent": {"directions": ["数据分析", "风险"], "cities": ["杭州", "上海"]},
    "prefs": {"resume": "材料/中文简历.pdf", "submit": "dry_run"},
}

QUESTIONS = (
    ("姓名", "person.name"),
    ("手机号", "contact.phone"),
    ("邮箱", "contact.email"),
    ("身份证号", "person.id_no"),
    ("出生日期（1999-01-01）", "person.birth_date"),
    ("学校", "education.0.school"),
    ("专业", "education.0.major"),
    ("学历（本科/硕士）", "education.0.level"),
    ("预计毕业时间（2026-11）", "education.0.grad_date"),
    ("求职方向（逗号分隔）", "intent.directions"),
    ("意向城市（逗号分隔）", "intent.cities"),
    ("简历文件路径", "prefs.resume"),
)

ROUNDS = [QUESTIONS[i:i + 3] for i in range(0, len(QUESTIONS), 3)]


def _put(profile: dict, path: str, value):
    parts = path.split(".")
    cur = profile
    for part in parts[:-1]:
        if part.isdigit():
            idx = int(part)
            while len(cur) <= idx:
                cur.append({})
            cur = cur[idx]
        else:
            cur = cur.setdefault(part, [] if parts[parts.index(part) + 1].isdigit() else {})
    last = parts[-1]
    if last.isdigit():
        idx = int(last)
        while len(cur) <= idx:
            cur.append({})
        cur[idx] = value
    else:
        cur[last] = value


def _seed_values(profile: dict) -> dict:
    v = values.empty()
    person = profile.get("person", {})
    contact = profile.get("contact", {})
    values.set_value(v, "person.name", person.get("name", ""))
    values.set_value(v, "contact.phone", contact.get("phone", ""))
    values.set_value(v, "contact.email", contact.get("email", ""))
    values.set_value(v, "person.id_no", person.get("id_no", ""), type_="text")
    values.set_value(v, "person.birth_date", person.get("birth_date", ""), type_="date")
    if profile.get("education"):
        edu = profile.get("education", [{}])[0]
        for key in ("level", "school", "major", "grad_date"):
            if edu.get(key):
                values.set_value(v, f"education.0.{key}", edu[key])
    values.set_value(v, "intent.directions", profile.get("intent", {}).get("directions", []))
    values.set_value(v, "intent.cities", profile.get("intent", {}).get("cities", []))
    values.set_value(v, "prefs.resume", profile.get("prefs", {}).get("resume", ""))
    values.set_value(v, "prefs.submit", profile.get("prefs", {}).get("submit", "dry_run"))
    return v


def create(path: Path | None = None, demo: bool = False, answers: dict | None = None) -> dict:
    """生成 profile.json 与 values.json；demo 用假数据。"""
    path = Path(path) if path else home.ensure_layout() / "profile.json"
    if demo:
        profile = DEMO_PROFILE
    elif answers:
        profile = {k: {} for k in ("person", "contact", "education", "intent", "prefs")}
        profile["education"] = [{}]
        for label, field_path in QUESTIONS:
            if field_path in answers:
                val = answers[field_path]
                if isinstance(val, str) and field_path in ("intent.directions", "intent.cities"):
                    val = [x.strip() for x in val.replace("，", ",").split(",") if x.strip()]
                if field_path.startswith("education.0."):
                    profile["education"][0][field_path.split(".")[-1]] = val
                elif field_path.startswith("person."):
                    profile["person"][field_path.split(".")[-1]] = val
                elif field_path.startswith("contact."):
                    profile["contact"][field_path.split(".")[-1]] = val
                elif field_path.startswith("intent."):
                    profile["intent"][field_path.split(".")[-1]] = val
                elif field_path.startswith("prefs."):
                    profile["prefs"][field_path.split(".")[-1]] = val
    else:
        raise ValueError("either demo or answers")

    values_doc = _seed_values(profile)
    home.write_json(path, profile, mode=0o600)
    home.write_json(path.parent / "values.json", values_doc, mode=0o600)
    return {"profile": profile, "values": values_doc}


def load(path: Path | None = None) -> dict:
    p = Path(path) if path else home.home() / "profile.json"
    return home.read_json(p, {}) or {}


def rounds() -> list[list[tuple[str, str]]]:
    return ROUNDS


def questions_json() -> list[list[dict]]:
    return [[{"label": label, "path": path} for label, path in round_] for round_ in ROUNDS]
