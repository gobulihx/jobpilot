"""字段匹配：页面标签 → canonical id，带置信度。

模型只裁决低置信项；高置信自动映射，低置信必须用户确认。
"""

from __future__ import annotations

from . import schema

AUTO = 0.80
SUGGEST = 0.45

MODULE_GROUPS = {
    "基本": {"person", "contact"},
    "个人": {"person", "contact"},
    "账户": {"person", "contact"},
    "联系": {"contact", "person"},
    "教育": {"education"},
    "学历": {"education"},
    "语言": {"languages"},
    "实习": {"experiences"},
    "工作": {"experiences"},
    "项目": {"experiences"},
    "家庭": {"family"},
    "亲属": {"family"},
    "奖惩": {"awards"},
    "奖励": {"awards"},
    "荣誉": {"awards"},
    "意向": {"intent"},
    "应聘": {"intent"},
    "求职": {"intent"},
    "其他": {"flags", "narratives"},
    "声明": {"flags"},
}


def _groups_for(module: str) -> set[str]:
    for key, groups in MODULE_GROUPS.items():
        if key in module:
            return groups
    return set()


def _score(key: str, canonical: str, label: str, groups: set[str]) -> tuple[float, str]:
    score = 0.0
    reason = ""
    if key == label:
        f = schema.FIELDS.get(canonical)
        score = 0.95 if f and schema.normalize_label(f.label) == label else 0.90
        reason = "标签一致"
    elif label in key or key in label:
        if len(key) >= 2 and len(label) >= 2:
            short, long = sorted((len(label), len(key)))
            score = 0.55 + 0.25 * (short / long)
            reason = "包含匹配"

    f = schema.FIELDS.get(canonical)
    if score and f and f.group in groups:
        score = min(0.99, score + 0.03)
    return score, reason


def match_control(control: dict, card: dict | None = None, alias_index=None) -> dict:
    card = card or {}
    alias_index = alias_index or schema.alias_index()
    label = schema.normalize_label(control.get("label", ""))
    module = control.get("module", "")
    groups = _groups_for(module)

    overrides = card.get("fields", {})
    if isinstance(overrides, dict):
        for key, target in overrides.items():
            if schema.normalize_label(key) == label and isinstance(target, str):
                return {"canonical": target, "confidence": 0.99, "reason": "站点卡指定"}

    if not label:
        return {"canonical": None, "confidence": 0.0, "reason": "没有标签"}

    candidates: list[tuple[float, str, str]] = []
    for key, canonicals in alias_index.items():
        for canonical in canonicals:
            score, reason = _score(key, canonical, label, groups)
            if score > 0:
                candidates.append((score, canonical, reason))

    if not candidates:
        return {"canonical": None, "confidence": 0.0, "reason": "没找到对应字段"}

    candidates.sort(key=lambda x: (-x[0], x[1]))
    best_score, best_id, best_reason = candidates[0]
    if len(candidates) > 1 and candidates[1][0] == best_score and candidates[1][1] != best_id:
        return {"canonical": None, "confidence": 0.40,
                "reason": "多个字段同名，需要确认", "options": [c[1] for c in candidates[:3]]}
    return {"canonical": best_id, "confidence": round(best_score, 2), "reason": best_reason}
