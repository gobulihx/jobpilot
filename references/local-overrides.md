# 本地覆盖（可选）

**默认不需要。** 字段匹配靠字段表，怪行为靠通用规则。只有某个站的标签或按钮
特别怪，才在本机写一张覆盖。

## 什么时候写

- 页面标签和字段表差太远，自动匹配认不出来。
- 按钮文案很怪，找不到保存/提交。
- 某个站有独特的多步结构，需要固定 URL 或字段映射。

## 放哪

```
~/.jobpilot/sites/<域名>.json
```

不随仓库分发。仓库里只有模板 `sitecards/sites/_template.json`。

## 怎么写

```bash
cp ~/.claude/skills/jobpilot/sitecards/sites/_template.json \
   ~/.jobpilot/sites/my-bank.json
```

只填你真正需要的部分：

```json
{
  "schema_version": 1,
  "id": "my-bank",
  "match": {"url_patterns": ["my-bank.example"]},
  "fields": {"页面上的怪标签": "education.0.school"},
  "save": {"hints": ["暂存"]},
  "submit": {"hints": ["确认投递"]}
}
```

其余键会从默认值继承。

## 不需要写进卡里的事

这些已经在内核里，所有站通用：

- 真实键盘输入（不用 JS 直接赋值）
- 保存后回读核对（不信弹窗）
- 不点「上一步」，用刷新重进
- 日期只读就点面板
- 提交前必须用户确认

## 红线

不写账号、密码、cookie、token；不写真实个人信息；不做绕过验证码的逻辑。
