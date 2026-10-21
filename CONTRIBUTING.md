# 贡献

最欢迎的两类贡献：**平台/框架级站点卡**和**失败夹具**。

公司专属的卡不收——它只对一家有效、改版就过期，放在你自己的
`~/.jobpilot/sites/` 就行。公开仓库只收 Element UI、智联这类平台/框架层的共性。

## 站点卡

1. 复制 `sitecards/sites/_template.json`，改名成你的站。
2. 填 `match.url_patterns`、字段映射、quirks。
3. 附一个脱敏的页面夹具到 `fixtures/`（把真实姓名换成「张三」，公司名换掉）。
4. 跑：

   ```bash
   python3 -m jobpilot cards validate
   python3 -m unittest discover -s tests -t .
   python3 -m jobpilot privacy scan
   ```

5. 一个 PR 只加一张卡，且必须是平台/框架级。

规范见 `references/site-card-spec.md`。

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
