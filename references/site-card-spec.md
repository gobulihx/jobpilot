# 站点卡规范

一张卡描述「这个站怎么填」。按 ATS 归类，不按公司归类。

## 分层

```
_generic.json        默认值
ats/element-ui.json  一类框架的共性
sites/nbcb.json      单个站的特例（覆盖前两层）
```

加载顺序：generic → ats → site，后者覆盖前者。

## 结构

```json
{
  "schema_version": 1,
  "id": "nbcb",
  "kind": "site",
  "match": {
    "url_patterns": ["zhaopin.nbcb.com.cn"],
    "widgets": ["el-form", "el-select"],
    "hints": ["宁波银行校园招聘"]
  },
  "fields": {
    "学校名称（限20字）": "education.0.school",
    "应聘理由": "narratives.why_company"
  },
  "quirks": {
    "real_keys": true,
    "false_save_error": "commitOthers is not a function",
    "back_blank": true,
    "readonly_date": false
  },
  "save": {"enabled": true, "hints": ["保存"]},
  "submit": {"enabled": false, "hints": ["提交"]}
}
```

## 字段说明

| 键 | 作用 |
|---|---|
| `match.url_patterns` | URL 包含即命中，命中越多优先级越高 |
| `match.widgets` | 页面框架特征，probe 时可采集 |
| `fields` | 页面标签（归一化后）→ canonical id；置信度 0.99 |
| `quirks.real_keys` | 必须真实键盘输入 |
| `quirks.false_save_error` | 假报错文案，出现不代表失败 |
| `quirks.back_blank` | 上一步回退会显示空白 |
| `quirks.readonly_date` | 日期只能点面板 |
| `submit.enabled` | 是否允许自动点到提交按钮（默认 false） |

## 红线

- 不写账号、密码、cookie、token。
- 不写真实个人信息。
- 不放绕过验证码或反自动化的逻辑。
- 一个 PR 一张卡，附脱敏夹具。
