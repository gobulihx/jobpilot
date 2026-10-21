"""找浏览器：优先用 Playwright 自带的，其次用系统装的 Chrome/Chromium。"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def system_chrome() -> str | None:
    if sys.platform == "darwin":
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
        for p in paths:
            if Path(p).exists():
                return p
        return None
    if os.name == "nt":
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]
        for p in paths:
            if Path(p).exists():
                return p
        return None
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                 "microsoft-edge"):
        found = shutil.which(name)
        if found:
            return found
    return None


def playwright_bundled(pw) -> str | None:
    try:
        exe = pw.chromium.executable_path
    except Exception:  # noqa: BLE001
        return None
    return exe if exe and Path(exe).exists() else None


def find_executable(pw=None) -> str | None:
    return playwright_bundled(pw) or system_chrome()


def ready() -> bool:
    """Playwright 包在，且有一个能启动的浏览器。"""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        return False
    try:
        pw = sync_playwright().start()
        try:
            return find_executable(pw) is not None
        finally:
            pw.stop()
    except Exception:  # noqa: BLE001
        return False
