"""把表模型 + 值 + 站点卡编译成可审查、可回放的填写计划。

不变量：每个写入动作都必须带 source（值的路径），否则不生成动作。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from . import schema
from . import values as values_mod
from .match import AUTO, SUGGEST, match_control

KIND_OP = {
    "text": "type", "long_text": "type", "tel": "type", "email": "type",
    "number": "type", "password": "type",
    "enum": "select", "select": "select", "radio": "select",
    "date": "pick_date", "month": "pick_date",
    "region": "pick_cascade", "cascade": "pick_cascade",
    "file": "upload", "upload": "upload",
    "bool": "check", "checkbox": "check",
}


def _concrete(canonical: str, control: dict, card: dict) -> str:
    f = schema.FIELDS.get(canonical)
    if not f or not f.repeat:
        return canonical
    group, name = canonical.split(".", 1)
    idx = control.get("repeat_index")
    if idx is None:
        idx = card.get("repeat_index", 0)
    return f"{group}.{idx}.{name}"


def choose_option(value, options: list[str]) -> tuple[str | None, str]:
    if not options:
        return str(value), "ok"
    v = schema.normalize_label(str(value))
    norm = [(o, schema.normalize_label(o)) for o in options]
    for raw, n in norm:
        if n == v:
            return raw, "exact"
    for raw, n in norm:
        if v and (v in n or n in v):
            return raw, "contains"
    return None, "no_match"


def _too_long(value, control, entry) -> tuple[str, str | None]:
    """超长时优先换一个短别名，绝不静默截断。"""
    maxlen = control.get("maxlength")
    if not maxlen or not isinstance(value, str) or len(value) <= maxlen:
        return value, None
    for alias in entry.get("aliases", []) if isinstance(entry, dict) else []:
        if isinstance(alias, str) and len(alias) <= maxlen:
            return alias, f"「{value}」超过 {maxlen} 字，改用「{alias}」"
    return value, f"「{value}」超过 {maxlen} 字，页面会截断"


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("是", "有", "true", "1", "yes", "y")


def _build_action(control: dict, path: str, value, entry, card: dict):
    op = KIND_OP.get(control["kind"], "type")
    if control["kind"] == "bool" and control.get("options"):
        op = "select"
    action = {
        "aid": f"a{control['index'] + 1}",
        "op": op,
        "target": {"cid": control["cid"], "label": control["label"],
                   "module": control["module"], "kind": control["kind"]},
        "value_ref": path,
        "value": value,
    }
    warning = None

    if op == "select" and isinstance(value, bool):
        value = "是" if value else "否"
    if isinstance(value, list):
        if op == "select":
            value = value[0] if value else ""
        else:
            value = "、".join(str(x) for x in value)
        action["value"] = value

    if op == "type":
        value, warning = _too_long(value, control, entry)
        action["value"] = value
        action["strategy"] = "real_keys"
        if control.get("maxlength"):
            action["expect"] = {"max": control["maxlength"]}
    elif op == "select":
        chosen, how = choose_option(value, control.get("options", []))
        if chosen is None:
            return None, {"cid": control["cid"], "label": control["label"],
                          "reason": f"选项里没有「{value}」", "value": value,
                          "options": control.get("options", [])}, None
        action["value"] = chosen
        action["match"] = how
    elif op == "pick_date":
        if card.get("quirks", {}).get("readonly_date"):
            action["strategy"] = "panel"
        action["value"] = str(value)
    elif op == "pick_cascade":
        path_value = value if isinstance(value, list) else [
            p for p in str(value).replace("／", "/").split("/") if p
        ]
        action["path"] = path_value
        action["value"] = "/".join(path_value)
    elif op == "upload":
        from pathlib import Path as _Path
        file_path = _Path(str(value)).expanduser()
        if not file_path.exists():
            return None, {"cid": control["cid"], "label": control["label"],
                          "reason": f"找不到文件：{value}"}, None
        size = file_path.stat().st_size
        if size > 10 * 1024 * 1024:
            warning = f"「{control['label']}」有 {size // 1024 // 1024} MB，可能超过站点上限"
        action["file"] = str(file_path)
    elif op == "check":
        action["value"] = _as_bool(value)

    if float(entry.get("confidence", 1)) < AUTO:
        action["needs_confirm"] = True
    return action, None, warning


def compile_plan(form: dict, vals: dict, card: dict, module: str | None = None,
                 run_id: str | None = None, save: bool = False) -> dict:
    alias_index = dict(schema.alias_index())
    alias_index.update(values_mod.custom_alias_index(vals))
    skipped = values_mod.skipped(vals)
    fill_mode = values_mod.get_value(vals, "prefs.fill_mode", "full") or "full"
    steps = []
    unmapped: list[dict] = []
    optional_missing: list[dict] = []
    blocking: list[dict] = []
    warnings: list[str] = []
    total = 0

    modules = []
    for c in form.get("controls", []):
        if c["module"] not in modules and (module is None or c["module"] == module):
            modules.append(c["module"])

    for mod in modules:
        actions = []
        assertions = []
        for c in form.get("controls", []):
            if c["module"] != mod:
                continue
            m = match_control(c, card, alias_index)
            conf = m["confidence"]
            if not m["canonical"]:
                if not c.get("label"):
                    if c.get("required"):
                        item = {"cid": c["cid"], "label": "（未命名字段）", "module": mod,
                                "reason": "页面上没有标签", "required": True, "canonical": None}
                        unmapped.append(item)
                        blocking.append({"cid": c["cid"], "label": item["label"],
                                         "module": mod, "reason": item["reason"], "path": None})
                    continue
                item = {
                    "cid": c["cid"], "label": c["label"], "module": mod,
                    "reason": m["reason"], "options": m.get("options", []),
                    "required": bool(c.get("required")), "canonical": None,
                }
                if c.get("required"):
                    unmapped.append(item)
                    blocking.append({"cid": c["cid"], "label": c["label"], "module": mod,
                                     "reason": m["reason"], "path": None})
                elif fill_mode != "required_only":
                    optional_missing.append(item)
                continue
            if conf < SUGGEST:
                unmapped.append({"cid": c["cid"], "label": c["label"], "module": mod,
                                 "reason": "拿不准", "suggest": m["canonical"]})
                continue

            path = _concrete(m["canonical"], c, card)
            ok, val = values_mod.resolve(vals, path)
            if not ok:
                f = schema.field_for(path)
                item = {
                    "cid": c["cid"], "label": c["label"], "module": mod,
                    "reason": "缺值", "canonical": path,
                    "required": bool(c.get("required")),
                    "type": f.type if f else "text",
                    "maxlen": f.maxlen if f else None,
                }
                if c.get("required"):
                    unmapped.append(item)
                    blocking.append({"cid": c["cid"], "label": c["label"], "module": mod,
                                     "reason": "缺值", "path": path,
                                     "type": item["type"], "maxlen": item["maxlen"]})
                elif path not in skipped and fill_mode != "required_only":
                    optional_missing.append(item)
                continue

            entry = values_mod.get_entry(vals, path) or {}
            entry = dict(entry)
            entry["confidence"] = conf
            action, problem, warning = _build_action(c, path, val, entry, card)
            if problem:
                problem["module"] = mod
                unmapped.append(problem)
                if c.get("required"):
                    blocking.append({"cid": c["cid"], "label": c["label"], "module": mod,
                                     "reason": problem["reason"], "path": path})
                continue
            if warning:
                warnings.append(warning)
            if conf < AUTO:
                action["needs_confirm"] = True
                unmapped.append({"cid": c["cid"], "label": c["label"], "module": mod,
                                 "reason": "匹配把握不大，请确认", "suggest": m["canonical"]})
                if c.get("required"):
                    blocking.append({"cid": c["cid"], "label": c["label"], "module": mod,
                                     "reason": "匹配把握不大", "path": path})
            actions.append(action)
            total += 1
            if action["op"] in ("type", "select"):
                assertions.append({"after": action["aid"], "cid": c["cid"],
                                   "label": c["label"], "expect": action["value"]})

        if save and actions:
            actions.append({"aid": f"save-{mod}", "op": "save_draft",
                            "target": {"module": mod},
                            "expect": card.get("quirks", {}).get("false_save_error")})

        steps.append({"module": mod, "actions": actions, "assertions": assertions})

    plan = {
        "version": 1,
        "run_id": run_id or datetime.now().strftime("%Y%m%d-%H%M%S"),
        "site": card.get("id", "_generic"),
        "url": form.get("url", ""),
        "dom_fingerprint": form.get("dom_fingerprint", ""),
        "steps": steps,
        "unmapped": unmapped,
        "optional_missing": optional_missing,
        "blocking": blocking,
        "warnings": warnings,
        "guards": {"submit": "blocked" if not card.get("submit", {}).get("enabled") else "confirm"},
        "stats": {"actions": total, "unmapped": len(unmapped), "modules": len(steps)},
    }
    return plan


def _canonical_json(plan: dict) -> str:
    copy = json.loads(json.dumps(plan, ensure_ascii=False))
    for key in ("run_id", "created_at"):
        copy.pop(key, None)
    copy.pop("stats", None)
    return json.dumps(copy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def plan_hash(plan: dict) -> str:
    return hashlib.sha256(_canonical_json(plan).encode()).hexdigest()[:16]


def explain(plan: dict) -> list[str]:
    lines = []
    for step in plan["steps"]:
        lines.append(f"[{step['module']}] {len(step['actions'])} 项")
        for a in step["actions"]:
            label = a["target"].get("label", a["op"])
            lines.append(f"  {label} ← {a['value_ref']}（{a['op']}）")
    for u in plan["unmapped"]:
        lines.append(f"  待确认：{u['label']}（{u['reason']}）")
    return lines
