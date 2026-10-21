"""没有浏览器时的最终降级：生成可粘贴的填写稿。"""

from __future__ import annotations

from pathlib import Path

from .. import export


class SheetBackend:
    name = "sheet"

    def __init__(self, out_path: Path, masked: bool = False):
        self.out_path = Path(out_path)
        self.masked = masked

    def perform(self, action: dict) -> dict:
        # 填写稿是一次性渲染，不逐动作执行
        return {"ok": True, "message": "填写稿已生成"}

    def render(self, plan: dict) -> Path:
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self.out_path.write_text(export.sheet_markdown(plan, masked=self.masked), encoding="utf-8")
        return self.out_path
