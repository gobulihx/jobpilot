# 邮箱回执：不接邮箱，接别人的工具

本鲸**不连 IMAP、不存密码、不要授权码**。你用什么工具收邮件都行，
把它导成本地文件，本鲸只读文件。

## 支持什么

| 格式 | 怎么给 |
|---|---|
| JSON | 一个列表，字段见下 |
| EML | 单封 `.eml`，或一个装着 `.eml` 的目录 |
| MBOX | `.mbox` / `.mbx` 归档 |

```bash
python3 ~/.claude/skills/jobpilot/bin/jobpilot inbox --mails mails.json
python3 ~/.claude/skills/jobpilot/bin/jobpilot inbox --mails ./某个目录/      # 里面全是 .eml
```

## JSON 字段

```json
[
  {
    "msgid": "<m1[at]example.com>",
    "from": "hr[at]example.com",
    "subject": "笔试通知",
    "snippet": "请于 10 月 25 日参加在线笔试",
    "date": "2026-10-20"
  }
]
```

只认这五个字段，但别名也收：`id/message_id`、`sender`、`preview/body/text`、
`ts/timestamp`。缺 `msgid` 会自动生成一个，重复的按 `msgid` 去重。

## 推荐工具

| 工具 | 适合 | 链接 |
|---|---|---|
| **himalaya** | 命令行收信，原生支持 JSON 输出 | https://github.com/pimalaya/himalaya |
| **goimapnotify** | 新邮件到达时触发脚本（IMAP IDLE） | https://github.com/shackra/goimapnotify |
| **imap-tools** | 想自己写 Python 小脚本 | https://github.com/ikvk/imap_tools |
| **imapfilter** | 想用规则筛信、转发、移动 | https://github.com/lefcha/imapfilter |

### himalaya

```bash
himalaya --json envelope list -m INBOX > mails.json
python3 ~/.claude/skills/jobpilot/bin/jobpilot inbox --mails mails.json
```

### goimapnotify

在它配置的 `onNewMail` 里跑：

```yaml
onNewMail: 'himalaya --json envelope list -m INBOX > ~/.jobpilot/cache/mails.json && python3 ~/.claude/skills/jobpilot/bin/jobpilot inbox --mails ~/.jobpilot/cache/mails.json'
```

### imap-tools

```python
import json
from imap_tools import MailBox

with MailBox("imap.163.com").login("你的邮箱", "授权码", "INBOX") as box:
    mails = [{
        "msgid": m.uid,
        "from": m.from_,
        "subject": m.subject,
        "snippet": (m.text or "")[:300],
        "date": str(m.date),
    } for m in box.fetch(limit=50)]
json.dump(mails, open("mails.json", "w", encoding="utf-8"), ensure_ascii=False)
```

### 不想折腾

Thunderbird 的「消息过滤器」、163/QQ 邮箱的「收信规则」也能把笔试/面试通知归到一个文件夹，
再手动导出或复制几封给本鲸看。慢一点，但不用装东西。

## 安全

- 163/QQ 等邮箱要用**授权码**，不是登录密码；用完可以随时吊销。
- 不要把授权码写进仓库、脚本或聊天记录；放在系统钥匙串或环境变量里。
- 本鲸只读本地文件，不解析附件，不执行邮件里的 HTML 或脚本。
- 摘要只留前 300 字，不落原始正文。
