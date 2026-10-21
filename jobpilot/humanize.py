"""把内部错误翻译成用户能看懂的一句话。

规则：用户文案里不出现术语、堆栈、字段英文名。
"""

from __future__ import annotations

MESSAGES = {
    "browser_missing": "没找到能用的浏览器。想自动填就把 Chrome 的调试口打开；不想装的话，人家给你一份填写稿。",
    "login_expired": "你的登录掉了，点一下重新进，人家接着填。",
    "page_changed": "这个站改版了，人家重新认一下，大概两分钟。",
    "save_check": "保存时页面报了个错，数据可能已经存上了，人家重进核对一下。",
    "network": "网络断了，人家先停下，等网好了接着来。",
    "captcha": "这个站要验证码，人家不硬来，你来点一下。",
    "low_confidence": "有 {n} 个字段人家拿不准，你确认一下。",
    "missing_value": "还差 {n} 项没填，先空着，提交前再补。",
    "submit_blocked": "停在提交页了。确认要投的话，把公司名打一遍。",
    "stale_plan": "资料改过了，这份计划是旧的。人家重新生成一份再填。",
    "upload_too_big": "照片超了大小限制，人家压一下再用。",
    "readonly_date": "这个日期框只能点着选，人家换一种选法。",
    "false_save_error": "页面报的错是假的，数据其实已经存上了。",
    "resume": "接着上次的进度来，已经填好的不会再问你。",
}

FORBIDDEN = (
    "selector",
    "xpath",
    "Traceback",
    "None",
    "null",
    "Element.setValue",
    "commitOthers",
    "DOM",
    "JSON",
    "API",
    "HTTP",
    "404",
    "500",
)


def say(code: str, **kw) -> str:
    text = MESSAGES.get(code, "出了点小状况，人家再试一次。")
    try:
        return text.format(**kw)
    except (KeyError, IndexError):
        return text


def check_user_text(text: str) -> list[str]:
    """返回命中的禁忌词，测试与 CI 用。"""
    return [w for w in FORBIDDEN if w.lower() in text.lower()]
