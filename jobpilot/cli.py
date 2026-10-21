"""命令行入口：所有流程都能单独跑，也能串起来。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from . import (
    doctor,
    export,
    formmodel,
    home,
    humanize,
    inbox,
    ledger,
    privacy,
    profile,
    schema,
    screen,
    sitecards,
    verify,
)
from . import plan as plan_mod
from . import values as values_mod
from .backends.sheet import SheetBackend

ROOT_DIR = Path(__file__).resolve().parent.parent


def _load_json_arg(path: str | None, default=None):
    if not path:
        return default
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def _values_path() -> Path:
    return home.home() / "values.json"


def _print(text: str = ""):
    print(text)


# --------------------------------------------------------------------------- doctor
def cmd_doctor(args) -> int:
    info = doctor.run()
    if args.json:
        _print(json.dumps(info["capabilities"], ensure_ascii=False, indent=2))
    else:
        for line in info["summary"]:
            _print(line)
        if not info["capabilities"].get("browser_ready"):
            _print("")
            _print(doctor.install_hint())
    return 0


# --------------------------------------------------------------------------- init
def cmd_init(args) -> int:
    if args.questions:
        _print(json.dumps(profile.questions_json(), ensure_ascii=False, indent=2))
        return 0
    if args.demo:
        created = profile.create(demo=True)
        _print("演示档案建好了：示例大学，金融科技，硕士。")
    elif args.answers:
        answers = _load_json_arg(args.answers, {})
        created = profile.create(demo=False, answers=answers)
        _print("档案建好了。")
    else:
        answers = {}
        total = len(profile.ROUNDS)
        try:
            for i, round_ in enumerate(profile.ROUNDS, 1):
                _print(f"\n第 {i}/{total} 轮，就三个问题：")
                for label, field_path in round_:
                    answer = input(f"  {label}：").strip()
                    if answer:
                        answers[field_path] = answer
        except EOFError:
            _print("\n这里没法一问一答。让助手在对话里问你，"
                   "然后把答案整理成一个文件，用 init --answers 传进来。")
            return 2
        created = profile.create(demo=False, answers=answers)
        _print("\n档案建好了。剩下的字段用到了再问，不会一次让你填一堆。")

    missing = values_mod.missing(created["values"])
    if missing:
        _print("")
        _print(humanize.say("missing_value", n=len(missing)))
        for path in missing:
            _print(f"  · {schema.label_for(path)}")
    else:
        _print("现在就能问：今天有什么能投的。")
    _print(f"数据放在：{home.home()}")
    return 0


# --------------------------------------------------------------------------- values
def cmd_values(args) -> int:
    vals = home.read_json(_values_path(), values_mod.empty()) or values_mod.empty()
    if args.action == "show":
        for row in values_mod.flat(vals, mask=not args.no_mask):
            _print(f"{row['label']}：{row['value']}")
        return 0
    if args.action == "missing":
        missing = values_mod.missing(vals)
        if not missing:
            _print("该有的都有了。")
        for path in missing:
            _print(f"  · {schema.label_for(path)}（{path}）")
        return 0
    if args.action == "set":
        if not args.path or args.value is None:
            _print("用法：values set 字段路径 值")
            return 2
        if issue := values_mod.check_value(args.path, args.value):
            _print(issue)
            return 2
        values_mod.set_value(vals, args.path, args.value)
        home.write_json(_values_path(), vals)
        _print(f"记下了：{values_mod.label_of(vals, args.path)}")
        return 0
    if args.action in ("skip", "unskip"):
        if not args.path:
            _print("要跳过哪一项？")
            return 2
        values_mod.skip(vals, args.path, on=args.action == "skip")
        home.write_json(_values_path(), vals)
        verb = "以后不再问" if args.action == "skip" else "重新算进待填"
        _print(f"记下了：{values_mod.label_of(vals, args.path)} {verb}。")
        return 0
    if args.action == "set-many":
        if not args.file:
            _print("给一个答案文件（--file answers.json）")
            return 2
        data = _load_json_arg(args.file, {})
        issues = [(path, values_mod.check_value(path, raw, vals)) for path, raw in data.items()]
        issues = [(path, msg) for path, msg in issues if msg]
        if issues:
            for path, msg in issues:
                _print(f"  · {msg}")
            _print("这几项不太对，改一下再给人家。")
            return 2
        for path, raw in data.items():
            values_mod.set_value(vals, path, raw)
        home.write_json(_values_path(), vals)
        _print(f"记下了 {len(data)} 项，下次不会再问。")
        return 0
    _print("支持 show / missing / set / set-many")
    return 2


# --------------------------------------------------------------------------- probe
def cmd_probe(args) -> int:
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(args.out).expanduser() if args.out else home.run_dir(run_id) / "form-model.json"
    if args.fixture:
        raw = _load_json_arg(args.fixture)
        form = formmodel.normalize(raw)
        home.write_json(out, form)
        _print(f"认出了 {len(form['controls'])} 个字段，放在 {out}")
        return 0
    if args.url:
        try:
            from .backends.cdp import CdpBackend
        except Exception:  # noqa: BLE001
            _print(humanize.say("browser_missing"))
            _print(doctor.install_hint())
            return 2
        probe_js = (ROOT_DIR / "runner" / "probe.js").read_text(encoding="utf-8")
        backend = CdpBackend()
        try:
            backend.fresh(args.url)
            raw = backend.page.evaluate(probe_js)
        finally:
            backend.close()
        form = formmodel.normalize(raw)
        home.write_json(out, form)
        _print(f"认出了 {len(form['controls'])} 个字段，放在 {out}")
        _print("页面给你留着了，你可以对照看看。")
        return 0
    _print("给一个页面文件（--fixture）或网址（--url）")
    return 2


# --------------------------------------------------------------------------- plan
def cmd_plan(args) -> int:
    form = _load_json_arg(args.form)
    if not form:
        _print("没找到页面结构，先跑一次 probe。")
        return 2
    form = formmodel.normalize(form)
    vals = _load_json_arg(args.values) if args.values else (
        home.read_json(_values_path(), values_mod.empty()) or values_mod.empty())
    user_cards = home.home() / "sites"
    card_id = args.card or sitecards.detect(
        form.get("url", ""), [c.get("widget", "") for c in form["controls"]],
        extra_dir=user_cards)
    card = sitecards.load(card_id, extra_dir=user_cards)
    compiled = plan_mod.compile_plan(form, vals, card, module=args.module, save=args.save)
    run_id = compiled["run_id"]
    out = Path(args.out).expanduser() if args.out else home.run_dir(run_id) / "fill-plan.json"
    home.write_json(out, compiled)
    _print(f"{compiled['stats']['actions']} 项可以填，{compiled['stats']['unmapped']} 项要你确认。")
    if compiled.get("blocking"):
        _print(f"必填还差 {len(compiled['blocking'])} 项，补齐再填。")
    _print(f"计划放在：{out}")
    return 0


# --------------------------------------------------------------------------- review
def cmd_review(args) -> int:
    compiled = _load_json_arg(args.plan)
    if not compiled:
        _print("没找到计划。")
        return 2
    if args.json:
        _print(json.dumps(compiled, ensure_ascii=False, indent=2))
    else:
        from . import review
        _print(review.render(compiled, masked=not args.no_mask))
    return 0


# --------------------------------------------------------------------------- sheet
def cmd_sheet(args) -> int:
    compiled = _load_json_arg(args.plan)
    if not compiled:
        _print("没找到计划。")
        return 2
    out = Path(args.out).expanduser() if args.out else home.ensure_layout() / "exports" / "填写稿.md"
    path = SheetBackend(out, masked=args.masked).render(compiled)
    _print(f"填写稿写好了：{path}")
    return 0


# --------------------------------------------------------------------------- run
def cmd_run(args) -> int:
    compiled = _load_json_arg(args.plan)
    if not compiled:
        _print("没找到计划。")
        return 2
    vals = home.read_json(_values_path(), values_mod.empty()) or values_mod.empty()

    blocking = compiled.get("blocking") or []
    # 值补过之后旧计划仍然记着缺口：先让用户重新生成，别拿旧计划硬填
    still = [b for b in blocking
             if not (b.get("path") and values_mod.resolve(vals, b["path"])[0])]
    if blocking and not still and not args.force:
        _print("资料补过了，这份计划还是旧的。人家按新资料重新生成一份再填。")
        return 2
    if still and not args.force:
        _print(f"先别填，还差 {len(still)} 个必填项：")
        for item in still[:5]:
            _print(f"  · {item['label']}：{item['reason']}")
        if len(still) > 5:
            _print(f"  ……还有 {len(still) - 5} 项")
        _print("补完人家再开始，省得你填一半卡住。")
        return 2

    optional = compiled.get("optional_missing") or []
    if optional:
        names = "、".join(u["label"] for u in optional[:5])
        more = f" 等 {len(optional)} 项" if len(optional) > 5 else ""
        _print(f"提醒一句：{names}{more}是选填，还空着。确认跳过就继续。")

    state_path = home.run_dir(compiled["run_id"]) / "run-state.json"

    if args.backend == "fake":
        from .execute import FakeBackend, run_plan
        backend = FakeBackend()
        result = run_plan(compiled, vals, backend, state_path=state_path,
                          dry_run=not args.save_draft)
    else:
        from .backends.cdp import BrowserUnavailable, CdpBackend
        from .execute import run_plan
        try:
            backend = CdpBackend()
        except BrowserUnavailable:
            _print(humanize.say("browser_missing"))
            _print(doctor.install_hint())
            return 2
        try:
            backend.use(compiled.get("url", ""))
            result = run_plan(compiled, vals, backend, state_path=state_path,
                              dry_run=not args.save_draft)
            readback = backend.readback()
            recon = verify.reconcile(compiled, readback)
            out = home.run_dir(compiled["run_id"]) / "results.json"
            home.write_json(out, {"result": result, "verify": recon})
            _print(f"填了 {result['done']} 项，回读核对 {recon['pass']}/{recon['checked']}。")
            _print("页面没关，你看一眼填得怎么样，没问题再自己点提交。")
            if recon["missing"] or recon["mismatch"]:
                _print(humanize.say("save_check"))
        finally:
            backend.close()

    if not result["ok"]:
        for item in result["failed"][:3]:
            gap = item.get("gap") or {}
            label = gap.get("label") or "这一项"
            _print(f"  · {label}：没填上。要不要换种填法，或者你自己填？")
        _print("停在出错的地方了，改完可以接着来。")
        return 1
    _print("都填好了，停在提交前。")
    return 0


# --------------------------------------------------------------------------- verify
def cmd_verify(args) -> int:
    compiled = _load_json_arg(args.plan)
    readback = _load_json_arg(args.readback, {})
    result = verify.reconcile(compiled, readback)
    _print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


# --------------------------------------------------------------------------- ledger
def cmd_ledger(args) -> int:
    db = ledger.Ledger(home.ensure_layout() / "ledger.db")
    try:
        if args.action == "add":
            app_id, created = db.add(args.company, args.position, args.city or "",
                                     args.batch or "", url=args.url or "",
                                     status=args.status or "draft")
            _print(("新建：" if created else "已经记过，更新了一下：") + app_id)
            return 0
        if args.action == "list":
            rows = db.list(args.status)
            if not rows:
                _print("还没有记录。")
                return 0
            _print("日期        公司                  岗位                     状态")
            for r in rows:
                _print(f"{(r.get('applied_at') or r['created_at'] or '')[:10]:12}"
                       f"{r['company'][:20]:22}{r['position'][:24]:26}"
                       f"{ledger.STATUS_LABEL.get(r['status'], r['status'])}")
            return 0
        if args.action == "funnel":
            _print(json.dumps(db.funnel(), ensure_ascii=False, indent=2))
            return 0
        if args.action == "export":
            out = Path(args.out).expanduser() if args.out else (
                home.ensure_layout() / "exports" / "投递记录.csv")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(export.applications_csv(db.rows()), encoding="utf-8-sig")
            _print(f"导出好了：{out}")
            xlsx = out.with_suffix(".xlsx")
            if export.applications_xlsx(db.rows(), xlsx):
                _print(f"Excel 也导了一份：{xlsx}")
            return 0
        _print("支持 add / list / funnel / export")
        return 2
    finally:
        db.close()


# --------------------------------------------------------------------------- screen
def cmd_screen(args) -> int:
    candidates = _load_json_arg(args.candidates, [])
    if not candidates:
        _print("给一份候选清单（--candidates）。")
        return 2
    vals = home.read_json(_values_path(), values_mod.empty()) or values_mod.empty()

    def gv(path, default=None):
        return values_mod.get_value(vals, path, default)

    profile_doc = {
        "degree": gv("education.0.level", ""),
        "grad_date": gv("education.0.grad_date", ""),
        "major": gv("education.0.major", ""),
        "cities": gv("intent.cities", []),
        "salary_min": args.salary_min if args.salary_min is not None else gv("intent.salary_min"),
        "english": args.english or gv("person.english_level", ""),
        "exclude": gv("intent.exclude", []),
        "employer_types": gv("intent.employer_types", []),
    }
    results = screen.evaluate_many(candidates, profile_doc)
    if args.json:
        _print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            _print(f"[{r['tier']}] {r.get('company', '')} · {r.get('position', '')}")
            for reason in r["reasons"][:4]:
                _print(f"    · {reason}")
            if r.get("fails"):
                for f in r["fails"]:
                    _print(f"    × {f}")
    return 0


# --------------------------------------------------------------------------- inbox
def cmd_inbox(args) -> int:
    mails = _load_json_arg(args.mails, [])
    if not mails:
        _print("给一份邮件清单（--mails）。")
        return 2
    db = ledger.Ledger(home.ensure_layout() / "ledger.db")
    try:
        apps = db.list()
        proposals = inbox.propose(mails, apps)
        if not proposals:
            _print("这批邮件里没有能对上的回执。")
            return 0
        for p in proposals:
            mark = "✓" if p["confidence"] >= 0.8 else "?"
            _print(f"{mark} {p['company'] or '没对上'} · {p['kind']} · {p['subject'][:30]}")
        if args.apply:
            n = 0
            for p in proposals:
                if p["app_id"] and p["confidence"] >= 0.8:
                    db.add_event(p["app_id"], p["kind"], note=p["subject"])
                    n += 1
                db.remember_mail(p["msgid"], "", p["from"], p["subject"], "", p["app_id"], p["kind"])
            _print(f"记下了 {n} 条状态变化。")
        return 0
    finally:
        db.close()


# --------------------------------------------------------------------------- extras
def cmd_extras(args) -> int:
    if args.questions:
        _print(json.dumps(profile.questions_json(extra=True), ensure_ascii=False, indent=2))
        return 0
    if not args.answers:
        _print("给一个答案文件（--answers answers.json）")
        return 2
    data = _load_json_arg(args.answers, {})
    vals = home.read_json(_values_path(), values_mod.empty()) or values_mod.empty()
    issues = [(path, values_mod.check_value(path, raw, vals)) for path, raw in data.items()]
    issues = [(path, msg) for path, msg in issues if msg]
    if issues:
        for path, msg in issues:
            _print(f"  · {msg}")
        _print("这几项不太对，改一下再给人家。")
        return 2
    for path, raw in data.items():
        values_mod.set_value(vals, path, raw)
    home.write_json(_values_path(), vals)
    _print(f"记下了 {len(data)} 项，以后填表会直接用。")
    return 0


# --------------------------------------------------------------------------- fields
def cmd_fields(args) -> int:
    vals = home.read_json(_values_path(), values_mod.empty()) or values_mod.empty()
    if args.action == "add":
        if not args.label:
            _print("要加什么字段？给个名字（--label）。")
            return 2
        aliases = [x.strip() for x in (args.aliases or "").replace("，", ",").split(",") if x.strip()]
        path = values_mod.add_custom(vals, args.label, value=args.value,
                                     type_=args.type or "text", aliases=aliases, slug=args.id)
        home.write_json(_values_path(), vals)
        _print(f"记下了：{args.label}。以后再遇到这个标签，人家会认。")
        return 0
    if args.action == "map":
        if not args.label or not args.path:
            _print("要映射哪个标签、对应哪个字段？")
            return 2
        known = schema.field_for(args.path) or args.path.startswith("custom.")
        if not known:
            _print(f"{args.path} 不是一个已知字段。要新加字段，用 fields add。")
            return 2
        values_mod.add_alias(vals, args.label, args.path)
        home.write_json(_values_path(), vals)
        _print(f"记下了：「{args.label}」就是 {values_mod.label_of(vals, args.path)}。")
        return 0
    if args.action == "list":
        custom = values_mod.custom_fields(vals)
        aliases = vals.get("aliases", {}) or {}
        if not custom and not aliases:
            _print("还没有自定义字段。")
            return 0
        for slug, meta in custom.items():
            extra = f"（别名：{'、'.join(meta.get('aliases', []))}）" if meta.get("aliases") else ""
            _print(f"custom.{slug}：{meta.get('label')}{extra}")
        for label, path in aliases.items():
            _print(f"别名：「{label}」→ {values_mod.label_of(vals, path)}")
        return 0
    if args.action == "remove":
        if not args.id:
            _print("要删哪个字段？给个 id。")
            return 2
        vals.get("custom_fields", {}).pop(args.id, None)
        vals.get("custom", {}).pop(args.id, None)
        vals["aliases"] = {k: v for k, v in (vals.get("aliases", {}) or {}).items()
                           if not v.startswith(f"custom.{args.id}")}
        home.write_json(_values_path(), vals)
        _print("删掉了。")
        return 0
    _print("支持 add / map / list / remove")
    return 2


# --------------------------------------------------------------------------- privacy / cards
def cmd_privacy(args) -> int:
    hits = privacy.scan_repo(ROOT_DIR)
    if not hits:
        _print("仓库里没有个人信息，干净。")
        return 0
    for path, kinds in hits:
        _print(f"{path}：{'、'.join(kinds)}")
    return 1


def cmd_cards(args) -> int:
    user_cards = home.home() / "sites"
    cards = sitecards.all_cards(extra_dir=user_cards)
    if args.action == "list":
        for name, _ in cards:
            _print(name)
        if not user_cards.exists():
            _print("\n本地卡目录还没建：~/.jobpilot/sites/（公司专属的卡放这里）")
        return 0
    problems = 0
    for name, card in cards:
        issues = sitecards.validate(card)
        if issues:
            problems += 1
            _print(f"{name}: {'；'.join(issues)}")
    _print("全部合格。" if not problems else f"{problems} 张需要改。")
    return 0 if not problems else 1


# --------------------------------------------------------------------------- demo
def cmd_demo(args) -> int:
    home.ensure_layout()
    profile.create(demo=True, full=True)
    _print("1/5 档案建好了（演示数据）")
    fixture = ROOT_DIR / "tests" / "fixtures" / "element-ui.form.json"
    form = formmodel.normalize(json.loads(fixture.read_text(encoding="utf-8")))
    vals = home.read_json(_values_path(), values_mod.empty())
    card = sitecards.load("_generic")
    compiled = plan_mod.compile_plan(form, vals, card, run_id="demo")
    out = home.run_dir("demo") / "fill-plan.json"
    home.write_json(out, compiled)
    _print(f"2/5 认出 {len(form['controls'])} 个字段，生成 {compiled['stats']['actions']} 个动作")
    sheet_path = SheetBackend(home.ensure_layout() / "exports" / "填写稿.md").render(compiled)
    _print(f"3/5 填写稿：{sheet_path}")
    db = ledger.Ledger(home.ensure_layout() / "ledger.db")
    db.add("示例银行", "总行风险岗", "杭州", "2027秋招", status="submitted")
    db.add("示例银行", "总行风险岗", "杭州", "2027秋招", status="submitted")
    _print(f"4/5 台账记录：{len(db.list())} 条（重复写入没有翻倍）")
    db.close()
    _print("5/5 演示完成。真实使用：jobpilot init")
    return 0


# --------------------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jobpilot", description="求职流水线")
    p.add_argument("--version", action="version", version="jobpilot 0.1.0")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor", help="看看现在能做什么")
    d.add_argument("--json", action="store_true")
    d.set_defaults(func=cmd_doctor)

    i = sub.add_parser("init", help="建档案（12 个字段）")
    i.add_argument("--demo", action="store_true")
    i.add_argument("--answers", help="（助手用）从 JSON 导入答案")
    i.add_argument("--questions", action="store_true", help="（助手用）输出 12 个问题")
    i.set_defaults(func=cmd_init)

    v = sub.add_parser("values", help="看/补字段")
    v.add_argument("action", choices=["show", "missing", "set", "set-many", "skip", "unskip"])
    v.add_argument("path", nargs="?")
    v.add_argument("value", nargs="?")
    v.add_argument("--file")
    v.add_argument("--no-mask", action="store_true")
    v.set_defaults(func=cmd_values)

    pr = sub.add_parser("probe", help="认页面上的字段")
    pr.add_argument("--fixture")
    pr.add_argument("--url")
    pr.add_argument("--out")
    pr.set_defaults(func=cmd_probe)

    pl = sub.add_parser("plan", help="生成填写计划")
    pl.add_argument("--form", required=True)
    pl.add_argument("--values")
    pl.add_argument("--card")
    pl.add_argument("--module")
    pl.add_argument("--out")
    pl.add_argument("--save", action="store_true")
    pl.set_defaults(func=cmd_plan)

    rv = sub.add_parser("review", help="审阅计划")
    rv.add_argument("plan")
    rv.add_argument("--json", action="store_true")
    rv.add_argument("--no-mask", action="store_true")
    rv.set_defaults(func=cmd_review)

    sh = sub.add_parser("sheet", help="生成填写稿")
    sh.add_argument("plan")
    sh.add_argument("--out")
    sh.add_argument("--masked", action="store_true")
    sh.set_defaults(func=cmd_sheet)

    rn = sub.add_parser("run", help="执行计划")
    rn.add_argument("plan")
    rn.add_argument("--backend", choices=["fake", "cdp"], default="cdp")
    rn.add_argument("--save-draft", action="store_true")
    rn.add_argument("--force", action="store_true", help="必填没补齐也先填")
    rn.set_defaults(func=cmd_run)

    ve = sub.add_parser("verify", help="回读核对")
    ve.add_argument("--plan", required=True)
    ve.add_argument("--readback", required=True)
    ve.set_defaults(func=cmd_verify)

    lg = sub.add_parser("ledger", help="投递台账")
    lg.add_argument("action", choices=["add", "list", "funnel", "export"])
    lg.add_argument("--company")
    lg.add_argument("--position")
    lg.add_argument("--city")
    lg.add_argument("--batch")
    lg.add_argument("--url")
    lg.add_argument("--status")
    lg.add_argument("--out")
    lg.set_defaults(func=cmd_ledger)

    sc = sub.add_parser("screen", help="筛岗")
    sc.add_argument("--candidates", required=True)
    sc.add_argument("--salary-min", type=int)
    sc.add_argument("--english")
    sc.add_argument("--json", action="store_true")
    sc.set_defaults(func=cmd_screen)

    ib = sub.add_parser("inbox", help="看回执")
    ib.add_argument("--mails", required=True)
    ib.add_argument("--apply", action="store_true")
    ib.set_defaults(func=cmd_inbox)

    ex = sub.add_parser("extras", help="高频补全项")
    ex.add_argument("--questions", action="store_true")
    ex.add_argument("--answers")
    ex.set_defaults(func=cmd_extras)

    fd = sub.add_parser("fields", help="字段表里没有的字段")
    fd.add_argument("action", choices=["add", "map", "list", "remove"])
    fd.add_argument("--label")
    fd.add_argument("--value")
    fd.add_argument("--type")
    fd.add_argument("--aliases")
    fd.add_argument("--id")
    fd.add_argument("--path")
    fd.set_defaults(func=cmd_fields)

    pv = sub.add_parser("privacy", help="扫描仓库")
    pv.add_argument("action", choices=["scan"], default="scan", nargs="?")
    pv.set_defaults(func=cmd_privacy)

    cd = sub.add_parser("cards", help="站点卡")
    cd.add_argument("action", choices=["list", "validate"], default="list", nargs="?")
    cd.set_defaults(func=cmd_cards)

    dm = sub.add_parser("demo", help="跑一遍演示")
    dm.set_defaults(func=cmd_demo)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        _print("\n停下了，进度还在。")
        return 130
    except Exception:  # noqa: BLE001
        import os
        import traceback
        try:
            log_dir = home.home() / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / "error.log").open("a", encoding="utf-8") as fh:
                fh.write(f"--- {datetime.now().isoformat()} ---\n")
                fh.write(privacy.mask(traceback.format_exc()) + "\n")
        except OSError:
            pass
        if os.environ.get("JOBPILOT_DEBUG"):
            traceback.print_exc()
        _print("出了点小状况，人家再试一次。要是还不行，把刚才那一步告诉我就行。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
