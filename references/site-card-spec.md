# 站点卡规范

站点卡**不是公司白名单**。它只描述两件代码猜不到的事：

1. **字段写法不一样**：这个站把「最高学历学校」写成什么标签，对应哪个 canonical 字段。
2. **行为不一样**：必须真实键盘输入、保存报假错、上一步回退空白、日期只能点面板。

字段的通用匹配由 `jobpilot/schema.py` 的标签与别名负责，**不需要站点卡**。

## 只公开平台/框架卡

| 层 | 放哪 | 进仓库吗 |
|---|---|---|
| `_generic.json` | 仓库 | 是 |
| `ats/*.json`（Element UI、智联这类平台/框架） | 仓库 | 是 |
| 公司专属卡 | `~/.jobpilot/sites/<域名>.json` | **否** |

原因：公司站改版快，一张卡只对一家有效。堆在仓库里会变成过期文件集合，
也会让人误以为「这个工具只支持这几家公司」。本地卡优先级最高，随时可改。

## 结构

```json
{
  "schema_version": 1,
  "id": "my-bank",
  "kind": "site",
  "match": {
    "url_patterns": ["my-bank.example"],
    "widgets": [],
    "hints": ["这家银行的校招站"]
  },
  "fields": {
    "页面上的奇怪标签": "education.0.school"
  },
  "quirks": {
    "real_keys": true,
    "false_save_error": "保存按钮报的那句话",
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

## 怎么写一张本地卡

```bash
cp ~/.claude/skills/jobpilot/sitecards/sites/_template.json \
   ~/.jobpilot/sites/my-bank.json
# 改 id、url_patterns、fields、quirks
python3 ~/.claude/skills/jobpilot/bin/jobpilot cards validate
```

## 红线

- 不写账号、密码、cookie、token。
- 不写真实个人信息。
- 不放绕过验证码或反自动化的逻辑。
- 公开 PR 只收平台/框架卡，并附脱敏夹具。
