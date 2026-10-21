"""真实浏览器执行器：优先连你已经开着的 Chrome；没有就自己开一个专用浏览器。

填完**不关页面**——用户要看一眼填得怎么样。专用浏览器的登录状态会保留在
~/.jobpilot/browser，下次不用重新登录。
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

from ..browser import find_executable

DEFAULT_PORT = 9222


class BrowserUnavailable(Exception):
    pass


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


def _profile_dir() -> Path:
    root = Path(os.environ.get("JOBPILOT_HOME", "~/.jobpilot")).expanduser()
    path = root / "browser"
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass
    return path


class CdpBackend:
    name = "cdp"

    def __init__(self, endpoint: str = f"http://127.0.0.1:{DEFAULT_PORT}",
                 delay_ms: int = 20, page=None):
        self._pw = None
        self.browser = None
        self._port = int(endpoint.rsplit(":", 1)[-1])
        self.delay_ms = delay_ms
        if page is not None:
            # 测试或调用方给现成页面时，不再自己连浏览器
            self.page = page
            return
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except ImportError as exc:
            raise BrowserUnavailable("browser_missing") from exc

        self._pw = sync_playwright().start()
        try:
            self.browser = self._connect_or_launch(endpoint)
        except Exception as exc:  # noqa: BLE001
            self._pw.stop()
            self._pw = None
            raise BrowserUnavailable("browser_missing") from exc

        contexts = self.browser.contexts
        self.context = contexts[0] if contexts else self.browser.new_context()
        pages = self.context.pages
        self.page = pages[-1] if pages else self.context.new_page()

    # ---- 连接或启动 -------------------------------------------------------
    def _connect_or_launch(self, endpoint: str):
        try:
            return self._pw.chromium.connect_over_cdp(endpoint)
        except Exception:  # noqa: BLE001
            pass

        port = self._port
        if _port_open(port):
            port = port + 1 if port < 9229 else port
        self._launch_detached(port)
        for _ in range(60):
            if _port_open(port):
                break
            time.sleep(0.25)
        else:
            raise RuntimeError("browser did not start")
        self._port = port
        return self._pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")

    def _launch_detached(self, port: int):
        exe = find_executable(self._pw)
        if not exe:
            raise RuntimeError("no browser binary")
        args = [
            exe,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={_profile_dir()}",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ]
        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    # ---- 页面 -------------------------------------------------------------
    def use(self, url: str):
        """优先复用已经打开的目标页，没有再新开一个。"""
        if not url:
            return
        target = url.split("#")[0]
        for page in self.context.pages:
            if page.url.split("#")[0] == target:
                self.page = page
                return
        self.page = self.context.new_page()
        self.page.goto(url)
        self.page.wait_for_load_state("domcontentloaded")

    def fresh(self, url: str):
        """探测：新开一个标签页，不碰用户手上正在填的页面。"""
        self.page = self.context.new_page()
        self.page.goto(url)
        self.page.wait_for_load_state("domcontentloaded")

    def close_page(self):
        """只在明确需要时关页面；默认不关。"""
        try:
            self.page.close()
        except Exception:  # noqa: BLE001
            pass

    # ---- 定位 -------------------------------------------------------------
    def _locator(self, action: dict):
        label = action["target"].get("label", "")
        cid = action["target"].get("cid", "")
        handle = self.page.evaluate_handle(
            """([label, cid]) => {
                const all = [...document.querySelectorAll('input,select,textarea')];
                return all.find(el => el.dataset.cid === cid) ||
                       all.find(el => {
                         const box = el.closest('.el-form-item, .form-item, .form-group, tr, li');
                         const text = (box ? box.innerText : '') + (el.getAttribute('aria-label') || '');
                         return label && text.includes(label);
                       }) || null;
            }""", [label, cid])
        element = handle.as_element()
        if element is None:
            raise RuntimeError(f"找不到字段：{label}")
        return element

    def _read(self) -> dict[str, str]:
        return self.page.evaluate(
            """() => {
                const out = {};
                document.querySelectorAll('input,select,textarea').forEach(el => {
                  const box = el.closest('.el-form-item, .form-item, .form-group, tr, li');
                  let label = el.getAttribute('aria-label') || '';
                  if (!label && box) {
                    const lab = box.querySelector('label, .el-form-item__label');
                    label = lab ? lab.innerText.trim() : '';
                  }
                  const key = el.dataset.cid || label;
                  if (!key) return;
                  out[key] = el.value !== undefined ? el.value : (el.innerText || '');
                });
                return out;
            }""")

    # ---- 动作 -------------------------------------------------------------
    def perform(self, action: dict) -> dict:
        op = action["op"]
        try:
            if op == "type":
                el = self._locator(action)
                el.click()
                el.fill("")
                el.focus()
                self.page.keyboard.type(str(action["value"]), delay=self.delay_ms)
                self.page.keyboard.press("Tab")
            elif op == "select":
                self._select(action)
            elif op == "pick_date":
                self._pick_date(action)
            elif op == "pick_cascade":
                self._pick_cascade(action)
            elif op == "upload":
                el = self._locator(action)
                el.set_input_files(str(Path(action["file"]).expanduser()))
            elif op == "check":
                el = self._locator(action)
                el.check()
            elif op == "save_draft":
                self._click_text(["保存草稿", "保存", "暂存"])
            elif op == "submit":
                self._click_text(["提交", "投递", "确认提交"])
            else:
                return {"ok": False, "message": f"不认识的动作 {op}"}
            return {"ok": True, "message": ""}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "message": f"操作没成功：{exc}"}

    def _select(self, action):
        el = self._locator(action)
        tag = el.evaluate("e => e.tagName.toLowerCase()")
        value = str(action["value"])
        if tag == "select":
            el.select_option(label=value)
            return
        el.click()
        time.sleep(0.2)
        option = self.page.get_by_text(value, exact=True).last
        option.click()
        self.page.keyboard.press("Escape")

    def _pick_date(self, action):
        el = self._locator(action)
        el.click()
        text = str(action["value"])
        try:
            self.page.get_by_text(text, exact=True).last.click()
        except Exception:  # noqa: BLE001
            el.fill(text)
            self.page.keyboard.press("Tab")

    def _pick_cascade(self, action):
        el = self._locator(action)
        el.click()
        for part in action.get("path", []):
            self.page.get_by_text(part, exact=True).last.click()
            time.sleep(0.15)

    def _click_text(self, texts: list[str]):
        for text in texts:
            try:
                self.page.get_by_role("button", name=text).last.click(timeout=1500)
                return
            except Exception:  # noqa: BLE001
                continue
        raise RuntimeError("找不到按钮")

    def readback(self) -> dict[str, str]:
        return self._read()

    def close(self):
        """只断开自动化连接，不关浏览器、不关页面——用户还要看。"""
        if self._pw is None:
            return
        try:
            self._pw.stop()
        finally:
            self._pw = None
