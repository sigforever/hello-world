# iOS 快捷指令集成指南

通过 iOS 快捷指令 (Shortcuts) 可以实现：
- 从分享菜单直接添加链接到稍后阅读
- 获取文章摘要
- 查看待阅读列表
- 接收推送通知

## 前置条件

1. 部署 ReadLater API 服务器
2. 获取服务器地址和 API 密钥（可选）
3. 在 iPhone 上安装"快捷指令" App

---

## 快捷指令 1: 添加到稍后阅读

### 创建步骤

1. 打开「快捷指令」App
2. 点击右上角 `+` 创建新快捷指令
3. 添加以下动作：

```
动作1: 获取剪贴板
  或者: 从快捷指令输入获取 URL

动作2: 获取 URL 的内容
  URL: http://你的服务器:8080/api/articles
  方法: POST
  请求体: JSON
  {
    "url": [剪贴板内容],
    "priority": 2
  }
  请求头:
    Content-Type: application/json
    X-API-Key: 你的API密钥

动作3: 获取字典值
  键: article.title

动作4: 显示通知
  标题: 已添加到稍后阅读
  内容: [标题]
```

### 配置分享菜单

1. 点击快捷指令名称旁的 `...`
2. 启用「在分享表单中显示」
3. 选择接受的类型: URL、Safari 网页

### 使用方式

在 Safari 或任何 App 中:
1. 点击分享按钮
2. 选择「添加到稍后阅读」
3. 自动处理并推送通知

---

## 快捷指令 2: 获取链接摘要

### 创建步骤

```
动作1: 从输入获取 URL
  或者: 请求输入 - URL

动作2: 获取 URL 的内容
  URL: http://你的服务器:8080/api/summarize
  方法: POST
  请求体: JSON
  {
    "url": [输入的URL]
  }

动作3: 获取字典值
  键: title

动作4: 获取字典值
  键: summary

动作5: 显示结果
  📚 [标题]

  📝 摘要:
  [摘要内容]
```

---

## 快捷指令 3: 查看待阅读列表

### 创建步骤

```
动作1: 获取 URL 的内容
  URL: http://你的服务器:8080/api/articles/unread?limit=5
  方法: GET

动作2: 获取字典值
  键: summary_text

动作3: 显示结果
  [summary_text]
```

---

## 快捷指令 4: 每日阅读提醒 (自动化)

### 创建自动化

1. 打开「快捷指令」>「自动化」
2. 创建个人自动化
3. 选择触发条件：「特定时间」（如每天早上 9:00）

```
动作1: 获取 URL 的内容
  URL: http://你的服务器:8080/api/articles/unread?limit=3
  方法: GET

动作2: 获取字典值
  键: count

动作3: 如果 [count] > 0

  动作3a: 获取字典值
    键: summary_text

  动作3b: 显示通知
    标题: 📚 今日阅读提醒
    内容: [summary_text]

动作4: 否则

  动作4a: 显示通知
    标题: ✅ 阅读清零
    内容: 太棒了！没有待阅读的文章
```

---

## 快捷指令 5: 与 Claude 联动

### 方案A: 复制摘要到 Claude

```
动作1: 获取 URL 的内容 (api/summarize)

动作2: 组合文本
  请帮我进一步分析这篇文章:

  标题: [title]
  摘要: [summary]
  链接: [url]

  请提供:
  1. 深入分析
  2. 相关延伸阅读建议
  3. 学习要点

动作3: 打开 Claude App

动作4: 复制到剪贴板
```

### 方案B: 使用 Anthropic API 直接生成

```
动作1: 获取 URL 的内容
  URL: https://api.anthropic.com/v1/messages
  方法: POST
  请求头:
    x-api-key: 你的Anthropic API密钥
    anthropic-version: 2023-06-01
    Content-Type: application/json
  请求体:
  {
    "model": "claude-3-haiku-20240307",
    "max_tokens": 1024,
    "messages": [
      {
        "role": "user",
        "content": "请为这个链接生成摘要: [URL]"
      }
    ]
  }

动作2: 获取字典值
  键: content[0].text

动作3: 显示结果
```

---

## 推送通知配置

### 方案1: 使用 Pushover (推荐)

1. 安装 Pushover App
2. 注册账号获取 User Key 和 API Token
3. 设置环境变量：
   ```bash
   export READLATER_PUSHOVER_USER=你的user_key
   export READLATER_PUSHOVER_TOKEN=你的api_token
   ```

### 方案2: 使用 Bark (国内推荐)

1. 安装 Bark App
2. 获取推送地址
3. 设置 Webhook：
   ```bash
   export READLATER_WEBHOOK_URL=https://api.day.app/你的key/
   ```

### 方案3: 使用 IFTTT

1. 创建 IFTTT Applet
2. 触发器: Webhook
3. 动作: iOS 通知
4. 设置 Webhook URL

---

## 快捷指令下载链接

> 注意：以下链接需要你手动配置服务器地址和 API 密钥

- [添加到稍后阅读](#) - 从分享菜单添加链接
- [获取摘要](#) - 快速获取文章摘要
- [今日阅读](#) - 查看待阅读列表
- [阅读提醒](#) - 每日自动提醒

---

## 故障排除

### 问题：无法连接到服务器
- 检查服务器是否运行
- 确认网络连接正常
- 如果使用局域网，确保 iPhone 在同一网络

### 问题：API 返回 401
- 检查 X-API-Key 是否正确
- 确认环境变量 READLATER_API_KEY 已设置

### 问题：摘要生成失败
- 检查 AI 后端配置（ANTHROPIC_API_KEY 或 OPENAI_API_KEY）
- 某些网站可能限制爬取，尝试其他链接
