# WeRead Playwright Project

本项目使用 [Playwright](https://playwright.dev/python/) 自动化操作微信读书 (`weread.qq.com`)。

## 快速开始

### 安装依赖

```bash
uv sync
uv run playwright install chromium
```

### 配置

复制 `env.example` 为 `.env` 并配置环境变量：

```bash
WEREAD_HEADLESS=false
WEREAD_DURATION=30
WEREAD_BOOK_INDEX=0
WEREAD_SPEED=medium
WEREAD_SCHEDULE_ENABLED=false
WEREAD_EMAIL_ENABLED=false
WEREAD_BARK_ENABLED=false
```

### 运行

```bash
# 立即运行一次
uv run python main.py

# 或使用定时任务模式（设置 WEREAD_SCHEDULE_ENABLED=true）
uv run python main.py
```

首次运行会显示二维码，使用微信扫码登录。登录后会自动保存 cookies，下次运行无需重新登录。

如果启用了邮件通知，二维码会自动发送到配置的邮箱。

## 邮件配置说明

### Gmail 配置示例

1. 启用两步验证
2. 生成应用专用密码：Google 账户 → 安全性 → 两步验证 → 应用专用密码
3. 配置环境变量：

```bash
WEREAD_EMAIL_ENABLED=true
WEREAD_EMAIL_SMTP=smtp.gmail.com
WEREAD_EMAIL_PORT=587
WEREAD_EMAIL_FROM=your-email@gmail.com
WEREAD_EMAIL_TO=recipient@gmail.com
WEREAD_EMAIL_PASSWORD=your-app-password  # 使用应用专用密码，不是账户密码
```

### QQ 邮箱配置示例

1. 开启 SMTP 服务：设置 → 账户 → POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务
2. 生成授权码（不是QQ密码）
3. 配置环境变量：

```bash
WEREAD_EMAIL_ENABLED=true
WEREAD_EMAIL_SMTP=smtp.qq.com
WEREAD_EMAIL_PORT=587
WEREAD_EMAIL_FROM=your-email@qq.com
WEREAD_EMAIL_TO=recipient@qq.com
WEREAD_EMAIL_PASSWORD=your-authorization-code  # 使用授权码
```

### 163 邮箱配置示例

```bash
WEREAD_EMAIL_ENABLED=true
WEREAD_EMAIL_SMTP=smtp.163.com
WEREAD_EMAIL_PORT=465
WEREAD_EMAIL_FROM=your-email@163.com
WEREAD_EMAIL_TO=recipient@163.com
WEREAD_EMAIL_PASSWORD=your-authorization-code  # 使用授权码
```

### 常见问题

1. **Connection unexpectedly closed**: 检查 SMTP 服务器地址和端口是否正确
2. **SMTP认证失败**: 确认使用的是授权码/应用专用密码，而不是账户密码
3. **连接超时**: 检查网络连接或防火墙设置
4. **Gmail 需要使用端口 587 或 465**
5. **QQ/163 邮箱需要在网页端开启 SMTP 服务并获取授权码**

### SMTP 加密方式配置

可以通过 `WEREAD_EMAIL_SECURITY` 环境变量控制加密方式：

- **auto** (默认): 根据端口自动选择
  - 端口 465: 使用 SSL
  - 端口 587: 使用 TLS (STARTTLS)
- **ssl**: 强制使用 SSL 连接
- **tls**: 强制使用 TLS (STARTTLS) 连接
- **none**: 不使用加密（不推荐）

示例：
```bash
# 强制使用 TLS
WEREAD_EMAIL_SECURITY=tls
WEREAD_EMAIL_PORT=587

# 强制使用 SSL
WEREAD_EMAIL_SECURITY=ssl
WEREAD_EMAIL_PORT=465
```

## 功能

- 支持登录二维码刷新
- 支持保存 cookies
- 支持加载 cookies
- 支持选择最近阅读的第 X 本书开始阅读
- 默认随机选择一本书开始阅读
- 支持自动阅读
- 支持跳到下一章
- 支持读完跳回第一章继续阅读
- 支持选择阅读速度
- 随机单页阅读时间
- 随机翻页时间
- 支持日志
- 支持定时任务
- 支持设置阅读时间
- 支持邮件通知
- 支持 Bark 推送通知
- 异常时强制刷新
- 使用统计



## Develop

```bash
uv sync
uv run playwright install # 
```
