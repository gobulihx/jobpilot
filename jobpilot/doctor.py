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


def _browser_ready() -> bool:
    """装没装 playwright 和浏览器能不能起来，是两件事。"""
    from . import browser
    return browser.ready()


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
        "browser_installed": _module("playwright"),
        "browser_ready": _browser_ready(),
        "cdp_9222": _port_open(9222),
        "search": "由助手判断",
        "node": shutil.which("node") or "",
        "sitecards": len(cards),
    }


def summary(caps: dict) -> list[str]:
    lines = []
    if caps["cdp_9222"]:
        lines.append("自动填表：能用（连你正开着的 Chrome，填完不关页面）。")
    elif caps.get("browser_ready"):
        lines.append("自动填表：能用（会自己开一个专用浏览器，填完留着给你看）。")
    elif caps.get("browser_installed"):
        lines.append("自动填表：组件装了一半，还差浏览器本体。下面的命令能补齐；不装也能生成填写稿。")
    else:
        lines.append("自动填表：还没准备。想用就装一下，不想装也能生成填写稿。")
    lines.append("表格导出：" + ("能用" if caps["xlsx"] else "先用 csv，装上表格组件后可以导出 Excel。"))
    lines.append(f"数据目录：{caps['home']}（{'可写' if caps['home_writable'] else '不可写'}）")
    lines.append(f"站点卡：{caps['sitecards']} 张")
    lines.append("搜索：看助手手上有没有搜索工具；有就直接用，没有就只读你给的链接。")
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
