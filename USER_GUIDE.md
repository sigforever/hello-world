# ReadLater 使用说明

ReadLater 是一个智能稍后阅读工具，帮助你保存、总结和管理待阅读链接。支持 AI 摘要、多渠道通知和云端同步。

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 基本配置

创建配置文件或设置环境变量：

```bash
# AI 摘要配置（可选，默认使用本地摘要）
export READLATER_SUMMARIZER=anthropic  # 可选: local/openai/anthropic
export ANTHROPIC_API_KEY=你的API密钥

# 或使用 OpenAI
export READLATER_SUMMARIZER=openai
export OPENAI_API_KEY=你的API密钥
```

---

## 命令行使用

### 添加文章

```bash
# 基本添加
python app.py add https://example.com/article

# 设置优先级（1=低, 2=中, 3=高）和标签
python app.py add https://example.com/article -p 3 -t "技术,AI"
```

### 查看文章列表

```bash
# 查看所有文章
python app.py list

# 只看未读文章
python app.py list -s unread

# 查看特定文章详情
python app.py show 1
```

### 管理阅读状态

```bash
# 标记为阅读中
python app.py read 1

# 标记为已完成
python app.py done 1

# 归档文章
python app.py archive 1

# 删除文章
python app.py delete 1
```

### 搜索和统计

```bash
# 搜索文章
python app.py search "关键词"

# 查看统计信息
python app.py stats

# 查看当前配置
python app.py config
```

### 提醒功能

```bash
# 手动触发提醒
python app.py remind

# 设置定时提醒（生成 cron 脚本）
python app.py setup-reminder
```

---

## API 服务器

### 启动服务器

```bash
python api_server.py
```

默认运行在 `http://localhost:8080`

### 常用 API

| 功能 | 方法 | 接口 |
|------|------|------|
| 添加链接 | POST | `/api/articles` |
| 获取摘要 | POST | `/api/summarize` |
| 未读列表 | GET | `/api/articles/unread` |
| 搜索 | GET | `/api/search?q=关键词` |
| 更新状态 | POST | `/api/articles/{id}/status` |

### API 示例

```bash
# 添加文章
curl -X POST http://localhost:8080/api/articles \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article", "priority": 2}'

# 获取未读列表
curl http://localhost:8080/api/articles/unread?limit=5
```

---

## iOS 快捷指令

### 设置步骤

1. 启动 API 服务器并确保 iOS 设备能访问
2. 在 iOS 快捷指令 App 中创建新快捷指令
3. 添加「获取 URL」→「获取网页内容」→「发送 HTTP 请求」动作
4. 配置 POST 请求到你的服务器地址

详细配置请参考 `claude_integration/IOS_SHORTCUTS.md`

---

## Claude AI 集成

### 方案一：纯对话模式（最简单）

直接在 Claude 中发送：

```
请帮我分析这篇文章：https://example.com/article

请提供：
1. 文章标题和类型
2. 100-200字摘要
3. 3个核心要点
4. 推荐阅读优先级
```

### 方案二：Notion MCP（推荐）

如果你使用 Notion，可以配置 Notion MCP，让 Claude 直接操作你的 Notion 数据库：

1. 配置 Notion Integration Token
2. 设置 MCP 服务
3. 直接对 Claude 说：「把这篇文章添加到我的稍后阅读数据库」

详细配置请参考 `claude_integration/NOTION_MCP.md`

---

## Notion 同步

### 配置 Notion 集成

```bash
export NOTION_TOKEN=你的Notion_Token
export NOTION_DATABASE_ID=你的数据库ID
export NOTION_SYNC_ENABLED=true
```

### 数据库属性要求

在 Notion 中创建数据库，包含以下属性：
- 标题（Title）
- URL（URL）
- 摘要（Text）
- 状态（Select: 未读/阅读中/已完成/已归档）
- 优先级（Select: 低/中/高）
- 标签（Multi-select）

详细配置请参考 `claude_integration/NOTION_SETUP.md`

---

## 通知配置

支持多种通知方式，通过环境变量配置：

### Bark（iOS 推荐）

```bash
export READLATER_BARK_URL=https://api.day.app/你的密钥
```

### Pushover

```bash
export READLATER_PUSHOVER_USER=你的用户ID
export READLATER_PUSHOVER_TOKEN=你的应用Token
```

### Telegram

```bash
export READLATER_TELEGRAM_BOT=你的机器人Token
export READLATER_TELEGRAM_CHAT=你的聊天ID
```

### Webhook（通用）

```bash
export READLATER_WEBHOOK_URL=https://你的Webhook地址
```

---

## 推荐工作流

### 日常收集

1. 浏览网页时发现好文章
2. 使用 iOS 快捷指令一键保存
3. 系统自动生成 AI 摘要

### 阅读时间

1. 运行 `python app.py list -s unread` 查看待读列表
2. 根据摘要和优先级选择阅读
3. 阅读后标记为已完成

### 每周回顾

1. 运行 `python app.py stats` 查看统计
2. 归档已完成文章
3. 清理不再需要的内容

---

## 常见问题

**Q: 如何切换 AI 摘要后端？**
```bash
export READLATER_SUMMARIZER=local    # 本地摘要（默认）
export READLATER_SUMMARIZER=openai   # 使用 GPT
export READLATER_SUMMARIZER=anthropic # 使用 Claude
```

**Q: 数据存储在哪里？**
默认存储在 `~/.readlater/readlater.db`（SQLite 数据库）

**Q: 如何备份数据？**
直接复制 `~/.readlater/readlater.db` 文件即可

**Q: API 服务器如何开启认证？**
```bash
export READLATER_API_KEY=你的密钥
```
然后在请求中添加 `X-API-Key` 头

---

## 更多资源

- 完整集成方案：`claude_integration/README.md`
- Claude 指令配置：`claude_integration/CLAUDE_SKILL.md`
- iOS 快捷指令：`claude_integration/IOS_SHORTCUTS.md`
- Notion 配置：`claude_integration/NOTION_SETUP.md`
