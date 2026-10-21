"""回执监控：只读邮件，关键词分类，提议状态变更，不自动改。"""

from __future__ import annotations

import unicodedata

KEYWORDS = {
    "written_test": ("笔试", "测评", "在线考试", "机考", "笔试通知"),
    "interview": ("面试", "复试", "初面", "终面", "面谈"),
    "offer": ("录用", "录取", "offer", "签约", "意向书"),
    "closed": ("未通过", "感谢信", "遗憾", "不合适", "已满", "结束"),
}


def classify(subject: str, snippet: str = "") -> str | None:
    text = f"{subject} {snippet}"
    for kind, words in KEYWORDS.items():
        for w in words:
            if w.lower() in text.lower():
                return kind
    return None


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKC", str(text or "")).lower()


def match_application(mail: dict, apps: list[dict]) -> dict | None:
    text = _norm(mail.get("subject", "")) + " " + _norm(mail.get("from", ""))
    best = None
    for app in apps:
        company = _norm(app.get("company", ""))
        if len(company) < 2:
            continue
        if company in text:
            best = app
            break
    return best


def propose(mails: list[dict], apps: list[dict]) -> list[dict]:
    proposals = []
    for mail in mails:
        kind = classify(mail.get("subject", ""), mail.get("snippet", ""))
        if not kind:
            continue
        app = match_application(mail, apps)
        proposals.append({
            "msgid": mail.get("msgid", ""),
            "subject": mail.get("subject", ""),
            "from": mail.get("from", ""),
            "kind": kind,
            "app_id": app["id"] if app else "",
            "company": app["company"] if app else "",
            "confidence": 0.9 if app else 0.4,
            "note": "" if app else "没对上投递记录，需要你确认",
        })
    return proposals
