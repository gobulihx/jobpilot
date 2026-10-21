"""数据目录：所有个人数据都在包外，默认 ~/.jobpilot，可用 JOBPILOT_HOME 覆盖。"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

SUBDIRS = ("sites", "materials", "cache", "runs", "exports", "logs")


def home() -> Path:
    p = Path(os.environ.get("JOBPILOT_HOME", "~/.jobpilot")).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p, 0o700)
    except OSError:
        pass
    return p


def ensure_layout() -> Path:
    root = home()
    for name in SUBDIRS:
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(d, 0o700)
        except OSError:
            pass
    return root


def run_dir(run_id: str) -> Path:
    """运行目录只允许普通文件名，防止计划文件里的 run_id 穿越到别处。"""
    import re

    safe = re.sub(r"[^A-Za-z0-9._-]", "_", str(run_id or "run"))
    if safe in ("", ".", ".."):
        safe = "run"
    root = (ensure_layout() / "runs").resolve()
    d = (root / safe).resolve()
    if not str(d).startswith(str(root) + os.sep):
        raise ValueError("run_id 不合法")
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def write_json(path: Path, data, mode: int = 0o600) -> Path:
    """原子写：先写同目录临时文件，再替换，避免写一半。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return path


def read_json(path: Path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_text(path: Path, text: str, mode: int = 0o600) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return path
