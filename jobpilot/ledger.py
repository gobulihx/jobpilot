"""台账：SQLite，事件溯源，幂等写入。

唯一键 = 公司 + 岗位 + 城市 + 批次（归一化）。状态从事件推导，但缓存一列便于查询。
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

STATUSES = ("draft", "filled", "submitted", "screening", "written_test",
            "interview", "offer", "closed")
STATUS_LABEL = {
    "draft": "草稿", "filled": "已填未投", "submitted": "已投递",
    "screening": "筛选中", "written_test": "笔试", "interview": "面试",
    "offer": "录用", "closed": "已结束",
}
_SUB_STATUS = {"submitted", "screening", "written_test", "interview", "offer"}


def _norm(text: str) -> str:
    s = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
    return re.sub(r"[\s\-—·・,，.。()（）\[\]【】/]+", "", s)


def key_of(company: str, position: str, city: str = "", batch: str = "") -> str:
    raw = "|".join(_norm(x) for x in (company, position, city, batch))
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS applications (
          id TEXT PRIMARY KEY,
          company TEXT NOT NULL,
          position TEXT NOT NULL,
          city TEXT DEFAULT '',
          batch TEXT DEFAULT '',
          url TEXT DEFAULT '',
          source TEXT DEFAULT '',
          status TEXT DEFAULT 'draft',
          submit_mode TEXT DEFAULT 'dry_run',
          created_at TEXT,
          updated_at TEXT,
          applied_at TEXT,
          resume_version TEXT DEFAULT '',
          site TEXT DEFAULT '',
          external_id TEXT DEFAULT '',
          note TEXT DEFAULT ''
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_app_id ON applications(id);
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          app_id TEXT NOT NULL,
          ts TEXT NOT NULL,
          type TEXT NOT NULL,
          note TEXT DEFAULT '',
          evidence TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS mails (
          msgid TEXT PRIMARY KEY,
          ts TEXT,
          frm TEXT,
          subject TEXT,
          snippet TEXT,
          app_id TEXT,
          kind TEXT
        );
        """)
        self.conn.commit()

    def add(self, company: str, position: str, city: str = "", batch: str = "",
            url: str = "", source: str = "", status: str = "draft",
            submit_mode: str = "dry_run", resume_version: str = "",
            site: str = "", external_id: str = "", note: str = "") -> tuple[str, bool]:
        """返回 (id, 是否新建)。重复调用不会产生第二条。"""
        if status not in STATUSES:
            raise ValueError(f"未知状态 {status}")
        app_id = key_of(company, position, city, batch)
        now = _now()
        self.conn.execute("""
          INSERT INTO applications
            (id, company, position, city, batch, url, source, status, submit_mode,
             created_at, updated_at, applied_at, resume_version, site, external_id, note)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(id) DO UPDATE SET
            url = COALESCE(NULLIF(excluded.url, ''), applications.url),
            source = COALESCE(NULLIF(excluded.source, ''), applications.source),
            resume_version = COALESCE(NULLIF(excluded.resume_version, ''), applications.resume_version),
            site = COALESCE(NULLIF(excluded.site, ''), applications.site),
            external_id = COALESCE(NULLIF(excluded.external_id, ''), applications.external_id),
            note = COALESCE(NULLIF(excluded.note, ''), applications.note),
            updated_at = excluded.updated_at
        """, (app_id, company, position, city, batch, url, source, status, submit_mode,
              now, now, now if status in _SUB_STATUS else None,
              resume_version, site, external_id, note))
        # 是否首次，用事件表判断
        exists = self.conn.execute(
            "SELECT 1 FROM events WHERE app_id=? LIMIT 1", (app_id,)).fetchone()
        first = not exists
        if first:
            self.conn.execute(
                "INSERT INTO events(app_id, ts, type, note) VALUES (?,?,?,?)",
                (app_id, now, status, "建档"))
        self.conn.commit()
        return app_id, first

    def add_event(self, app_id: str, type_: str, note: str = "", evidence: str = "") -> bool:
        if type_ not in STATUSES:
            raise ValueError(f"未知状态 {type_}")
        row = self.conn.execute("SELECT status FROM applications WHERE id=?", (app_id,)).fetchone()
        if not row:
            return False
        now = _now()
        self.conn.execute(
            "INSERT INTO events(app_id, ts, type, note, evidence) VALUES (?,?,?,?,?)",
            (app_id, now, type_, note, evidence))
        if type_ in _SUB_STATUS:
            self.conn.execute(
                "UPDATE applications SET status=?, updated_at=?, "
                "applied_at=COALESCE(applied_at, ?) WHERE id=?",
                (type_, now, now, app_id))
        else:
            self.conn.execute(
                "UPDATE applications SET status=?, updated_at=? WHERE id=?",
                (type_, now, app_id))
        self.conn.commit()
        return True

    def get(self, app_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM applications WHERE id=?", (app_id,)).fetchone()
        return dict(row) if row else None

    def find(self, company: str, position: str = "", city: str = "") -> dict | None:
        if position:
            row = self.conn.execute(
                "SELECT * FROM applications WHERE company=? AND position=? AND city=?",
                (company, position, city)).fetchone()
            return dict(row) if row else None
        row = self.conn.execute(
            "SELECT * FROM applications WHERE company=? ORDER BY updated_at DESC LIMIT 1",
            (company,)).fetchone()
        return dict(row) if row else None

    def find_all(self, company: str, position: str = "", city: str = "") -> list[dict]:
        out = []
        for row in self.list():
            if _norm(row["company"]) != _norm(company):
                continue
            if position and _norm(row["position"]) != _norm(position):
                continue
            if city and _norm(row["city"]) != _norm(city):
                continue
            out.append(row)
        return out

    def list(self, status: str | None = None) -> list[dict]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM applications WHERE status=? ORDER BY updated_at DESC",
                (status,)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM applications ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]

    def events(self, app_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM events WHERE app_id=? ORDER BY id", (app_id,)).fetchall()
        return [dict(r) for r in rows]

    def funnel(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) c FROM applications").fetchone()["c"]
        counts = {s: 0 for s in STATUSES}
        for row in self.conn.execute("SELECT status, COUNT(*) c FROM applications GROUP BY status"):
            counts[row["status"]] = row["c"]
        applied = sum(counts[s] for s in _SUB_STATUS)
        return {
            "总数": total,
            "已投递": applied,
            "回复": counts["written_test"] + counts["interview"] + counts["offer"],
            "面试": counts["interview"] + counts["offer"],
            "录用": counts["offer"],
            "明细": {STATUS_LABEL[k]: v for k, v in counts.items()},
        }

    def rows(self) -> list[dict]:
        out = []
        for app in self.list():
            out.append({
                "日期": (app.get("applied_at") or app.get("created_at") or "")[:10],
                "公司": app["company"],
                "岗位": app["position"],
                "城市": app["city"],
                "状态": STATUS_LABEL.get(app["status"], app["status"]),
                "内推方式": app.get("source", ""),
                "笔试": "有" if app["status"] in ("written_test",) else "",
                "面试": "有" if app["status"] in ("interview", "offer") else "",
                "链接": app.get("url", ""),
            })
        return out

    def remember_mail(self, msgid: str, ts: str, frm: str, subject: str,
                      snippet: str, app_id: str = "", kind: str = "") -> bool:
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO mails(msgid, ts, frm, subject, snippet, app_id, kind) "
            "VALUES (?,?,?,?,?,?,?)", (msgid, ts, frm, subject, snippet, app_id, kind))
        self.conn.commit()
        return cur.rowcount == 1

    def close(self):
        self.conn.close()
