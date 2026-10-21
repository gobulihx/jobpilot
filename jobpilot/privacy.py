"""PII 掩码与仓库扫描。

数据只在 ~/.jobpilot，仓库里不许出现真实身份证、手机号、邮箱。
"""

from __future__ import annotations

import re
from pathlib import Path

ID_RE = re.compile(r"(?<!\d)(\d{6})(\d{8})(\d{3}[\dXx])(?!\d)")
PHONE_RE = re.compile(r"(?<!\d)(1[3-9]\d)(\d{4})(\d{4})(?!\d)")
EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]{1,3})[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")

SECRET_PATTERNS = {
    "AWS Access Key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "GitHub Token": re.compile(r"(ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,})"),
    "Private Key": re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "Slack Token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "API Key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "Google API Key": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
}

SENSITIVE_IDS = {
    "person.id_no",
    "family.id_no",
    "contact.phone",
    "contact.email",
    "contact.emergency_phone",
    "experiences.supervisor_phone",
    "family.phone",
}


def mask_id(value: str) -> str:
    return ID_RE.sub(lambda m: f"{m.group(1)}{'*' * 8}{m.group(3)}", str(value))


def mask_phone(value: str) -> str:
    return PHONE_RE.sub(lambda m: f"{m.group(1)}****{m.group(3)}", str(value))


def mask_email(value: str) -> str:
    return EMAIL_RE.sub(lambda m: f"{m.group(1)}***{m.group(2)}", str(value))


def mask(value):
    if not isinstance(value, str):
        return value
    return mask_email(mask_phone(mask_id(value)))


def mask_obj(obj):
    if isinstance(obj, dict):
        return {k: mask_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [mask_obj(v) for v in obj]
    return mask(obj)


def scan_secrets(text: str) -> list[str]:
    return [name for name, pattern in SECRET_PATTERNS.items() if pattern.search(text)]


def scan_text(text: str) -> list[str]:
    hits = []
    if ID_RE.search(text):
        hits.append("身份证号")
    if PHONE_RE.search(text):
        hits.append("手机号")
    if EMAIL_RE.search(text):
        hits.append("邮箱")
    return hits


SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", "dist", "build"}
SKIP_FILES = {"privacy.py"}  # 正则本身


def scan_repo(root: Path, allow: tuple[str, ...] = ()) -> list[tuple[str, list[str]]]:
    """扫描仓库内文本文件。tests/ 与 fixtures/ 放的是合成数据，默认跳过。"""
    root = Path(root)
    found: list[tuple[str, list[str]]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.name in SKIP_FILES:
            continue
        rel = path.relative_to(root).as_posix()
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if rel.startswith(("tests/", "fixtures/")):
            continue
        if any(rel.startswith(a) for a in allow):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".zip", ".pdf", ".xlsx"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "jobpilot-privacy-allow" in text:
            continue
        hits = scan_text(text) + scan_secrets(text)
        if hits:
            found.append((rel, hits))
    return found
