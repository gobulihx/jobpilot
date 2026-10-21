"""审阅：给用户看的一份 diff，默认掩码。"""

from __future__ import annotations

import hashlib
import json

from . import privacy, schema


def _show(value, sensitive: bool) -> str:
    if sensitive:
        return str(privacy.mask(value))
    return str(value)


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
    if plan.get("unmapped"):
        lines.append("")
        lines.append("【还要你补/确认】")
        for u in plan["unmapped"]:
            hint = f"，建议「{u.get('suggest')}」" if u.get("suggest") else ""
            lines.append(f"  · {u['label']}：{u['reason']}{hint}")
    if plan.get("warnings"):
        lines.append("")
        for w in plan["warnings"]:
            lines.append(f"  ！{w}")
    lines.append("")
    lines.append("停在提交前，等你点头。")
    return "\n".join(lines)


def approval_token(plan: dict) -> str:
    actions = [a for step in plan.get("steps", []) for a in step.get("actions", [])
               if a["op"] != "save_draft"]
    raw = json.dumps(actions, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]
