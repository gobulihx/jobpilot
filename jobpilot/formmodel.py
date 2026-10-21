"""表模型：把页面探测结果规范化，给每个控件一个稳定 cid。

probe.js 在页面里做确定性抽取；这里只做校验、补 cid、算指纹。
"""

from __future__ import annotations

import hashlib
import re


def _cid(module: str, label: str, kind: str, index: int) -> str:
    raw = f"{module}|{label}|{kind}|{index}".encode()
    return hashlib.sha1(raw).hexdigest()[:10]


def fingerprint(controls: list[dict]) -> str:
    """结构指纹：标签+类型，不含值。页面改版时指纹会变。"""
    parts = []
    for c in controls:
        parts.append(f"{c.get('module', '')}/{c.get('label', '')}/{c.get('kind', '')}")
    return hashlib.sha1("\n".join(parts).encode()).hexdigest()[:16]


def normalize(raw: dict) -> dict:
    controls = []
    for i, c in enumerate(raw.get("controls", [])):
        label = str(c.get("label", "")).strip()
        kind = str(c.get("kind", "text")).strip() or "text"
        module = str(c.get("module") or raw.get("module") or "默认").strip()
        controls.append({
            "cid": c.get("cid") or _cid(module, label, kind, i),
            "module": module,
            "label": label,
            "kind": kind,
            "required": bool(c.get("required", False)),
            "maxlength": c.get("maxlength"),
            "options": c.get("options") or [],
            "current": c.get("current", ""),
            "widget": c.get("widget", ""),
            "hint": c.get("hint", ""),
            "index": i,
        })
    return {
        "url": raw.get("url", ""),
        "title": raw.get("title", ""),
        "frame": raw.get("frame"),
        "module": raw.get("module", "默认"),
        "controls": controls,
        "dom_fingerprint": raw.get("dom_fingerprint") or fingerprint(controls),
    }


def by_cid(form: dict, cid: str) -> dict | None:
    for c in form.get("controls", []):
        if c["cid"] == cid:
            return c
    return None


def modules(form: dict) -> list[str]:
    seen = []
    for c in form.get("controls", []):
        if c["module"] not in seen:
            seen.append(c["module"])
    return seen


def is_sensitive_label(label: str) -> bool:
    return bool(re.search(r"身份证|证件号|手机|电话|邮箱|密码", label))
