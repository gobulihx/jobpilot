# 贡献

最欢迎的贡献：**字段别名**、**失败夹具**、**通用规则的修正**。

公司专属的本地覆盖不收——它只对一家有效、改版就过期，放在你自己的
`~/.jobpilot/sites/` 就行。写法见 `references/local-overrides.md`。

## 字段别名

页面标签的变体加进 `jobpilot/schema.py` 的 aliases，附一个最小表单夹具。

## 失败夹具

1. 复制 `fixtures/element-ui.html`，改成触发问题的最小页面。
2. 把真实姓名换成「张三」，公司名换掉。
3. 跑：

   ```bash
   python3 -m unittest discover -s tests -t .
   python3 -m jobpilot privacy scan
   ```

## 提交前检查

- [ ] 没有真实个人信息（身份证、手机、邮箱、公司账号）
- [ ] 没有 cookie、token、密码
- [ ] 新逻辑有测试
- [ ] 用户可见文案里没有技术术语
- [ ] `privacy scan` 通过

## 不要提交

- 真实站点的账号密码
- 真实简历或证件照
- 绕过验证码、反自动化的代码
- 自动提交的默认开关

## 问题模板

提 bug 时附上 `jobpilot doctor --json` 的输出（已脱敏），不要贴完整计划或值文件。
