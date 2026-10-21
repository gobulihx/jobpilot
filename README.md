# jobpilot

> 把求职从「每次重新填一遍」变成「一次建档，每岗三分钟」。

一个给中文求职者用的 Claude Code 技能。本地运行，数据不出本机。

- 第一次只问 **12 个筛岗字段**；姓名、身份证等到第一次填表再问
- 网申先探测、再生成计划、**提交前给你看一份 diff**
- 默认 **不提交**，你说投才投
- 选填项不会静默跳过，列出来让你决定
- 字段表不够用？现场加（GRE、证书这类），不用改代码
- 没有浏览器也能用：生成逐字段**填写稿**，复制粘贴
- 投递台账幂等，重复记录不会翻倍

## 30 秒安装

```bash
git clone https://github.com/gobulihx/jobpilot ~/.claude/skills/jobpilot
```

重开 Claude Code，然后说一句：

> 帮我弄求职助手

## 开始用

在任意目录开一个会话，说一句：

> 帮我建求职档案

之后正常说话就行，不用记任何命令：

| 你说 | 它做 |
|---|---|
| 帮我建求职档案 | 分 4 轮问 12 个筛岗问题 |
| 今天有什么能投的 | 找岗、筛岗，给三档结论 |
| 这个岗位值不值得投 | 逐条对照硬门槛 |
| 投这个 | 探测页面 → 生成计划 → 给你看 diff → 你点头才填 |
| 有回音吗 | 扫邮箱，提议改状态 |
| 我还缺什么 | 列出没填的字段 |

**命令是助手内部用的，你不用知道。** 你只管说人话。

## 验证安装（可选）

想先看看它长什么样：

```bash
cd ~/.claude/skills/jobpilot
./bin/jobpilot doctor   # 自检
./bin/jobpilot demo     # 演示数据跑一遍
```

`demo` 会写默认数据目录。想不碰真实档案，先：

```bash
export JOBPILOT_HOME=~/jobpilot-demo
```

## 它怎么工作

```
探页面  →  认字段  →  编计划  →  人审  →  执行  →  回读  →  记账
probe     match      plan      review   run     verify   ledger
```

**大多数情况不需要站点卡。** 字段匹配靠字段表；怪行为靠通用规则：真实键盘输入、
回读核对、不用「上一步」、日期只读现场判断。只有某个站的标签或按钮特别怪，
才在本机加一张覆盖（`~/.jobpilot/sites/`），不随仓库分发。

**这些命令你不用记。** 它们只在助手内部使用；你看到的应该是「还差 3 项，你补一下」，
而不是「请运行 jobpilot values missing」。

**模型不往页面里手打值。** 页面上有什么、该填哪个字段、填什么，都是确定性代码算出来的；
模型只裁决「这个标签到底对应哪个字段」和「低置信项要不要问用户」。

每个写入动作都带一个来源路径，比如 `education.0.school`。
值文件里找不到来源，就不生成动作。

## 能力与降级

| 能力 | 有 | 没有 |
|---|---|---|
| 浏览器（Playwright） | 自动填表 + 回读核对 | 生成填写稿 |
| 搜索（exa / DeepSeek Web） | 找公告、读原文 | 只读你给的链接 |
| 邮箱 | 扫回执、提议改状态 | 每周手动导出一次 |
| openpyxl | 导出 xlsx | 导出 csv |

**装了就会自己用，不用额外配置。**

- 先连你已经开着的 Chrome（调试口 9222）；
- 连不上就自己开一个专用浏览器，第一次登录一次，之后记住；
- 填完**不关页面**，留给你核对，自己点提交。

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

也可以手动开调试口，让它直接用你日常的 Chrome：

```bash
open -na "Google Chrome" --args --remote-debugging-port=9222
```

**搜索工具**（exa / DeepSeek Web）由助手在对话里判断：装了就直接搜，没装就只读你给的链接。
CLI 本身不联网搜索，也不检测你装了哪个搜索工具。

## 隐私

- 数据只在本机 `~/.jobpilot/`，目录 700、值文件 600
- 仓库里没有任何个人信息；CI 会扫描身份证、手机号、邮箱
- 日志脱敏，截图只落本地
- 没有遥测，不上传任何东西

详见 [PRIVACY.md](PRIVACY.md)。

## 它不做什么

- 不代注册、不代过验证码、不代实人认证
- 不代聊（BOSS / 智联只读浏览）
- 不默认提交：`dry_run` → `confirm` → `auto`（按站点白名单）
- 不编造经历：缺值留空，提交前列出来

## 已知限制

- 不内置任何公司的站点卡。字段匹配靠字段表，怪行为靠通用规则；
  某个站特别怪时，才在 `~/.jobpilot/sites/` 加一张本地覆盖。
- 页面改版会让旧计划失效，需要重新探测。
- 只覆盖中国大陆校招站；国际 ATS 未实现。
- 真站 smoke 测试只能手动跑，CI 只跑本地页面。
- `commitOthers` 之类的假保存错误靠站点卡声明，没声明的站会按普通错误处理。

## 贡献

最需要的是**站点卡**：一张卡 + 一个脱敏页面夹具，就能让后面的人少踩一次坑。
规范见 [references/site-card-spec.md](references/site-card-spec.md) 和 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 开发

```bash
python3 -m unittest discover -s tests -t .    # 101 个测试：96 单元 + 5 浏览器
python3 -m jobpilot privacy scan              # 仓库 PII 扫描
```

需要浏览器时：

```bash
python3 -m pip install playwright && python3 -m playwright install chromium
python3 -m unittest tests.e2e.test_fill -v
```

## 许可证

MIT
