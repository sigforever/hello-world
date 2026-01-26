# Notion MCP 集成指南

使用 Notion MCP（Model Context Protocol）让 Claude 直接操作你的 Notion 数据库，无需自建服务器。

---

## 什么是 MCP？

MCP（Model Context Protocol）是 Anthropic 推出的协议，允许 Claude 直接与外部工具交互。通过 Notion MCP，你可以：

- 在 Claude 对话中直接添加页面到 Notion
- 查询和搜索 Notion 数据库
- 更新页面内容和属性
- 无需自建服务器或 API

---

## 方案一：Claude Desktop 配置

### 1. 安装 Notion MCP Server

```bash
# 使用 npx（推荐，无需安装）
npx @notionhq/notion-mcp-server

# 或全局安装
npm install -g @notionhq/notion-mcp-server
```

### 2. 获取 Notion Integration Token

1. 访问 [Notion Integrations](https://www.notion.so/my-integrations)
2. 点击「+ New integration」
3. 命名为 `Claude MCP`
4. 复制 **Internal Integration Token**

### 3. 连接 Integration 到数据库

**重要！必须执行此步骤：**

1. 打开你的「稍后阅读」数据库
2. 点击右上角 `...` 菜单
3. 选择「Add connections」
4. 搜索并添加 `Claude MCP`

### 4. 配置 Claude Desktop

编辑 Claude Desktop 配置文件：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "notion": {
      "command": "npx",
      "args": ["@notionhq/notion-mcp-server"],
      "env": {
        "NOTION_API_KEY": "secret_xxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

### 5. 重启 Claude Desktop

重启后，Claude 就可以直接操作你的 Notion 了！

---

## 方案二：Claude Code 配置

### 配置 MCP

在项目根目录创建 `.mcp.json`：

```json
{
  "mcpServers": {
    "notion": {
      "command": "npx",
      "args": ["@notionhq/notion-mcp-server"],
      "env": {
        "NOTION_API_KEY": "secret_xxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

或者在全局配置 `~/.claude/settings.json` 中添加。

---

## 方案三：Claude iOS App（通过代理）

Claude iOS App 目前不直接支持 MCP，但可以通过以下方式实现：

### 使用 MCP 代理服务

1. 在服务器上运行 MCP 代理
2. 通过 iOS 快捷指令调用代理 API

参见本项目的 `api_server.py`，已集成 Notion 支持。

---

## 使用 Notion MCP

配置完成后，在 Claude 中可以直接说：

### 添加链接到稍后阅读

```
请帮我把这篇文章添加到 Notion 的「稍后阅读」数据库：
https://example.com/article

请设置：
- 优先级：高
- 标签：技术、AI
- 生成摘要
```

### 查看未读文章

```
请查询我 Notion「稍后阅读」数据库中所有未读的文章，
按优先级排序，显示标题和摘要。
```

### 标记已读

```
请把「深入理解 React」这篇文章标记为已完成，
并添加笔记：「很好的入门文章，讲解清晰」
```

### 生成阅读报告

```
请统计我本周在 Notion 中完成阅读的文章，
生成一份阅读报告，包括：
- 阅读数量
- 主题分布
- 关键收获
```

---

## Notion 数据库结构

为了获得最佳体验，建议数据库包含以下属性：

| 属性名 | 类型 | 说明 |
|--------|------|------|
| 标题 | Title | 文章标题 |
| URL | URL | 链接地址 |
| 摘要 | Text | 文章摘要 |
| 状态 | Select | 未读 / 阅读中 / 已完成 / 已归档 |
| 优先级 | Select | 高 / 中 / 低 |
| 标签 | Multi-select | 分类标签 |
| 添加时间 | Date | 添加日期 |
| 阅读时间 | Date | 完成日期 |
| 笔记 | Text | 阅读笔记 |

---

## Claude Custom Instruction（配合 MCP）

在 Claude Project 中使用以下指令：

```
你是我的稍后阅读助手，通过 Notion MCP 管理我的阅读列表。

## 核心功能

### /read <链接>
1. 访问链接获取标题和内容
2. 生成 100-200 字摘要
3. 添加到 Notion「稍后阅读」数据库
4. 设置状态为「未读」，优先级为「中」

### /list
查询 Notion 数据库中所有未读/阅读中的文章，按优先级排序显示。

### /done <标题关键词>
1. 搜索匹配的文章
2. 更新状态为「已完成」
3. 设置阅读时间为当前时间

### /digest
生成未读文章的综合摘要报告。

### /note <标题关键词> <笔记内容>
为指定文章添加阅读笔记。

## 输出格式

添加成功后显示：
📚 **[标题]**
🔗 [链接]
📝 [摘要]
✅ 已添加到 Notion
```

---

## MCP 可用工具

Notion MCP 提供以下工具：

| 工具 | 说明 |
|------|------|
| `notion_search` | 搜索页面和数据库 |
| `notion_query_database` | 查询数据库内容 |
| `notion_create_page` | 创建新页面 |
| `notion_update_page` | 更新页面属性 |
| `notion_get_page` | 获取页面详情 |
| `notion_append_blocks` | 追加内容块 |

---

## 故障排除

### Claude 没有显示 Notion 工具

1. 检查配置文件语法是否正确
2. 确认 NOTION_API_KEY 正确
3. 重启 Claude Desktop

### 找不到数据库

1. 确认已将 Integration 连接到数据库
2. 在 Notion 中检查数据库的 Connections 设置

### 权限错误

1. 检查 Integration 是否有读写权限
2. 确认数据库属性名称正确

---

## 与本地 API 配合使用

如果你同时使用本项目的 API 服务器，可以：

1. **本地存储 + Notion 同步**
   - API 服务器保存到本地 SQLite
   - 同时通过 MCP 同步到 Notion

2. **离线支持**
   - 本地数据库作为备份
   - 网络恢复后同步

配置 `NOTION_SYNC_ENABLED=true` 启用自动同步。

---

## 参考资源

- [Notion MCP Server 官方仓库](https://github.com/notionhq/notion-mcp-server)
- [MCP 协议文档](https://modelcontextprotocol.io)
- [Notion API 文档](https://developers.notion.com)
