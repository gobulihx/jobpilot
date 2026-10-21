# 浏览器安装与使用

自动填表要一个能操作网页的浏览器。**强烈建议装**，但装不装由用户决定。

## 装好之后

技能会自己发现并使用，不需要额外配置：

1. 先连你已经开着的 Chrome（调试口 9222）；
2. 连不上就自己开一个专用浏览器（系统 Chrome 或 Playwright 自带的 Chromium）；
3. 登录状态存在 `~/.jobpilot/browser`，第一次登录一次，之后记住；
4. **填完不关页面**，留给用户核对。

## 装法一：Playwright + Chromium（推荐，干净）

装到**运行 jobpilot 的那个 Python** 里：

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

如果系统提示 `externally-managed-environment`：

```bash
python3 -m pip install --user --break-system-packages playwright
python3 -m playwright install chromium
```

或者用 uv：

```bash
uv pip install --python "$(command -v python3)" playwright
python3 -m playwright install chromium
```

首次会下载约 150 MB 的 Chromium。公司网络慢就设置 `HTTPS_PROXY` 再装。

## 装法二：直接用现有 Chrome

适合已经登录过招聘站、不想再下一套浏览器的人。

macOS：

```bash
open -na "Google Chrome" --args --remote-debugging-port=9222
```

Linux：

```bash
google-chrome --remote-debugging-port=9222
```

Windows：给 Chrome 快捷方式加参数 `--remote-debugging-port=9222`，先完全退出 Chrome 再启动。

注意：Chrome 已经在运行时加参数通常不生效，要先退出所有窗口。

## 验证

```bash
python3 ~/.claude/skills/jobpilot/bin/jobpilot doctor
```

看到「自动填表：能用」就成了。

## 第一次用

会弹出一个新浏览器窗口，底部可能有「Chrome 正受自动化软件控制」的提示，正常。
在这个窗口里登录一次招聘站，之后这个专用 profile 会记住。

## 常见问题

| 现象 | 处理 |
|---|---|
| `No module named playwright` | 装到了别的 Python；用 `python3 -m pip`，别用 `pip` |
| 提示 externally-managed | 加 `--break-system-packages`，或用 uv |
| 浏览器下载失败/很慢 | 设置代理；或改用「装法二」直接连 Chrome |
| 连不上 9222 | Chrome 没退出干净，或端口被占；换个端口 9223 |
| 页面打开了但找不到字段 | 站点改版，重新探测；必要时加本地覆盖 |
| 登录状态丢了 | 专用 profile 在 `~/.jobpilot/browser`，别删 |
| 公司电脑不让装 | 不装也能用，生成填写稿手动粘 |

## 隐私

- 不保存账号密码，登录永远由用户自己做。
- 专用 profile 只在本机，权限 700。
- 运行记录和计划落在 `~/.jobpilot/runs/`，不进仓库。

## 卸载

```bash
python3 -m pip uninstall playwright
rm -rf ~/.jobpilot/browser
```
