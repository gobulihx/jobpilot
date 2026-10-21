"""导出：填写稿、台账表格。xlsx 需要 openpyxl，没装就用 csv。"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from . import privacy, schema


def _cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def sheet_markdown(plan: dict, masked: bool = False) -> str:
    lines = [f"# 填写稿：{plan.get('url', '')}", ""]
    for step in plan.get("steps", []):
        if not step["actions"]:
            continue
        lines.append(f"## {step['module']}")
        lines.append("")
        lines.append("| 字段 | 填写内容 | 说明 |")
        lines.append("|---|---|---|")
        for a in step["actions"]:
            if a["op"] == "save_draft":
                continue
            f = schema.field_for(a.get("value_ref", ""))
            val = a.get("value", "")
            if f and f.sensitive:
                val = privacy.mask(val) if masked else val
            note = "自动选的最接近项" if a.get("match") not in (None, "exact") else ""
            if a.get("needs_confirm"):
                note = (note + "；要确认").strip("；")
            lines.append(f"| {_cell(a['target'].get('label', ''))} | {_cell(val)} | {_cell(note)} |")
        lines.append("")
    if plan.get("unmapped"):
        lines.append("## 待补/待确认")
        lines.append("")
        for u in plan["unmapped"]:
            lines.append(f"- {u['label']}：{u['reason']}")
        lines.append("")
    return "\n".join(lines)


def applications_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    cols = ["日期", "公司", "岗位", "城市", "状态", "内推方式", "笔试", "面试", "链接"]
    writer = csv.DictWriter(buf, fieldnames=cols)
    writer.writeheader()
    for r in rows:
        writer.writerow({c: r.get(c, "") for c in cols})
    return buf.getvalue()


def applications_markdown(rows: list[dict]) -> str:
    lines = ["| 日期 | 公司 | 岗位 | 城市 | 状态 |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r.get('日期', '')} | {r.get('公司', '')} | {r.get('岗位', '')} | "
                     f"{r.get('城市', '')} | {r.get('状态', '')} |")
    return "\n".join(lines) + "\n"


def applications_xlsx(rows: list[dict], path: Path) -> bool:
    try:
        import openpyxl  # type: ignore
    except ImportError:
        return False
    cols = ["日期", "公司", "岗位", "城市", "状态", "内推方式", "笔试", "面试", "链接"]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "投递记录"
    ws.append(cols)
    for r in rows:
        ws.append([r.get(c, "") for c in cols])
    wb.save(path)
    return True
