# ReadLater - 稍后阅读

一个简单高效的命令行稍后阅读工具，帮助你保存链接、智能总结内容，并定期提醒你阅读。

## 功能特性

- **链接保存**: 快速保存任意网页链接
- **智能摘要**: 自动提取网页内容并生成摘要（支持本地/OpenAI/Claude）
- **定期提醒**: 自动提醒未读文章，支持多种通知方式
- **优先级管理**: 为文章设置优先级，重要内容优先阅读
- **标签分类**: 使用标签组织和管理文章
- **搜索功能**: 全文搜索已保存的文章
- **阅读统计**: 追踪阅读进度和习惯

## 安装

```bash
# 克隆项目
git clone <repository-url>
cd hello-world

# 安装依赖
pip install -r requirements.txt
```

## 快速开始

```bash
# 添加链接
python app.py add https://example.com/article

# 添加带优先级和标签的链接
python app.py add https://example.com/article -p 3 -t "tech,python"

# 查看所有文章
python app.py list

# 查看未读文章
python app.py list -s unread

# 查看文章详情
python app.py show 1

# 标记为阅读中
python app.py read 1

# 标记为已完成
python app.py done 1

# 搜索文章
python app.py search "关键词"

# 触发阅读提醒
python app.py remind

# 查看统计
python app.py stats
```

## 命令列表

| 命令 | 说明 |
|------|------|
| `add <url>` | 添加新链接 |
| `list` | 列出文章 |
| `show <id>` | 显示文章详情 |
| `read <id>` | 标记为阅读中 |
| `done <id>` | 标记为已完成 |
| `archive <id>` | 归档文章 |
| `delete <id>` | 删除文章 |
| `search <keyword>` | 搜索文章 |
| `remind` | 触发阅读提醒 |
| `stats` | 显示统计信息 |
| `config` | 显示当前配置 |
| `setup-reminder` | 生成定时提醒脚本 |

## 配置

通过环境变量进行配置：

```bash
# 数据库路径
export READLATER_DB_PATH=~/.readlater/readlater.db

# 摘要后端 (local/openai/anthropic)
export READLATER_SUMMARIZER=openai

# OpenAI 配置
export OPENAI_API_KEY=sk-xxx
export OPENAI_MODEL=gpt-3.5-turbo

# Anthropic 配置
export ANTHROPIC_API_KEY=sk-xxx

# 提醒间隔（小时）
export READLATER_REMINDER_HOURS=24

# 每次提醒的最大文章数
export READLATER_MAX_REMINDERS=5

# Webhook URL（可选，用于钉钉/企业微信等通知）
export READLATER_WEBHOOK_URL=https://...
```

## 定时提醒

使用 cron 设置定时提醒：

```bash
# 生成 cron 配置
python app.py setup-reminder

# 手动添加到 crontab
crontab -e
# 添加: 0 */8 * * * cd /path/to/app && python app.py remind
```

## 项目结构

```
.
├── app.py          # 主应用入口
├── models.py       # 数据模型
├── storage.py      # 数据存储层
├── summarizer.py   # 内容提取与智能摘要
├── reminder.py     # 提醒功能
├── config.py       # 配置管理
├── requirements.txt
└── README.md
```

## License

MIT
