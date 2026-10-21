"""筛岗：硬门槛逐条对照，只给三档结论。"""

from __future__ import annotations

TIERS = ("推荐投", "备选", "不投")
_DEGREE_RANK = {"专科": 1, "本科": 2, "硕士": 3, "博士": 4, "不限": 0, "": 0}


def _norm_degree(text: str) -> str:
    t = str(text or "")
    for key in ("博士", "硕士", "本科", "专科"):
        if key in t:
            return key
    return "不限"


def _fmt(value) -> str:
    try:
        number = float(value)
        return str(int(number)) if number.is_integer() else str(number)
    except (TypeError, ValueError):
        return str(value)


def _num(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_month(text: str) -> tuple[int, int] | None:
    try:
        parts = str(text).replace("/", "-").strip().split("-")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return None


def evaluate(candidate: dict, profile: dict) -> dict:
    reasons: list[str] = []
    evidence: dict = {}
    unknown: list[str] = []
    fails: list[str] = []

    degree_req = _norm_degree(candidate.get("degree", "不限"))
    my_degree = _norm_degree(profile.get("degree", ""))
    if degree_req != "不限" and my_degree:
        if _DEGREE_RANK.get(my_degree, 0) < _DEGREE_RANK.get(degree_req, 0):
            fails.append(f"要求{degree_req}，你是{my_degree}")
        else:
            reasons.append(f"学历够（{my_degree} ≥ {degree_req}）")

    window = candidate.get("grad_window")
    grad = profile.get("grad_date")
    if window and grad:
        lo, _, hi = str(window).partition("至")
        lo_m, hi_m = _parse_month(lo), _parse_month(hi)
        g = _parse_month(grad)
        if lo_m and hi_m and g:
            if not (lo_m <= g <= hi_m):
                fails.append(f"毕业时间 {grad} 不在 {window} 内")
            else:
                reasons.append("毕业时间在窗口内")
    elif window and not grad:
        unknown.append("毕业时间")

    salary_low = _num(candidate.get("salary_low"))
    salary_high = _num(candidate.get("salary_high"))
    want = _num(profile.get("salary_min"))
    if salary_high is not None and want is not None:
        if salary_high < want:
            fails.append(f"薪资上限 {_fmt(salary_high)} 低于你的下限 {_fmt(want)}")
        elif salary_low is not None and salary_low >= want:
            reasons.append(f"薪资 {_fmt(salary_low)}–{_fmt(salary_high)}，够线")
        else:
            reasons.append(f"薪资 {_fmt(salary_low)}–{_fmt(salary_high)}，下限偏低")
    elif want is not None:
        unknown.append("薪资")

    english_req = str(candidate.get("english", "") or "").upper()
    english_have = str(profile.get("english", "") or "").upper()
    if "CET6" in english_req or "六级" in english_req:
        if not english_have:
            unknown.append("英语")
        elif "CET6" in english_have or "六级" in english_have:
            reasons.append("英语够（六级）")
        else:
            fails.append("要求六级，你只有四级")

    cities = profile.get("cities") or []
    city = candidate.get("city", "")
    city_ok = (not cities) or (not city) or city in cities or any(c in city for c in cities)
    if city_ok:
        reasons.append("城市可接受")
    else:
        reasons.append(f"城市{city}不在你列的意向里（不是硬伤）")

    major = candidate.get("major_req") or []
    my_major = profile.get("major", "")
    major_ok = False
    if not major:
        major_ok = True
        reasons.append("专业不限")
    else:
        for m in major:
            if m and (m in my_major or my_major in m):
                major_ok = True
                reasons.append(f"专业对口（{m}）")
                break
        if not major_ok:
            reasons.append(f"专业要求 {('、'.join(major))}，你的是 {my_major}（自行判断）")

    raw_exclude = profile.get("exclude") or []
    if isinstance(raw_exclude, str):
        raw_exclude = [raw_exclude]
    exclude = [str(x) for x in raw_exclude if str(x).strip()]
    haystack = f"{candidate.get('company', '')}{candidate.get('position', '')}{city}"
    for term in exclude:
        if term in haystack:
            fails.append(f"在你排除的清单里：{term}")
            break

    raw_types = profile.get("employer_types") or []
    if isinstance(raw_types, str):
        raw_types = [raw_types]
    types = [str(x) for x in raw_types if str(x).strip()]
    category = str(candidate.get("category", "") or "")
    if types and category and not any(t in category for t in types):
        reasons.append(f"机构类型 {category} 不在你的偏好里（不是硬伤）")

    sources = candidate.get("salary_sources")
    if salary_low is not None and (sources is None or sources < 2):
        evidence["薪资来源不足"] = "只有一个来源，结论按估算"
        unknown.append("薪资交叉验证")

    if fails:
        tier = "不投"
    elif unknown:
        tier = "备选"
        reasons.append("缺数据：" + "、".join(dict.fromkeys(unknown)))
    elif major_ok:
        tier = "推荐投"
    else:
        tier = "备选"

    return {
        "tier": tier,
        "reasons": reasons,
        "fails": fails,
        "unknown": list(dict.fromkeys(unknown)),
        "evidence": evidence,
    }


def evaluate_many(candidates: list[dict], profile: dict) -> list[dict]:
    out = []
    for c in candidates:
        result = evaluate(c, profile)
        out.append({**c, **result})
    order = {t: i for i, t in enumerate(TIERS)}
    out.sort(key=lambda r: (order[r["tier"]], -float(r.get("salary_high") or 0)))
    return out
