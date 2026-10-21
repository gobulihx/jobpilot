"""站点卡：按 ATS 归类，分层覆盖 _generic → ats → site。"""

from __future__ import annotations

import json
from pathlib import Path

CARD_DIR = Path(__file__).resolve().parent.parent / "sitecards"


def _read(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load(card_id: str = "_generic", extra_dir: Path | None = None) -> dict:
    generic = _read(CARD_DIR / "_generic.json")
    card = generic
    for sub in ("ats", "sites"):
        p = CARD_DIR / sub / f"{card_id}.json"
        if p.exists():
            card = _merge(card, _read(p))
    if extra_dir:
        p = Path(extra_dir) / f"{card_id}.json"
        if p.exists():
            card = _merge(card, _read(p))
    return card


def detect(url: str, widgets: list[str] | None = None, extra_dir: Path | None = None) -> str:
    """按 URL 与控件特征挑一张卡；挑不到用 _generic。"""
    widgets = widgets or []
    candidates = []
    for sub in ("ats", "sites"):
        base = Path(extra_dir) if (sub == "sites" and extra_dir) else CARD_DIR / sub
        if not base.exists():
            continue
        for p in base.glob("*.json"):
            card = _read(p)
            score = 0
            patterns = card.get("match", {}).get("url_patterns", [])
            for pat in patterns:
                if pat and pat in url:
                    score += 2
            for w in card.get("match", {}).get("widgets", []):
                if w in widgets:
                    score += 1
            if score:
                candidates.append((score, p.stem))
    if not candidates:
        return "_generic"
    candidates.sort(reverse=True)
    return candidates[0][1]


def validate(card: dict) -> list[str]:
    issues = []
    if not isinstance(card.get("schema_version"), int):
        issues.append("缺 schema_version")
    if "fields" in card and not isinstance(card["fields"], dict):
        issues.append("fields 必须是 标签→canonical 的字典")
    for key in card.get("fields", {}):
        if not isinstance(card["fields"][key], str):
            issues.append(f"fields.{key} 必须指向 canonical id")
    return issues
