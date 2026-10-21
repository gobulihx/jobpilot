"""执行计划：模型不碰页面，执行器按动作回放；失败即停，状态可续。"""

from __future__ import annotations

import json
from pathlib import Path

from . import humanize
from . import values as values_mod


class ExecuteError(Exception):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class FakeBackend:
    """测试用：把页面当成一个 dict，验证动作顺序与值。"""

    name = "fake"

    def __init__(self, page: dict | None = None, fail_on: set[str] | None = None):
        self.page = page or {}
        self.fail_on = fail_on or set()
        self.log: list[dict] = []

    def perform(self, action: dict) -> dict:
        aid = action["aid"]
        if aid in self.fail_on:
            return {"ok": False, "message": "模拟失败"}
        op = action["op"]
        if op == "save_draft":
            self.log.append({"aid": aid, "op": op})
            return {"ok": True, "message": "已保存"}
        cid = action["target"]["cid"]
        if action.get("needs_confirm") and not action.get("confirmed"):
            return {"ok": False, "message": "要你确认"}
        self.page[cid] = action.get("value")
        self.log.append({"aid": aid, "op": op, "cid": cid, "value": action.get("value")})
        return {"ok": True, "message": ""}


def _resolve_action(plan: dict, action: dict, vals: dict) -> dict:
    """执行前重新从 values 解析，防止计划里的值和值文件不一致（防陈旧计划）。"""
    if action["op"] == "save_draft":
        return action
    ref = action.get("value_ref")
    if not ref:
        raise ExecuteError("bad_plan", f"{action['aid']} 没有来源")
    ok, current = values_mod.resolve(vals, ref)
    if not ok:
        raise ExecuteError("missing_value", ref)
    display = current
    if isinstance(current, list):
        display = "、".join(str(x) for x in current)
    elif isinstance(current, bool) and action["op"] in ("select", "type"):
        display = "是" if current else "否"

    if "value" in action and action["value"] != display:
        # 允许「是/否」与布尔互转
        if action["op"] == "check" and bool(action["value"]) == (
                str(current).strip().lower() in ("是", "有", "true", "1")):
            pass
        else:
            raise ExecuteError("stale_plan", f"{ref} 的值变了，请重新生成计划")
    action = dict(action)
    action["value"] = display
    return action


def run_plan(plan: dict, vals: dict, backend, state_path: Path | None = None,
             dry_run: bool = True, allow_submit: bool = False) -> dict:
    state = {"done": [], "failed": [], "skipped": []}
    if state_path and Path(state_path).exists():
        try:
            state = json.loads(Path(state_path).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    done = set(state.get("done", []))
    results = []
    failed = False

    for step in plan.get("steps", []):
        for action in step.get("actions", []):
            aid = action["aid"]
            if aid in done:
                results.append({"aid": aid, "ok": True, "message": "上次已完成"})
                continue
            if action["op"] == "save_draft" and dry_run:
                results.append({"aid": aid, "ok": True, "message": "演练模式，不保存"})
                continue
            if action["op"] == "submit" and not allow_submit:
                results.append({"aid": aid, "ok": False, "message": humanize.say("submit_blocked",
                                                                               company="")})
                failed = True
                break
            try:
                resolved = _resolve_action(plan, action, vals)
            except ExecuteError as exc:
                results.append({
                    "aid": aid, "ok": False, "message": humanize.say("missing_value", n=1),
                    "code": exc.code,
                    "gap": {"cid": action["target"].get("cid"),
                            "label": action["target"].get("label", ""),
                            "module": action["target"].get("module", ""),
                            "reason": exc.detail or exc.code},
                })
                failed = True
                break

            if action.get("expect", {}).get("max"):
                maxlen = action["expect"]["max"]
                if isinstance(resolved.get("value"), str) and len(resolved["value"]) > maxlen:
                    results.append({"aid": aid, "ok": False,
                                    "message": f"「{action['target'].get('label')}」超过 {maxlen} 字"})
                    failed = True
                    break

            outcome = backend.perform(resolved)
            if not outcome.get("ok"):
                outcome["gap"] = {"cid": action["target"].get("cid"),
                                  "label": action["target"].get("label", ""),
                                  "module": action["target"].get("module", ""),
                                  "reason": outcome.get("message", "")}
            results.append({"aid": aid, **outcome})
            if outcome.get("ok"):
                done.add(aid)
                state["done"] = sorted(done)
            else:
                failed = True
                break
        if failed:
            break

    state["results"] = results
    if state_path:
        Path(state_path).parent.mkdir(parents=True, exist_ok=True)
        Path(state_path).write_text(json.dumps(state, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
    return {
        "ok": not failed,
        "done": len(done),
        "failed": [r for r in results if not r.get("ok")],
        "results": results,
        "state_path": str(state_path) if state_path else "",
    }
