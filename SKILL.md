---
name: jobpilot
description: 求职流水线：建档、找岗、筛岗、网申填表、投递台账、回执监控。当用户提到 求职、找工作、秋招、春招、网申、投简历、岗位、JD、笔试、面试、offer、投递记录 时使用。
---

# jobpilot

把求职从「每次重新填一遍」变成「一次建档，每岗三分钟」。

先读这一节，再动手。下文 `$SKILL_DIR` 指**本文件所在的目录**（也就是技能目录）。

## 用户只需要说话

| 用户说 | 你做 |
|---|---|
| 帮我建求职档案 / 开始求职 | doctor → init（在对话里问 12 个问题） |
| 今天有什么能投的 | 找岗 → 筛岗，给三档结论 |
| 这个岗位值不值得投 | 对照硬门槛，给推荐投/备选/不投 |
| 投这个 | probe → plan → review → run/sheet |
| 有回音吗 | 取邮件 → inbox，提议改状态 |
| 我还缺什么 | values missing，翻译成人话 |

**命令是你的工具，不是用户的。** 不要念命令、不要让用户复制命令、不要说
「你可以运行 …」。用户只需要回答问题和点头。

## 六条铁律

1. **默认不提交。** `dry_run` 是默认值。点提交前必须让用户明确确认，最好让他把公司名打一遍。
2. **每个写进页面的值都要有来源。** 来源是 `~/.jobpilot/values.json` 里的路径；找不到就停下来问，不许自己编。
3. **缺值不编。** 留空，列进「待补」，提交前再说。
4. **每轮最多问 3 项。** 一次给一堆字段，用户就不想干了。
5. **不代注册、不代过验证码、不代实人认证、不代聊。** BOSS/智联只读浏览。
6. **用户数据只在 `~/.jobpilot`。** 不进仓库，不进日志，不外传。
7. **填完不关页面。** 用户要看一眼填得怎么样；浏览器和标签页都留着。

## 第一次使用

用户说「帮我弄求职助手」「开始求职」之类时：

1. 跑一次自检，把结果翻译成人话（不要报库名）：
   ```bash
   python3 "$SKILL_DIR/bin/jobpilot" doctor
   ```
2. 建档。**在对话里问，不要直接跑交互式命令**（技能环境里没有一问一答的终端）。
   `--questions` / `--answers` 是给你用的，不要把这两个命令念给用户。
   先取问题清单：
   ```bash
   python3 "$SKILL_DIR/bin/jobpilot" init --questions
   ```
   分 4 轮问，每轮 3 个，只收 12 个字段。问完写成 `answers.json`（键是 path）：
   ```json
   {"person.name": "张三", "contact.phone": "138xxxx0000",
    "contact.email": "你的邮箱", "education.0.school": "示例大学",
    "intent.directions": "风险,数据"}
   ```
   再导入：
   ```bash
   python3 "$SKILL_DIR/bin/jobpilot" init --answers answers.json
   ```
   如果用户已经有一份资料（xlsx、json、简历），先读，能推断的先填好让他点头，不要让他重填。
3. 告诉他两句话就够：数据在哪、下一次说什么。

**不要**在第一次就把家庭、语言成绩、实习全问完。等哪个站真要了再问。

## 五段流程

### 一、找岗

输入：官方公告、招聘页面、用户给的链接、本地时间线文件。
工具顺序：先搜索（exa / DeepSeek Web），拿不到再开浏览器。
**有搜索工具就直接用，不要问用户「要不要联网」。** 没有就不联网，只读用户给的链接和本地文件。
输出：候选清单，每条至少带公司、岗位、城市、截止日、入口。

- 没有搜索工具时，只读用户给的链接和本地文件，不假装联网。
- 遇到登录页、验证码，停下让用户点，不要硬来。

### 二、筛岗

```bash
python3 "$SKILL_DIR/bin/jobpilot" screen --candidates 候选.json --salary-min 20
```

只给三档：**推荐投 / 备选 / 不投**。不要「可以试试」「感兴趣可以投」。

硬门槛逐条对照，不要笼统说「匹配」：毕业时间、学历、专业、英语、薪资下限、城市。
薪资结论要两个来源；只有一来源就标「估算」。查不到的数据明说「缺数据」，不编。

细节见 `references/screening.md`。

### 三、填表（核心）

顺序固定，不要跳步：

**三种填表方式，按有什么选：**

