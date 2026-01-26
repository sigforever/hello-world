#!/usr/bin/env python3
"""
Notion 数据库集成模块
将稍后阅读的文章同步到 Notion 数据库
"""

import json
import requests
from datetime import datetime
from typing import Optional, List, Dict, Any
from models import Article, ReadStatus, Priority
from config import Config


class NotionClient:
    """Notion API 客户端"""

    BASE_URL = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": self.NOTION_VERSION
        }

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """发送API请求"""
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = requests.request(
                method,
                url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_body = e.response.json() if e.response else {}
            raise Exception(f"Notion API 错误: {error_body.get('message', str(e))}")
        except Exception as e:
            raise Exception(f"请求失败: {str(e)}")

    def get_database(self, database_id: str) -> dict:
        """获取数据库信息"""
        return self._request("GET", f"/databases/{database_id}")

    def query_database(self, database_id: str, filter_obj: dict = None,
                       sorts: list = None, page_size: int = 100) -> List[dict]:
        """查询数据库"""
        data = {"page_size": page_size}
        if filter_obj:
            data["filter"] = filter_obj
        if sorts:
            data["sorts"] = sorts

        result = self._request("POST", f"/databases/{database_id}/query", data)
        return result.get("results", [])

    def create_page(self, database_id: str, properties: dict,
                    content_blocks: list = None) -> dict:
        """在数据库中创建页面（即添加一行）"""
        data = {
            "parent": {"database_id": database_id},
            "properties": properties
        }
        if content_blocks:
            data["children"] = content_blocks

        return self._request("POST", "/pages", data)

    def update_page(self, page_id: str, properties: dict) -> dict:
        """更新页面属性"""
        return self._request("PATCH", f"/pages/{page_id}", {"properties": properties})

    def archive_page(self, page_id: str) -> dict:
        """归档（删除）页面"""
        return self._request("PATCH", f"/pages/{page_id}", {"archived": True})

    def search(self, query: str, filter_type: str = "database") -> List[dict]:
        """搜索 Notion"""
        data = {
            "query": query,
            "filter": {"property": "object", "value": filter_type}
        }
        result = self._request("POST", "/search", data)
        return result.get("results", [])


class NotionSync:
    """Notion 同步服务"""

    # 默认数据库属性结构
    DEFAULT_PROPERTIES = {
        "标题": {"title": {}},
        "URL": {"url": {}},
        "摘要": {"rich_text": {}},
        "状态": {
            "select": {
                "options": [
                    {"name": "未读", "color": "red"},
                    {"name": "阅读中", "color": "yellow"},
                    {"name": "已完成", "color": "green"},
                    {"name": "已归档", "color": "gray"}
                ]
            }
        },
        "优先级": {
            "select": {
                "options": [
                    {"name": "高", "color": "red"},
                    {"name": "中", "color": "yellow"},
                    {"name": "低", "color": "blue"}
                ]
            }
        },
        "标签": {"multi_select": {}},
        "添加时间": {"date": {}},
        "阅读时间": {"date": {}},
        "笔记": {"rich_text": {}}
    }

    # 状态映射
    STATUS_MAP = {
        ReadStatus.UNREAD: "未读",
        ReadStatus.READING: "阅读中",
        ReadStatus.FINISHED: "已完成",
        ReadStatus.ARCHIVED: "已归档"
    }

    STATUS_REVERSE_MAP = {v: k for k, v in STATUS_MAP.items()}

    # 优先级映射
    PRIORITY_MAP = {
        Priority.HIGH: "高",
        Priority.MEDIUM: "中",
        Priority.LOW: "低"
    }

    PRIORITY_REVERSE_MAP = {v: k for k, v in PRIORITY_MAP.items()}

    def __init__(self, config: Config = None):
        self.config = config or Config()
        if not self.config.NOTION_TOKEN:
            raise ValueError("未配置 Notion Token，请设置 NOTION_TOKEN 环境变量")

        self.client = NotionClient(self.config.NOTION_TOKEN)
        self.database_id = self.config.NOTION_DATABASE_ID

    def find_database(self, name: str = "稍后阅读") -> Optional[str]:
        """搜索名为指定名称的数据库"""
        results = self.client.search(name, "database")
        for db in results:
            if db.get("title"):
                title_text = "".join([t.get("plain_text", "") for t in db["title"]])
                if name in title_text:
                    return db["id"]
        return None

    def create_database(self, parent_page_id: str, name: str = "稍后阅读") -> str:
        """创建新的稍后阅读数据库"""
        data = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": name}}],
            "properties": self.DEFAULT_PROPERTIES
        }
        result = self.client._request("POST", "/databases", data)
        return result["id"]

    def article_to_properties(self, article: Article) -> dict:
        """将 Article 转换为 Notion 属性"""
        properties = {
            "标题": {
                "title": [{"text": {"content": article.title or "无标题"}}]
            },
            "URL": {"url": article.url},
            "状态": {"select": {"name": self.STATUS_MAP.get(article.status, "未读")}},
            "优先级": {"select": {"name": self.PRIORITY_MAP.get(article.priority, "中")}},
        }

        # 摘要（限制长度，Notion rich_text 有2000字符限制）
        if article.summary:
            summary_text = article.summary[:1900]
            properties["摘要"] = {
                "rich_text": [{"text": {"content": summary_text}}]
            }

        # 标签
        if article.tags:
            properties["标签"] = {
                "multi_select": [{"name": tag} for tag in article.tags[:10]]
            }

        # 添加时间
        if article.created_at:
            properties["添加时间"] = {
                "date": {"start": article.created_at.isoformat()}
            }

        # 阅读时间
        if article.read_at:
            properties["阅读时间"] = {
                "date": {"start": article.read_at.isoformat()}
            }

        # 笔记
        if article.notes:
            properties["笔记"] = {
                "rich_text": [{"text": {"content": article.notes[:1900]}}]
            }

        return properties

    def properties_to_article(self, page: dict) -> Article:
        """将 Notion 页面转换为 Article"""
        props = page.get("properties", {})

        # 提取标题
        title = ""
        if "标题" in props and props["标题"].get("title"):
            title = "".join([t.get("plain_text", "") for t in props["标题"]["title"]])

        # 提取URL
        url = props.get("URL", {}).get("url", "")

        # 提取摘要
        summary = ""
        if "摘要" in props and props["摘要"].get("rich_text"):
            summary = "".join([t.get("plain_text", "") for t in props["摘要"]["rich_text"]])

        # 提取状态
        status = ReadStatus.UNREAD
        if "状态" in props and props["状态"].get("select"):
            status_name = props["状态"]["select"].get("name", "未读")
            status = self.STATUS_REVERSE_MAP.get(status_name, ReadStatus.UNREAD)

        # 提取优先级
        priority = Priority.MEDIUM
        if "优先级" in props and props["优先级"].get("select"):
            priority_name = props["优先级"]["select"].get("name", "中")
            priority = self.PRIORITY_REVERSE_MAP.get(priority_name, Priority.MEDIUM)

        # 提取标签
        tags = []
        if "标签" in props and props["标签"].get("multi_select"):
            tags = [t.get("name", "") for t in props["标签"]["multi_select"]]

        # 提取时间
        created_at = None
        if "添加时间" in props and props["添加时间"].get("date"):
            date_str = props["添加时间"]["date"].get("start")
            if date_str:
                created_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        read_at = None
        if "阅读时间" in props and props["阅读时间"].get("date"):
            date_str = props["阅读时间"]["date"].get("start")
            if date_str:
                read_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        # 提取笔记
        notes = ""
        if "笔记" in props and props["笔记"].get("rich_text"):
            notes = "".join([t.get("plain_text", "") for t in props["笔记"]["rich_text"]])

        article = Article(
            url=url,
            title=title,
            summary=summary,
            status=status,
            priority=priority,
            tags=tags,
            created_at=created_at,
            read_at=read_at,
            notes=notes
        )
        # 存储 Notion page_id 用于后续更新
        article._notion_page_id = page.get("id")

        return article

    def add_article(self, article: Article) -> dict:
        """添加文章到 Notion 数据库"""
        if not self.database_id:
            raise ValueError("未配置 Notion 数据库 ID")

        properties = self.article_to_properties(article)

        # 创建内容块（可选：将正文作为页面内容）
        content_blocks = []
        if article.content:
            # 将内容分段（Notion 文本块有2000字符限制）
            content_chunks = [article.content[i:i+1900]
                           for i in range(0, min(len(article.content), 10000), 1900)]
            for chunk in content_chunks:
                content_blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": chunk}}]
                    }
                })

        result = self.client.create_page(self.database_id, properties, content_blocks)
        return {
            "success": True,
            "page_id": result.get("id"),
            "url": result.get("url"),
            "message": "已添加到 Notion"
        }

    def find_by_url(self, url: str) -> Optional[dict]:
        """通过URL查找文章"""
        if not self.database_id:
            return None

        filter_obj = {
            "property": "URL",
            "url": {"equals": url}
        }
        results = self.client.query_database(self.database_id, filter_obj)
        return results[0] if results else None

    def update_article(self, page_id: str, article: Article) -> dict:
        """更新 Notion 中的文章"""
        properties = self.article_to_properties(article)
        result = self.client.update_page(page_id, properties)
        return {
            "success": True,
            "page_id": result.get("id"),
            "message": "已更新"
        }

    def update_status(self, page_id: str, status: ReadStatus) -> dict:
        """更新文章状态"""
        properties = {
            "状态": {"select": {"name": self.STATUS_MAP.get(status, "未读")}}
        }
        if status == ReadStatus.FINISHED:
            properties["阅读时间"] = {
                "date": {"start": datetime.now().isoformat()}
            }

        result = self.client.update_page(page_id, properties)
        return {"success": True, "message": f"状态已更新为: {self.STATUS_MAP.get(status)}"}

    def get_unread_articles(self, limit: int = 10) -> List[Article]:
        """获取未读文章"""
        if not self.database_id:
            return []

        filter_obj = {
            "or": [
                {"property": "状态", "select": {"equals": "未读"}},
                {"property": "状态", "select": {"equals": "阅读中"}}
            ]
        }
        sorts = [
            {"property": "优先级", "direction": "ascending"},  # 高优先级在前
            {"property": "添加时间", "direction": "ascending"}  # 早添加的在前
        ]

        results = self.client.query_database(
            self.database_id,
            filter_obj,
            sorts,
            page_size=limit
        )
        return [self.properties_to_article(page) for page in results]

    def get_all_articles(self, status: ReadStatus = None, limit: int = 50) -> List[Article]:
        """获取所有文章"""
        if not self.database_id:
            return []

        filter_obj = None
        if status:
            filter_obj = {
                "property": "状态",
                "select": {"equals": self.STATUS_MAP.get(status, "未读")}
            }

        sorts = [{"property": "添加时间", "direction": "descending"}]

        results = self.client.query_database(
            self.database_id,
            filter_obj,
            sorts,
            page_size=limit
        )
        return [self.properties_to_article(page) for page in results]

    def search_articles(self, keyword: str) -> List[Article]:
        """搜索文章（在标题中搜索）"""
        if not self.database_id:
            return []

        filter_obj = {
            "property": "标题",
            "rich_text": {"contains": keyword}
        }

        results = self.client.query_database(self.database_id, filter_obj)
        return [self.properties_to_article(page) for page in results]

    def delete_article(self, page_id: str) -> dict:
        """删除（归档）文章"""
        self.client.archive_page(page_id)
        return {"success": True, "message": "已归档"}

    def get_statistics(self) -> dict:
        """获取统计信息"""
        if not self.database_id:
            return {"error": "未配置数据库"}

        stats = {
            "unread": 0,
            "reading": 0,
            "finished": 0,
            "archived": 0,
            "total": 0
        }

        # 查询各状态数量
        for status, name in self.STATUS_MAP.items():
            filter_obj = {"property": "状态", "select": {"equals": name}}
            results = self.client.query_database(self.database_id, filter_obj)
            count = len(results)
            stats[status.value] = count
            stats["total"] += count

        return stats


