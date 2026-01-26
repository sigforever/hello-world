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


class ReadLaterAPI:
    """API业务逻辑层"""

    def __init__(self):
        self.config = Config()
        self.storage = Storage(self.config.get_db_path())
        self.reminder_service = ReminderService(self.storage, self.config)

    def add_url(self, url: str, priority: int = 2, tags: str = "") -> dict:
        """添加新链接"""
        # 检查是否已存在
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

            # 保存到数据库
            article_id = self.storage.add_article(article)
            article.id = article_id

            return {
                "success": True,
                "message": "已添加到稍后阅读列表",
                "article": self._article_to_dict(article)
            }

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
            result = {"success": True, "status": "healthy", "version": "1.0.0"}

        elif path == '/':
            result = {
                "name": "ReadLater API",
                "version": "1.0.0",
                "endpoints": {
                    "POST /api/articles": "添加新链接",
                    "POST /api/summarize": "仅获取链接摘要（不保存）",
                    "GET /api/articles": "获取文章列表",
                    "GET /api/articles/unread": "获取未读文章摘要",
                    "GET /api/articles/<id>": "获取文章详情",
                    "POST /api/articles/<id>/status": "更新文章状态",
                    "DELETE /api/articles/<id>": "删除文章",
                    "GET /api/search?q=keyword": "搜索文章",
                    "GET /api/stats": "获取统计信息"
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
                result = self.api.add_url(url, priority, tags)

        elif path == '/api/summarize':
            url = body.get('url')
            if not url:
                result = {"success": False, "error": "Missing URL"}
            else:
                result = self.api.summarize_url_only(url)

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
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           📚 ReadLater API Server                             ║
╠══════════════════════════════════════════════════════════════╣
║  服务地址: http://{host}:{port}
║  API文档: http://{host}:{port}/
║
║  快速开始:
║  - 添加链接: POST /api/articles {{"url": "..."}}
║  - 获取摘要: POST /api/summarize {{"url": "..."}}
║  - 未读列表: GET /api/articles/unread
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
