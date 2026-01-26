#!/usr/bin/env python3
"""
ReadLater HTTP API Server
提供RESTful API，支持iOS Shortcuts和Claude集成
"""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from typing import Optional

from models import Article, ReadStatus, Priority
from storage import Storage
from summarizer import process_url, ContentExtractor
from reminder import ReminderService
from config import Config

# Notion 支持（可选）
try:
    from notion_sync import NotionSync, sync_to_notion, get_notion_unread_summary
    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False


class ReadLaterAPI:
    """API业务逻辑层"""

    def __init__(self):
        self.config = Config()
        self.storage = Storage(self.config.get_db_path())
        self.reminder_service = ReminderService(self.storage, self.config)

        # 初始化 Notion 同步
        self.notion_sync = None
        if NOTION_AVAILABLE and self.config.NOTION_TOKEN and self.config.NOTION_DATABASE_ID:
            try:
                self.notion_sync = NotionSync(self.config)
            except Exception as e:
                print(f"Notion 初始化失败: {e}")

    def add_url(self, url: str, priority: int = 2, tags: str = "",
                sync_notion: bool = None) -> dict:
        """添加新链接"""
        # 检查是否已存在（本地数据库）
        existing = self.storage.get_article_by_url(url)
        if existing:
            return {
                "success": False,
                "error": "链接已存在",
                "article": self._article_to_dict(existing)
            }

        try:
            # 提取内容和生成摘要
            title, content, summary = process_url(url, self.config)

            # 创建文章对象
            article = Article(
                url=url,
                title=title,
                content=content,
                summary=summary,
                priority=Priority(priority),
                tags=tags.split(',') if tags else []
            )

            # 保存到本地数据库
            article_id = self.storage.add_article(article)
            article.id = article_id

            result = {
                "success": True,
                "message": "已添加到稍后阅读列表",
                "article": self._article_to_dict(article)
            }

            # 同步到 Notion
            should_sync = sync_notion if sync_notion is not None else self.config.NOTION_SYNC_ENABLED
            if should_sync and self.notion_sync:
                try:
                    notion_result = self.notion_sync.add_article(article)
                    result["notion"] = notion_result
                    result["message"] += " (已同步到 Notion)"
                except Exception as e:
                    result["notion_error"] = str(e)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def summarize_url_only(self, url: str) -> dict:
        """仅获取链接摘要，不保存"""
        try:
            title, content, summary = process_url(url, self.config)
            return {
                "success": True,
                "url": url,
                "title": title,
                "summary": summary,
                "content_preview": content[:500] + "..." if len(content) > 500 else content
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_articles(self, status: str = None, limit: int = 20) -> dict:
        """获取文章列表"""
        status_filter = None
        if status:
            try:
                status_filter = ReadStatus(status)
            except ValueError:
                return {"success": False, "error": f"无效的状态: {status}"}

        articles = self.storage.get_all_articles(status=status_filter, limit=limit)
        return {
            "success": True,
            "count": len(articles),
            "articles": [self._article_to_dict(a) for a in articles]
        }

    def get_article(self, article_id: int) -> dict:
        """获取单篇文章详情"""
        article = self.storage.get_article(article_id)
        if not article:
            return {"success": False, "error": f"找不到文章 ID: {article_id}"}
        return {
            "success": True,
            "article": self._article_to_dict(article)
        }

    def get_unread_summary(self, limit: int = 5) -> dict:
        """获取未读文章摘要（用于推送/Claude）"""
        articles = self.storage.get_unread_articles(limit=limit)

        if not articles:
            return {
                "success": True,
                "message": "没有未读文章",
                "count": 0,
                "articles": []
            }

        # 生成友好的摘要文本
        summary_text = f"📚 你有 {len(articles)} 篇待阅读文章：\n\n"
        for i, article in enumerate(articles, 1):
            priority_emoji = {Priority.LOW: "🔵", Priority.MEDIUM: "🟡", Priority.HIGH: "🔴"}
            summary_text += f"{i}. {priority_emoji[article.priority]} **{article.title}**\n"
            summary_text += f"   摘要: {article.summary[:100]}...\n\n"

        return {
            "success": True,
            "count": len(articles),
            "summary_text": summary_text,
            "articles": [self._article_to_dict(a) for a in articles]
        }

    def mark_status(self, article_id: int, status: str) -> dict:
        """更新文章状态"""
        article = self.storage.get_article(article_id)
        if not article:
            return {"success": False, "error": f"找不到文章 ID: {article_id}"}

        try:
            new_status = ReadStatus(status)
        except ValueError:
            return {"success": False, "error": f"无效的状态: {status}"}

        article.status = new_status
        if new_status == ReadStatus.FINISHED:
            article.read_at = datetime.now()

        self.storage.update_article(article)
        return {
            "success": True,
            "message": f"已将文章标记为 {status}",
            "article": self._article_to_dict(article)
        }

    def search(self, keyword: str) -> dict:
        """搜索文章"""
        articles = self.storage.search_articles(keyword)
        return {
            "success": True,
            "keyword": keyword,
            "count": len(articles),
            "articles": [self._article_to_dict(a) for a in articles]
        }

    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = self.storage.get_statistics()
        return {
            "success": True,
            "statistics": stats
        }

    def delete_article(self, article_id: int) -> dict:
        """删除文章"""
        article = self.storage.get_article(article_id)
        if not article:
            return {"success": False, "error": f"找不到文章 ID: {article_id}"}

        self.storage.delete_article(article_id)
        return {
            "success": True,
            "message": f"已删除文章: {article.title}"
        }

    def _article_to_dict(self, article: Article) -> dict:
        """将Article对象转换为字典"""
        return {
            "id": article.id,
            "url": article.url,
            "title": article.title,
            "summary": article.summary,
            "status": article.status.value,
            "priority": article.priority.value,
            "priority_name": article.priority.name,
            "tags": article.tags,
            "created_at": article.created_at.isoformat() if article.created_at else None,
            "read_at": article.read_at.isoformat() if article.read_at else None
        }

    # ========== Notion 相关方法 ==========

    def notion_add_url(self, url: str, priority: int = 2, tags: str = "") -> dict:
        """直接添加链接到 Notion（不保存到本地）"""
        if not self.notion_sync:
            return {"success": False, "error": "Notion 未配置或不可用"}

        try:
            # 提取内容和生成摘要
            title, content, summary = process_url(url, self.config)

            # 创建文章对象
            article = Article(
                url=url,
                title=title,
                content=content,
                summary=summary,
                priority=Priority(priority),
                tags=tags.split(',') if tags else []
            )

            # 检查 Notion 中是否已存在
            existing = self.notion_sync.find_by_url(url)
            if existing:
                return {
                    "success": False,
                    "error": "链接已存在于 Notion",
                    "page_id": existing.get("id")
                }

            # 添加到 Notion
            result = self.notion_sync.add_article(article)
            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def notion_get_unread(self, limit: int = 10) -> dict:
        """获取 Notion 中的未读文章"""
        if not self.notion_sync:
            return {"success": False, "error": "Notion 未配置或不可用"}

        try:
            return get_notion_unread_summary(self.config, limit)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def notion_get_articles(self, status: str = None, limit: int = 50) -> dict:
        """获取 Notion 中的文章列表"""
        if not self.notion_sync:
            return {"success": False, "error": "Notion 未配置或不可用"}

        try:
            status_filter = None
            if status:
                try:
                    status_filter = ReadStatus(status)
                except ValueError:
                    return {"success": False, "error": f"无效的状态: {status}"}

            articles = self.notion_sync.get_all_articles(status_filter, limit)
            return {
                "success": True,
                "count": len(articles),
                "articles": [
                    {
                        "title": a.title,
                        "url": a.url,
                        "summary": a.summary,
                        "status": a.status.value,
                        "priority": a.priority.value,
                        "tags": a.tags,
                        "notion_page_id": getattr(a, '_notion_page_id', None)
                    }
                    for a in articles
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def notion_update_status(self, page_id: str, status: str) -> dict:
        """更新 Notion 中文章的状态"""
        if not self.notion_sync:
            return {"success": False, "error": "Notion 未配置或不可用"}

        try:
            new_status = ReadStatus(status)
        except ValueError:
            return {"success": False, "error": f"无效的状态: {status}"}

        try:
            return self.notion_sync.update_status(page_id, new_status)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def notion_search(self, keyword: str) -> dict:
        """在 Notion 中搜索文章"""
        if not self.notion_sync:
            return {"success": False, "error": "Notion 未配置或不可用"}

        try:
            articles = self.notion_sync.search_articles(keyword)
            return {
                "success": True,
                "keyword": keyword,
                "count": len(articles),
                "articles": [
                    {
                        "title": a.title,
                        "url": a.url,
                        "summary": a.summary,
                        "notion_page_id": getattr(a, '_notion_page_id', None)
                    }
                    for a in articles
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def notion_stats(self) -> dict:
        """获取 Notion 统计信息"""
        if not self.notion_sync:
            return {"success": False, "error": "Notion 未配置或不可用"}

        try:
            stats = self.notion_sync.get_statistics()
            return {"success": True, "statistics": stats}
        except Exception as e:
            return {"success": False, "error": str(e)}


class APIHandler(BaseHTTPRequestHandler):
    """HTTP请求处理器"""

    api = ReadLaterAPI()

    # API密钥验证（可选）
    API_KEY = os.environ.get('READLATER_API_KEY', '')

    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-API-Key')
        self.end_headers()

    def _verify_api_key(self) -> bool:
        """验证API密钥"""
        if not self.API_KEY:
            return True  # 未设置密钥则跳过验证

        auth_header = self.headers.get('X-API-Key') or self.headers.get('Authorization', '').replace('Bearer ', '')
        return auth_header == self.API_KEY

    def _send_json(self, data: dict, status_code=200):
        self._set_headers(status_code)
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))

    def _get_json_body(self) -> dict:
        """解析JSON请求体"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        return json.loads(body.decode('utf-8'))

    def do_OPTIONS(self):
        """处理CORS预检请求"""
        self._set_headers(200)

    def do_GET(self):
        """处理GET请求"""
        if not self._verify_api_key():
            self._send_json({"success": False, "error": "Invalid API key"}, 401)
            return

        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 路由
        if path == '/api/articles':
            status = query.get('status', [None])[0]
            limit = int(query.get('limit', [20])[0])
            result = self.api.get_articles(status, limit)

        elif path == '/api/articles/unread':
            limit = int(query.get('limit', [5])[0])
            result = self.api.get_unread_summary(limit)

        elif path.startswith('/api/articles/'):
            try:
                article_id = int(path.split('/')[-1])
                result = self.api.get_article(article_id)
            except ValueError:
                result = {"success": False, "error": "Invalid article ID"}

        elif path == '/api/search':
            keyword = query.get('q', [''])[0]
            if not keyword:
                result = {"success": False, "error": "Missing search keyword"}
            else:
                result = self.api.search(keyword)

        elif path == '/api/stats':
            result = self.api.get_stats()

        elif path == '/api/health':
            result = {"success": True, "status": "healthy", "version": "1.1.0",
                     "notion_enabled": self.api.notion_sync is not None}

        # Notion 相关路由
        elif path == '/api/notion/articles':
            status = query.get('status', [None])[0]
            limit = int(query.get('limit', [50])[0])
            result = self.api.notion_get_articles(status, limit)

        elif path == '/api/notion/articles/unread':
            limit = int(query.get('limit', [10])[0])
            result = self.api.notion_get_unread(limit)

        elif path == '/api/notion/search':
            keyword = query.get('q', [''])[0]
            if not keyword:
                result = {"success": False, "error": "Missing search keyword"}
            else:
                result = self.api.notion_search(keyword)

        elif path == '/api/notion/stats':
            result = self.api.notion_stats()

        elif path == '/':
            result = {
                "name": "ReadLater API",
                "version": "1.1.0",
                "notion_enabled": self.api.notion_sync is not None,
                "endpoints": {
                    "POST /api/articles": "添加新链接（可选同步到Notion）",
                    "POST /api/summarize": "仅获取链接摘要（不保存）",
                    "GET /api/articles": "获取文章列表",
                    "GET /api/articles/unread": "获取未读文章摘要",
                    "GET /api/articles/<id>": "获取文章详情",
                    "POST /api/articles/<id>/status": "更新文章状态",
                    "DELETE /api/articles/<id>": "删除文章",
                    "GET /api/search?q=keyword": "搜索文章",
                    "GET /api/stats": "获取统计信息"
                },
                "notion_endpoints": {
                    "POST /api/notion/articles": "添加链接到Notion",
                    "GET /api/notion/articles": "获取Notion文章列表",
                    "GET /api/notion/articles/unread": "获取Notion未读文章",
                    "POST /api/notion/articles/<page_id>/status": "更新Notion文章状态",
                    "GET /api/notion/search?q=keyword": "搜索Notion文章",
                    "GET /api/notion/stats": "获取Notion统计信息"
                }
            }
        else:
            result = {"success": False, "error": "Not found"}
            self._send_json(result, 404)
            return

        self._send_json(result)

    def do_POST(self):
        """处理POST请求"""
        if not self._verify_api_key():
            self._send_json({"success": False, "error": "Invalid API key"}, 401)
            return

        parsed = urlparse(self.path)
        path = parsed.path

        try:
            body = self._get_json_body()
        except json.JSONDecodeError:
            self._send_json({"success": False, "error": "Invalid JSON"}, 400)
            return

        # 路由
        if path == '/api/articles':
            url = body.get('url')
            if not url:
                result = {"success": False, "error": "Missing URL"}
            else:
                priority = body.get('priority', 2)
                tags = body.get('tags', '')
                sync_notion = body.get('sync_notion')
                result = self.api.add_url(url, priority, tags, sync_notion)

        elif path == '/api/summarize':
            url = body.get('url')
            if not url:
                result = {"success": False, "error": "Missing URL"}
            else:
                result = self.api.summarize_url_only(url)

        # Notion 相关 POST 路由
        elif path == '/api/notion/articles':
            url = body.get('url')
            if not url:
                result = {"success": False, "error": "Missing URL"}
            else:
                priority = body.get('priority', 2)
                tags = body.get('tags', '')
                result = self.api.notion_add_url(url, priority, tags)

        elif '/api/notion/articles/' in path and path.endswith('/status'):
            page_id = path.split('/')[-2]
            status = body.get('status')
            if not status:
                result = {"success": False, "error": "Missing status"}
            else:
                result = self.api.notion_update_status(page_id, status)

        elif path.endswith('/status'):
            try:
                article_id = int(path.split('/')[-2])
                status = body.get('status')
                if not status:
                    result = {"success": False, "error": "Missing status"}
                else:
                    result = self.api.mark_status(article_id, status)
            except (ValueError, IndexError):
                result = {"success": False, "error": "Invalid request"}
        else:
            result = {"success": False, "error": "Not found"}
            self._send_json(result, 404)
            return

        self._send_json(result, 200 if result.get('success') else 400)

    def do_DELETE(self):
        """处理DELETE请求"""
        if not self._verify_api_key():
            self._send_json({"success": False, "error": "Invalid API key"}, 401)
            return

        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith('/api/articles/'):
            try:
                article_id = int(path.split('/')[-1])
                result = self.api.delete_article(article_id)
            except ValueError:
                result = {"success": False, "error": "Invalid article ID"}
        else:
            result = {"success": False, "error": "Not found"}
            self._send_json(result, 404)
            return

        self._send_json(result)

    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {args[0]}")


def run_server(host='0.0.0.0', port=8080):
    """启动API服务器"""
    server = HTTPServer((host, port), APIHandler)

    # 检查 Notion 状态
    config = Config()
    notion_status = "已启用 ✓" if (config.NOTION_TOKEN and config.NOTION_DATABASE_ID) else "未配置"

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           📚 ReadLater API Server v1.1.0                      ║
╠══════════════════════════════════════════════════════════════╣
║  服务地址: http://{host}:{port}
║  API文档: http://{host}:{port}/
║  Notion:  {notion_status}
║
║  快速开始:
║  - 添加链接: POST /api/articles {{"url": "..."}}
║  - 获取摘要: POST /api/summarize {{"url": "..."}}
║  - 未读列表: GET /api/articles/unread
║
║  Notion 接口:
║  - 添加到Notion: POST /api/notion/articles {{"url": "..."}}
║  - Notion未读:   GET /api/notion/articles/unread
╚══════════════════════════════════════════════════════════════╝
    """)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.shutdown()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='ReadLater API Server')
    parser.add_argument('-H', '--host', default='0.0.0.0', help='服务器地址')
    parser.add_argument('-p', '--port', type=int, default=8080, help='服务器端口')
    args = parser.parse_args()

    run_server(args.host, args.port)
