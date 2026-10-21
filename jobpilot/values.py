"""值层：canonical values 的读写、校验、缺失统计。

每个值都是 ``{"v": ..., "type": ..., "sensitive": ...}``，也接受裸字符串
（旧的或手写的文件），读取时自动包装。
"""

from __future__ import annotations

import re
from typing import Any

from . import schema

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
_TEL_RE = re.compile(r"^\+?\d{6,15}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def empty() -> dict:
    return {"person": {}, "contact": {}, "education": [], "languages": [], "experiences": [],
            "family": [], "awards": [], "intent": {}, "narratives": {}, "flags": {}, "prefs": {}}


def _parts(path: str) -> list[str]:
    return [p for p in path.split(".") if p]


def _norm_parts(path: str) -> list[str]:
    """重复块允许省略下标：education.school → education.0.school。"""
    parts = _parts(path)
    if len(parts) >= 2 and not parts[1].isdigit():
        from . import schema
        if parts[0] in schema.REPEAT_GROUPS:
            parts.insert(1, "0")
    return parts


def get_entry(values: dict, path: str) -> dict | None:
    cur: Any = values
    for part in _norm_parts(path):
        if isinstance(cur, list):
            if not part.isdigit():
                return None
            idx = int(part)
            if idx >= len(cur):
                return None
            cur = cur[idx]
        elif isinstance(cur, dict):
            if part not in cur:
                return None
            cur = cur[part]
        else:
            return None
    return cur if isinstance(cur, dict) else None


def get_value(values: dict, path: str, default=None):
    entry = get_entry(values, path)
    if entry is None:
        # 允许裸值
        cur: Any = values
        for part in _norm_parts(path):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
                cur = cur[int(part)]
            else:
                return default
        if isinstance(cur, (dict, list)):
            return default
        return cur
    return entry.get("v", default)


def resolve(values: dict, path: str) -> tuple[bool, Any]:
    """返回 (是否有值, 值)。空字符串算没值。"""
    val = get_value(values, path)
    if val is None or (isinstance(val, str) and not val.strip()) or val == []:
        return False, None
    return True, val


def set_value(values: dict, path: str, value, type_: str | None = None) -> dict:
    parts = _norm_parts(path)
    cur: Any = values
    for i, part in enumerate(parts[:-1]):
        nxt = parts[i + 1]
        if isinstance(cur, list):
            idx = int(part)
            while len(cur) <= idx:
                cur.append({})
            cur = cur[idx]
        else:
            if part not in cur or not isinstance(cur[part], (dict, list)):
                cur[part] = [] if nxt.isdigit() else {}
            cur = cur[part]
    last = parts[-1]
    entry = {"v": value}
    f = schema.field_for(path)
    if type_ or (f and f.type != "text"):
        entry["type"] = type_ or (f.type if f else "text")
    if f and f.sensitive:
        entry["sensitive"] = True
    if isinstance(cur, list):
        idx = int(last)
        while len(cur) <= idx:
            cur.append({})
        cur[idx] = entry
    else:
        cur[last] = entry
    return values


def delete_path(values: dict, path: str) -> None:
    parts = _norm_parts(path)
    cur: Any = values
    for part in parts[:-1]:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return
    last = parts[-1]
    if isinstance(cur, dict):
        cur.pop(last, None)
    elif isinstance(cur, list) and last.isdigit() and int(last) < len(cur):
        cur[int(last)] = {}


def _is_empty(v) -> bool:
    return v is None or v == "" or v == [] or v == {}


def missing(values: dict, ids: tuple[str, ...] | list[str] | None = None) -> list[str]:
    ids = ids or schema.L0
    out = []
    for path in ids:
        ok, _ = resolve(values, path)
        if not ok:
            out.append(path)
    return out


def check_value(path: str, raw) -> str | None:
    """检查单个值能不能写；返回一句问题，没问题返回 None。"""
    f = schema.field_for(path)
    if f is None:
        return f"{path}: 不认识这个字段"
    if raw is None or raw == "":
        return None
    if f.type == "number":
        try:
            float(raw)
        except (TypeError, ValueError):
            return f"{f.label}: 要填数字"
    if f.type == "bool":
        if not isinstance(raw, bool) and str(raw) not in ("是", "否", "true", "false"):
            return f"{f.label}: 填「是」或「否」"
    if f.type == "date" and not _DATE_RE.match(str(raw)):
        return f"{f.label}: 日期写成 2000-01-01"
    if f.type == "month" and not _MONTH_RE.match(str(raw)):
        return f"{f.label}: 月份写成 2026-11"
    if f.type == "tel" and not _TEL_RE.match(str(raw)):
        return f"{f.label}: 电话格式不对"
    if f.type == "email" and not _EMAIL_RE.match(str(raw)):
        return f"{f.label}: 邮箱格式不对"
    if f.maxlen and isinstance(raw, str) and len(raw) > f.maxlen:
        return f"{f.label}: 超过 {f.maxlen} 字"
    return None


def validate(values: dict) -> list[str]:
    """返回问题列表（内部用，不直接给用户看）。"""
    issues: list[str] = []
    for path in _walk(values):
        f = schema.field_for(path)
        if f is None:
            continue
        entry = get_entry(values, path)
        if entry is None:
            continue
        val = entry.get("v")
        if _is_empty(val):
            continue
        if f.maxlen and isinstance(val, str) and len(val) > f.maxlen:
            issues.append(f"{path}: 超过 {f.maxlen} 字（{len(val)}）")
        if f.type in ("date",) and not _DATE_RE.match(str(val)):
            issues.append(f"{path}: 日期要写成 2002-02-15")
        if f.type in ("month",) and not _MONTH_RE.match(str(val)):
            issues.append(f"{path}: 月份要写成 2026-11")
        if f.type == "tel" and not _TEL_RE.match(str(val)):
            issues.append(f"{path}: 电话格式不对")
        if f.type == "email" and not _EMAIL_RE.match(str(val)):
            issues.append(f"{path}: 邮箱格式不对")
        if f.type == "bool" and not isinstance(val, bool) and str(val) not in ("是", "否"):
            issues.append(f"{path}: 应该是 是/否")
    for path in schema.L0:
        if not resolve(values, path)[0]:
            issues.append(f"{path}: 还没填")
    return issues


def _walk(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict) and "v" in v:
                yield p
            else:
                yield from _walk(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{prefix}.{i}")


def flat(values: dict, mask: bool = False) -> list[dict]:
    """按页面顺序用的扁平列表：path / label / value / sensitive。"""
    from .privacy import mask as mask_value

    rows = []
    for path in _walk(values):
        f = schema.field_for(path)
        val = get_value(values, path)
        if _is_empty(val):
            continue
        if mask and (f and f.sensitive or (isinstance(val, str) and _looks_sensitive(val))):
            val = mask_value(val)
        rows.append({
            "path": path,
            "label": f.label if f else path,
            "value": val,
            "sensitive": bool(f and f.sensitive),
        })
    return rows


def _looks_sensitive(text: str) -> bool:
    import re
    return bool(re.search(r"\d{17}[\dXx]|1[3-9]\d{9}", text))
