"""回读核对：页面里的值和计划里的值是否一致。"""

from __future__ import annotations


def reconcile(plan: dict, readback: dict[str, str]) -> dict:
    expected = {}
    labels = {}
    for step in plan.get("steps", []):
        for a in step.get("actions", []):
            if a["op"] == "save_draft":
                continue
            cid = a["target"]["cid"]
            expected[cid] = str(a.get("value", ""))
            labels[cid] = a["target"].get("label", "")

    missing, mismatch, ok = [], [], []
    for cid, want in expected.items():
        got = readback.get(cid)
        if got is None:
            got = readback.get(labels[cid])
        if got is None or got == "":
            missing.append({"cid": cid, "label": labels[cid], "expect": want})
        elif str(got).strip() != want.strip():
            mismatch.append({"cid": cid, "label": labels[cid], "expect": want, "got": got})
        else:
            ok.append(cid)

    return {
        "ok": not missing and not mismatch,
        "checked": len(expected),
        "pass": len(ok),
        "missing": missing,
        "mismatch": mismatch,
    }
