"""能力探测：只说现在能做什么，不报库名。"""

from __future__ import annotations

import importlib.util
import os
import shutil
import socket
import sys
from pathlib import Path

from . import home


def _module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


def capabilities() -> dict:
    root = home.ensure_layout()
    cards = list((Path(__file__).resolve().parent.parent / "sitecards").rglob("*.json"))
    writable = os.access(root, os.W_OK)
    return {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "python_ok": sys.version_info >= (3, 11),
        "home": str(root),
        "home_writable": writable,
        "xlsx": _module("openpyxl"),
        "browser": _module("playwright"),
        "cdp_9222": _port_open(9222),
        "node": shutil.which("node") or "",
        "sitecards": len(cards),
    }


def summary(caps: dict) -> list[str]:
    lines = []
    if caps["browser"] and caps["cdp_9222"]:
        lines.append("自动填表：能用（浏览器已接上）。")
    elif caps["browser"]:
        lines.append("自动填表：能装，但没连上 Chrome。打开调试口，或者人家给你填写稿。")
    else:
        lines.append("自动填表：还没准备。想用就装一下，不想装也能生成填写稿。")
    lines.append("表格导出：" + ("能用" if caps["xlsx"] else "先用 csv，装上表格组件后可以导出 Excel。"))
    lines.append(f"数据目录：{caps['home']}（{'可写' if caps['home_writable'] else '不可写'}）")
    lines.append(f"站点卡：{caps['sitecards']} 张")
    return lines


def run() -> dict:
    caps = capabilities()
    return {"capabilities": caps, "summary": summary(caps)}


def install_hint() -> str:
    return ("想自动填表：\n"
            "  python3 -m pip install playwright\n"
            "  python3 -m playwright install chromium\n"
            "想用已经开着的 Chrome（macOS）：\n"
            "  open -na 'Google Chrome' --args --remote-debugging-port=9222")
