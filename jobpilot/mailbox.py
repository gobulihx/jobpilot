"""邮件适配器：只读本地文件，不接邮箱、不存密码。

支持：
- JSON（himalaya / imap-tools / 自己导出的列表）
- .eml 单封，或一个装着 .eml 的目录
- .mbox 归档
"""

from __future__ import annotations

import email
import hashlib
import json
import mailbox
import re
from email import policy
from email.header import decode_header, make_header
from email.message import Message
from pathlib import Path

MAX_BODY = 200_000
SNIPPET = 300


def _decode(value) -> str:
    if value is None:
        return ""
    try:
        return str(make_header(decode_header(str(value))))
    except Exception:  # noqa: BLE001
        return str(value)


def _strip_html(text: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _snippet(text: str) -> str:
    return _strip_html(str(text or ""))[:SNIPPET]


def _body(msg: Message) -> str:
    try:
        if msg.is_multipart():
            plain = None
            html = None
            for part in msg.walk():
                ctype = part.get_content_type()
                if part.get_content_disposition() == "attachment":
                    continue
                if ctype == "text/plain" and plain is None:
                    plain = part.get_content()
                elif ctype == "text/html" and html is None:
                    html = part.get_content()
            return str(plain or html or "")[:MAX_BODY]
        return str(msg.get_content() or "")[:MAX_BODY]
    except Exception:  # noqa: BLE001
        return ""


def _from_text(value) -> str:
    if isinstance(value, dict):
        return str(value.get("addr") or value.get("email") or value.get("address")
                   or value.get("name") or "")
    if isinstance(value, list):
        return _from_text(value[0]) if value else ""
    return str(value or "")


def _fallback_id(frm: str, subject: str, date: str) -> str:
    return hashlib.sha1(f"{frm}|{subject}|{date}".encode()).hexdigest()


def normalize(raw: dict) -> dict | None:
    """把不同工具导出的字段收敛成 msgid/from/subject/snippet/date。"""
    if not isinstance(raw, dict):
        return None
    d = {str(k).lower(): v for k, v in raw.items()}
    frm = _from_text(d.get("from") or d.get("sender") or d.get("from_") or "")
    subject = _decode(d.get("subject") or "")
    date = str(d.get("date") or d.get("ts") or d.get("timestamp") or "")
    snippet = _snippet(d.get("snippet") or d.get("preview") or d.get("body")
                       or d.get("text") or d.get("content") or "")
    msgid = str(d.get("msgid") or d.get("message_id") or d.get("message-id")
                or d.get("id") or "")
    if not msgid:
        msgid = _fallback_id(frm, subject, date)
    if not (subject or snippet or frm):
        return None
    return {"msgid": msgid, "from": frm, "subject": subject, "snippet": snippet, "date": date}


def _from_eml(msg: Message) -> dict:
    frm = _decode(msg.get("From"))
    subject = _decode(msg.get("Subject"))
    date = str(msg.get("Date") or "")
    msgid = str(msg.get("Message-ID") or "") or _fallback_id(frm, subject, date)
    return {
        "msgid": msgid,
        "from": frm,
        "subject": subject,
        "snippet": _snippet(_body(msg)),
        "date": date,
    }


def _load_json(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("messages") or data.get("data") or data.get("items") or []
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        mail = normalize(item)
        if mail:
            out.append(mail)
    return out


def load(path: str | Path) -> list[dict]:
    """读取本地邮件文件，按 msgid 去重。"""
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(str(p))

    mails: list[dict] = []
    if p.is_dir():
        for child in sorted(p.glob("*.eml"))[:500]:
            with child.open("rb") as fh:
                mails.append(_from_eml(email.message_from_binary_file(fh, policy=policy.default)))
    elif p.suffix.lower() in (".mbox", ".mbx"):
        box = mailbox.mbox(
            str(p),
            factory=lambda fh: email.message_from_binary_file(fh, policy=policy.default),
        )
        try:
            for msg in box:
                mails.append(_from_eml(msg))
        finally:
            box.close()
    elif p.suffix.lower() == ".eml":
        with p.open("rb") as fh:
            mails.append(_from_eml(email.message_from_binary_file(fh, policy=policy.default)))
    elif p.suffix.lower() == ".json":
        mails.extend(_load_json(p))
    else:
        try:
            mails.extend(_load_json(p))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("不认识这个邮件文件，给 JSON / EML / MBOX 或目录") from exc

    seen = set()
    unique = []
    for mail in mails:
        if mail["msgid"] in seen:
            continue
        seen.add(mail["msgid"])
        unique.append(mail)
    return unique
