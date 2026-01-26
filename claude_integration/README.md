# ReadLater + Claude iOS 集成指南

本指南介绍如何将 ReadLater 稍后阅读应用与 Claude iOS App 结合使用，实现：
- 在 Claude 中提交链接并获取摘要
- 通过 iOS 快捷指令自动化工作流
- 接收推送通知提醒阅读

---

## 方案概览

| 方案 | 复杂度 | 功能 | 适合人群 |
|------|--------|------|---------|
| A. Claude 纯对话 | 简单 | 链接摘要、分析 | 所有人 |
| B. iOS 快捷指令 | 中等 | 分享菜单添加、自动提醒 | iPhone用户 |
| C. API + 快捷指令 | 较高 | 完整功能、持久化存储 | 有服务器的用户 |
| **D. Notion 集成** | 中等 | 同步到Notion数据库、跨设备 | Notion用户（推荐） |

---

## 方案 A：纯 Claude 对话（最简单）

直接在 Claude iOS App 中使用，无需任何配置。

### 使用方式

打开 Claude App，发送：

```
请帮我分析这篇文章：https://example.com/article

请提供：
1. 文章标题和类型
2. 100-200字摘要
3. 3个核心要点
4. 推荐阅读优先级（高/中/低）
```

### 创建 Claude Project（推荐）

1. 打开 Claude iOS App
2. 创建新 Project
3. 在 Instructions 中粘贴 `CLAUDE_SKILL.md` 中的内容
4. 之后在该 Project 中直接发送链接即可

---

## 方案 B：iOS 快捷指令（推荐）

无需服务器，直接调用 Anthropic API。

### 前提条件
- Anthropic API Key（从 console.anthropic.com 获取）

### 创建快捷指令

1. 打开「快捷指令」App
2. 创建新快捷指令
3. 按照 `IOS_SHORTCUTS.md` 中的方案B配置

### 分享菜单集成

配置好后，在 Safari 中点击分享按钮，选择你的快捷指令，即可获取文章摘要。

---

## 方案 C：部署 API 服务器（完整功能）

部署自己的服务器，实现持久化存储和完整功能。

### 1. 部署服务器

```bash
# 克隆项目
git clone <repo-url>
cd hello-world

# 安装依赖
pip install -r requirements.txt
pip install anthropic  # 如果使用Claude摘要

# 配置环境变量
export READLATER_SUMMARIZER=anthropic
export ANTHROPIC_API_KEY=sk-ant-xxx
export READLATER_API_KEY=your_secret_key  # 可选

# 启动API服务器
python api_server.py
```

### 2. 配置 iOS 快捷指令

按照 `IOS_SHORTCUTS.md` 中的方案A配置，使用你的服务器地址。

### 3. 配置推送通知

选择一种推送方式：

#### Bark（国内推荐）
```bash
export READLATER_BARK_URL=https://api.day.app/your_key
```

#### Pushover（国际推荐）
```bash
export READLATER_PUSHOVER_USER=your_user_key
export READLATER_PUSHOVER_TOKEN=your_api_token
```

#### Telegram
```bash
export READLATER_TELEGRAM_BOT=your_bot_token
export READLATER_TELEGRAM_CHAT=your_chat_id
```

### 4. 设置定时提醒

```bash
# 生成 cron 脚本
python app.py setup-reminder

# 或使用 iOS 自动化（方案B）在每天固定时间调用 API
```

---

## 方案 D：Notion 集成（推荐）

将文章同步到 Notion 数据库，享受 Notion 强大的整理和跨设备能力。

### 快速配置

```bash
# 1. 获取 Notion Integration Token
#    访问 https://www.notion.so/my-integrations 创建

# 2. 配置环境变量
export NOTION_TOKEN=secret_xxxxxxxxxxxxx
export NOTION_DATABASE_ID=你的数据库ID
export NOTION_SYNC_ENABLED=true  # 自动同步到Notion

# 3. 启动服务器
python api_server.py
```

### Notion API 接口

```bash
# 添加到 Notion
POST /api/notion/articles
{"url": "https://example.com", "priority": 2}

# 获取 Notion 未读列表
GET /api/notion/articles/unread?limit=10

# 更新状态
POST /api/notion/articles/<page_id>/status
{"status": "finished"}

# 搜索
GET /api/notion/search?q=React
```

### 详细配置

参见 [NOTION_SETUP.md](./NOTION_SETUP.md) 获取完整的 Notion 集成指南。

---

## API 接口文档

### 添加链接
```bash
POST /api/articles
Content-Type: application/json
X-API-Key: your_key  # 如果设置了API密钥

{"url": "https://example.com", "priority": 2, "tags": "tech,ai"}
```

### 仅获取摘要（不保存）
```bash
POST /api/summarize
Content-Type: application/json

{"url": "https://example.com"}
```

### 获取未读列表
```bash
GET /api/articles/unread?limit=5
```

### 搜索文章
```bash
GET /api/search?q=keyword
```

### 标记已读
```bash
POST /api/articles/1/status
Content-Type: application/json

{"status": "finished"}
```

---

## Claude 斜杠命令参考

在 Claude Project 中可以使用的命令：

| 命令 | 说明 | 示例 |
|------|------|------|
| `/read <url>` | 添加并总结链接 | `/read https://example.com` |
| `/list` | 查看待阅读列表 | `/list` |
| `/done <id>` | 标记已读 | `/done 1` |
| `/digest` | 生成每日摘要 | `/digest` |
| `/search <keyword>` | 搜索文章 | `/search React` |

---

## 完整工作流示例

### 日常使用流程

1. **收集阶段**（白天）
   - 在浏览器/App中看到好文章
   - 点击分享 → 选择「添加到稍后阅读」
   - 自动获取摘要并保存

2. **阅读阶段**（晚上/周末）
   - 打开 Claude App
   - 发送 `/list` 查看待阅读列表
   - 根据摘要决定阅读顺序
   - 阅读后发送 `/done <id>` 标记完成

3. **回顾阶段**（每周）
   - 发送 `/digest` 获取综合摘要
   - 回顾本周阅读内容

### 高级用法

```
请帮我分析这5篇文章，并：
1. 按主题分类
2. 找出它们的共同主题
3. 建议阅读顺序
4. 生成综合学习笔记

[链接1]
[链接2]
...
```

---

## 常见问题

### Q: Claude 能直接访问网页吗？
A: Claude iOS App 本身不能直接访问网页。但你可以：
1. 复制文章内容到对话中
2. 使用 iOS 快捷指令先获取内容再传给 Claude
3. 使用方案C的 API 服务器

### Q: 如何实现真正的推送通知？
A: 推荐使用：
- **Bark**（国内）：免费、简单
- **Pushover**（国际）：一次性付费、功能强大
- **iOS 快捷指令自动化**：每天定时检查并显示通知

### Q: 数据存储在哪里？
A:
- 方案A/B：不持久化，仅当次对话
- 方案C：存储在服务器的 SQLite 数据库中

### Q: 如何迁移数据？
A: 数据库文件位于 `~/.readlater/readlater.db`，直接复制即可迁移。

---

## 相关文件

- `CLAUDE_SKILL.md` - Claude Custom Instruction 模板
- `IOS_SHORTCUTS.md` - iOS 快捷指令详细配置
- `NOTION_SETUP.md` - Notion 集成配置指南
- `api_server.py` - API 服务器
- `notion_sync.py` - Notion 同步模块
- `reminder.py` - 推送通知支持
