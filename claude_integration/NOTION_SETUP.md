# Notion 集成配置指南

将稍后阅读的文章同步到 Notion 数据库，实现跨设备访问和更好的整理体验。

---

## 快速开始

### 1. 创建 Notion Integration

1. 访问 [Notion Integrations](https://www.notion.so/my-integrations)
2. 点击「+ New integration」
3. 填写基本信息：
   - Name: `ReadLater`
   - Logo: 可选
   - Associated workspace: 选择你的工作区
4. 点击「Submit」创建
5. 复制 **Internal Integration Token**（以 `secret_` 开头）

### 2. 创建或选择数据库

#### 方案 A：使用现有数据库

如果你已有一个数据库，确保它包含以下属性：

| 属性名 | 类型 | 说明 |
|--------|------|------|
| 标题 | Title | 文章标题 |
| URL | URL | 链接地址 |
| 摘要 | Text | 文章摘要 |
| 状态 | Select | 未读/阅读中/已完成/已归档 |
| 优先级 | Select | 高/中/低 |
| 标签 | Multi-select | 分类标签 |
| 添加时间 | Date | 添加日期 |
| 阅读时间 | Date | 完成阅读日期 |
| 笔记 | Text | 个人笔记 |

#### 方案 B：创建新数据库

1. 在 Notion 中创建新页面
2. 输入 `/database` 选择「Database - Inline」
3. 命名为「稍后阅读」
4. 按上表添加属性

### 3. 连接 Integration 到数据库

**重要步骤，必须执行！**

1. 打开你的数据库页面
2. 点击右上角 `...` 菜单
3. 选择「Add connections」
4. 搜索并添加 `ReadLater`（你创建的 Integration）

### 4. 获取数据库 ID

数据库 ID 在 URL 中：
```
https://www.notion.so/workspace/数据库ID?v=xxx
                          ^^^^^^^^
                          这部分就是 ID
```

或者在数据库页面：
1. 点击右上角 `...`
2. 选择「Copy link」
3. 从链接中提取 ID

### 5. 配置环境变量

```bash
# Notion Integration Token
export NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxx

# 数据库 ID
export NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 启用自动同步（可选）
export NOTION_SYNC_ENABLED=true
```

---

## API 使用

### 添加文章到 Notion

```bash
# 仅添加到 Notion
curl -X POST http://localhost:8080/api/notion/articles \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article", "priority": 2, "tags": "tech,ai"}'
```

### 添加到本地 + 同步到 Notion

```bash
curl -X POST http://localhost:8080/api/articles \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article", "sync_notion": true}'
```

### 获取 Notion 未读列表

```bash
curl http://localhost:8080/api/notion/articles/unread?limit=10
```

### 更新文章状态

```bash
curl -X POST http://localhost:8080/api/notion/articles/<page_id>/status \
  -H "Content-Type: application/json" \
  -d '{"status": "finished"}'
```

### 搜索 Notion 文章

```bash
curl "http://localhost:8080/api/notion/search?q=React"
```

---

## iOS 快捷指令集成

### 添加到 Notion 的快捷指令

```
动作1: 获取剪贴板（或分享输入的URL）

动作2: 获取 URL 的内容
  URL: http://你的服务器:8080/api/notion/articles
  方法: POST
  请求体: JSON
  {
    "url": [剪贴板内容],
    "priority": 2
  }

动作3: 获取字典值
  键: page_id

动作4: 显示通知
  标题: ✅ 已添加到 Notion
  内容: 文章已保存到稍后阅读数据库
```

### 查看 Notion 未读列表

```
动作1: 获取 URL 的内容
  URL: http://你的服务器:8080/api/notion/articles/unread?limit=5
  方法: GET

动作2: 获取字典值
  键: summary_text

动作3: 显示结果
  [summary_text]
```

---

## Claude 集成

在 Claude iOS App 的 Project Instructions 中添加：

```
你是稍后阅读助手，数据存储在 Notion 中。

## API 端点
- 服务器: http://your-server:8080
- 添加到Notion: POST /api/notion/articles {"url": "..."}
- 获取未读: GET /api/notion/articles/unread
- 更新状态: POST /api/notion/articles/<page_id>/status {"status": "finished"}

## 可用状态
- unread: 未读
- reading: 阅读中
- finished: 已完成
- archived: 已归档

当用户分享链接时，调用 API 添加到 Notion 并返回摘要。
```

---

## 数据库视图建议

在 Notion 中创建以下视图以便管理：

### 1. 待阅读视图（看板）
- 按状态分组
- 显示：标题、优先级、添加时间

### 2. 按优先级视图（表格）
- 筛选：状态 = 未读 或 阅读中
- 排序：优先级（降序）→ 添加时间（升序）

### 3. 本周完成（画廊）
- 筛选：阅读时间 = 本周
- 显示：标题、摘要、标签

### 4. 归档（表格）
- 筛选：状态 = 已归档
- 排序：阅读时间（降序）

---

## 高级功能

### 自动同步所有新增文章

设置环境变量：
```bash
export NOTION_SYNC_ENABLED=true
```

之后所有通过 `/api/articles` 添加的文章都会自动同步到 Notion。

### 双向同步（手动）

如果需要将 Notion 中手动添加的文章同步到本地：

```python
from notion_sync import NotionSync
from storage import Storage
from config import Config

config = Config()
notion = NotionSync(config)
storage = Storage(config.get_db_path())

# 获取 Notion 中的所有文章
articles = notion.get_all_articles()

# 同步到本地
for article in articles:
    if not storage.get_article_by_url(article.url):
        storage.add_article(article)
```

---

## 故障排除

### 错误：Notion 未配置或不可用
- 检查 `NOTION_TOKEN` 环境变量是否设置
- 检查 `NOTION_DATABASE_ID` 是否正确

### 错误：Could not find database
- 确认数据库已连接到 Integration（步骤3）
- 检查数据库 ID 是否正确

### 错误：Validation error - property not found
- 确认数据库包含所有必需的属性
- 属性名称必须完全匹配（区分大小写）

### 文章添加成功但属性为空
- 检查属性类型是否正确
- Title 属性必须是「Title」类型
- URL 属性必须是「URL」类型

---

## 完整工作流示例

1. **收集** - 在 Safari 中看到好文章，分享到快捷指令
2. **同步** - 自动添加到 Notion 数据库并生成摘要
3. **整理** - 在 Notion 中按标签、优先级整理
4. **阅读** - 使用 Notion 的阅读器视图阅读
5. **完成** - 标记为已完成，记录笔记
6. **回顾** - 在 Claude 中生成阅读报告