def sync_to_notion(article: Article, config: Config = None) -> dict:
    """
    便捷函数：同步单篇文章到 Notion
    """
    try:
        sync = NotionSync(config)

        # 检查是否已存在
        existing = sync.find_by_url(article.url)
        if existing:
            # 更新已有文章
            return sync.update_article(existing["id"], article)
        else:
            # 添加新文章
            return sync.add_article(article)

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_notion_unread_summary(config: Config = None, limit: int = 5) -> dict:
    """
    便捷函数：获取 Notion 中的未读文章摘要
    """
    try:
        sync = NotionSync(config)
        articles = sync.get_unread_articles(limit)

        if not articles:
            return {
                "success": True,
                "message": "没有未读文章",
                "count": 0,
                "articles": []
            }

        # 生成摘要文本
        summary_text = f"📚 Notion 中有 {len(articles)} 篇待阅读文章：\n\n"
        for i, article in enumerate(articles, 1):
            priority_emoji = {"高": "🔴", "中": "🟡", "低": "🔵"}
            p_name = sync.PRIORITY_MAP.get(article.priority, "中")
            summary_text += f"{i}. {priority_emoji.get(p_name, '🟡')} **{article.title}**\n"
            if article.summary:
                summary_text += f"   摘要: {article.summary[:80]}...\n"
            summary_text += f"   🔗 {article.url}\n\n"

        return {
            "success": True,
            "count": len(articles),
            "summary_text": summary_text,
            "articles": [
                {
                    "title": a.title,
                    "url": a.url,
                    "summary": a.summary,
                    "status": a.status.value,
                    "priority": a.priority.value,
                    "notion_page_id": getattr(a, '_notion_page_id', None)
                }
                for a in articles
            ]
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