| 有什么 | 怎么填 |
|---|---|
| 本地浏览器（Playwright） | probe → plan → review → run → verify |
| 只有浏览器工具（MCP） | 用工具执行 `runner/probe.js`，把返回值存成 `表单.json`，再 plan → review → **sheet** |
| 都没有 | 让用户贴页面字段，或直接生成填写稿 |

MCP 探测的写法：把 `runner/probe.js` 的内容交给浏览器工具执行，返回的 JSON 原样保存，
`plan --form` 会自己规范化。

```bash
# 1. 认页面：有本地浏览器时直接探测
python3 "$SKILL_DIR/bin/jobpilot" probe --url "https://..."

# 2. 生成计划（模型只做映射，不往页面打字）
python3 "$SKILL_DIR/bin/jobpilot" plan --form 表单.json --card element-ui

# 3. 给用户看一份 diff（掩码）
python3 "$SKILL_DIR/bin/jobpilot" review 计划.json

# 4a. 有浏览器：执行并回读
python3 "$SKILL_DIR/bin/jobpilot" run 计划.json
# 4b. 没有浏览器：生成填写稿
python3 "$SKILL_DIR/bin/jobpilot" sheet 计划.json
```

**审阅时只说三件事**：能填几项、哪几项要确认、哪几项空着。不要念 JSON。

**执行失败就停**，不要重试到天荒地老，也不要用别的方法硬填同一个框。

**执行完不要关浏览器、不要关标签页。** 告诉用户「页面留着，你看一眼，没问题自己点提交」。
第一次自动开专用浏览器时，让用户登录一次，之后会记住。

站点知识见 `references/apply-playbook.md` 和 `references/site-card-spec.md`。
**公司专属的卡只写本地**（`~/.jobpilot/sites/<域名>.json`），不要提交进仓库。

### 四、记账

投完立刻记，幂等，重复写不会多一条：

```bash
python3 "$SKILL_DIR/bin/jobpilot" ledger add --company "某银行" --position "风险岗" \
  --city 杭州 --status submitted
python3 "$SKILL_DIR/bin/jobpilot" ledger export
```

状态只有八个：草稿 / 已填未投 / 已投递 / 筛选中 / 笔试 / 面试 / 录用 / 已结束。

### 五、回执

只读邮件，关键词分类，**提议**状态变更，不自动改。邮件先用邮箱工具取回来，
整理成 `msgid / from / subject / snippet` 四个字段，再喂给 inbox：

```bash
python3 "$SKILL_DIR/bin/jobpilot" inbox --mails 邮件.json
```

用户点头后再加 `--apply`。

## 降级

按阶段降级，不是全局降级。对用户只说「现在能做什么」。

| 缺什么 | 怎么办 |
|---|---|
| 没浏览器 | 出填写稿，用户自己粘 |
| 没搜索 | 只读用户给的链接和本地文件 |
| 没邮箱 | 提醒用户每周导出一次投递记录 |
| 没表格组件 | 导出 csv |

## 说话方式

- 第一句给结论，不铺垫。
- 一次只讲一件事，细节写进文件。
- 不展示堆栈、字段英文名、报错码。
- 保存报错就说「数据可能已经存上了，人家重进核对一下」。
- 页面改版就说「这个站改版了，人家重新认一下，两分钟」。
- 登录过期就说「点一下重新进，人家接着填」。
- 不说「你应该」「你必须」「正确做法是」。
- 不提命令、参数、文件路径，除非用户主动问。

## 数据在哪

| 东西 | 位置 |
|---|---|
| 档案与值 | `~/.jobpilot/profile.json`、`values.json`（600 权限） |
| 台账 | `~/.jobpilot/ledger.db` |
| 每次运行的计划与截图 | `~/.jobpilot/runs/<run_id>/`（700） |
| 导出 | `~/.jobpilot/exports/` |
| 站点卡 | 仓库 `sitecards/`（平台/框架级）+ `~/.jobpilot/sites/`（公司专属，本地优先） |

`JOBPILOT_HOME` 可以改数据目录。

## 失败了怎么办

| 情况 | 处理 |
|---|---|
| 页面结构变了 | 重新 probe，不要沿用旧计划 |
| 计划里的值和值文件不一致 | 重新生成计划（说明用户改过值） |
| 某个框填不进去 | 停下报告，换人工或换填写稿 |
| 上传超限 | 先压图，再传 |
| 被判定异常 | 立刻停手，换渠道或让用户手动 |

## 更多

- `references/apply-playbook.md`：真实网申踩过的坑与处理
- `references/screening.md`：三档判定与红线
- `references/tracking.md`：台账字段、状态机、导出
- `references/site-card-spec.md`：站点卡怎么写
