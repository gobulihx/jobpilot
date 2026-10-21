"""审阅：给用户看的一份 diff，默认掩码。"""

from __future__ import annotations

import hashlib
import json

from . import privacy, schema


def _show(value, sensitive: bool) -> str:
    if sensitive:
        return str(privacy.mask(value))
    return str(value)


def _type_hint(item: dict) -> str:
    hints = {"number": "（数字）", "date": "（2000-01-01）", "month": "（2026-11）",
             "email": "（邮箱）", "tel": "（电话）", "long_text": "（长文本）"}
    if item.get("maxlen"):
        return f"（不超过 {item['maxlen']} 字）"
    return hints.get(item.get("type", ""), "")


def _section(lines: list[str], title: str, items: list[dict], limit: int | None = None,
             footer: str = "") -> None:
    if not items:
        return
    lines.append("")
    lines.append(f"【{title}（{len(items)} 项）】")
    groups: dict[str, list[dict]] = {}
    for u in items:
        groups.setdefault(u.get("module", ""), []).append(u)
    shown = 0
    for module, group in groups.items():
        if len(groups) > 1 and module:
            lines.append(f"  〔{module}〕")
        for u in group:
            if limit is not None and shown >= limit:
                break
            hint = _type_hint(u)
            suggest = f"，建议「{u['suggest']}」" if u.get("suggest") else ""
            lines.append(f"  · {u['label']}{hint}：{u['reason']}{suggest}")
            shown += 1
    if limit is not None and len(items) > limit:
        lines.append(f"  ……还有 {len(items) - limit} 项")
    if footer:
        lines.append(f"  {footer}")


def render(plan: dict, masked: bool = True) -> str:
    lines = []
    total = plan.get("stats", {}).get("actions", 0)
    lines.append(f"共 {total} 项，准备填 {plan.get('url', '这个页面')}。")
    for step in plan.get("steps", []):
        if not step["actions"]:
            continue
        lines.append("")
        lines.append(f"【{step['module']}】")
        for a in step["actions"]:
            if a["op"] == "save_draft":
                lines.append("  · 保存这一页")
                continue
            label = a["target"].get("label", "")
            f = schema.field_for(a.get("value_ref", ""))
            sensitive = bool(f and f.sensitive)
            value = _show(a.get("value", ""), sensitive and masked)
            extra = "" if a.get("match", "exact") == "exact" else "（自动选的最接近项）"
            if a.get("needs_confirm"):
                extra += "（要你确认）"
            lines.append(f"  {label}：{value}{extra}")
            if a.get("strategy") == "real_keys":
                pass
    blocking = {b.get("cid") for b in plan.get("blocking", [])}
    required = [u for u in plan.get("unmapped", []) if u.get("cid") in blocking]
    others = [u for u in plan.get("unmapped", []) if u.get("cid") not in blocking]
    optional = plan.get("optional_missing", [])

    _section(lines, "先补这几项，才能开始填", required)
    _section(lines, "其他要确认的", others)
    _section(lines, "选填没填，可以补也可以跳过", optional, limit=8,
             footer="要补就说；跳过的话说一声，以后不再问。")

    if plan.get("warnings"):
        lines.append("")
        for w in plan["warnings"]:
            lines.append(f"  ！{w}")
    lines.append("")
    if blocking:
        lines.append("先补上面这几项，人家再开始。")
    else:
        lines.append("停在提交前，等你点头。")
    return "\n".join(lines)


def approval_token(plan: dict) -> str:
    actions = [a for step in plan.get("steps", []) for a in step.get("actions", [])
               if a["op"] != "save_draft"]
    raw = json.dumps(actions, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]
