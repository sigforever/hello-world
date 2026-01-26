"""
数据存储层 - 使用 SQLite
"""

import sqlite3
import os
from typing import List, Optional
from datetime import datetime, timedelta
from contextlib import contextmanager

from models import Article, ReadStatus, Priority


class Storage:
    """SQLite 存储管理器"""

    def __init__(self, db_path: str = "readlater.db"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT,
                    summary TEXT,
                    content TEXT,
                    status TEXT DEFAULT 'unread',
                    priority INTEGER DEFAULT 2,
                    tags TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    read_at TEXT,
                    reminder_count INTEGER DEFAULT 0,
                    last_reminded_at TEXT,
                    notes TEXT
                )
            ''')

    def add_article(self, article: Article) -> int:
        """添加文章"""
        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO articles (url, title, summary, content, status, priority,
                                     tags, created_at, updated_at, read_at,
                                     reminder_count, last_reminded_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article.url,
                article.title,
                article.summary,
                article.content,
                article.status.value,
                article.priority.value,
                ','.join(article.tags) if article.tags else '',
                article.created_at.isoformat() if article.created_at else datetime.now().isoformat(),
                article.updated_at.isoformat() if article.updated_at else datetime.now().isoformat(),
                article.read_at.isoformat() if article.read_at else None,
                article.reminder_count,
                article.last_reminded_at.isoformat() if article.last_reminded_at else None,
                article.notes
            ))
            return cursor.lastrowid

    def get_article(self, article_id: int) -> Optional[Article]:
        """根据ID获取文章"""
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT * FROM articles WHERE id = ?', (article_id,))
            row = cursor.fetchone()
            if row:
                return Article.from_dict(dict(row))
            return None

    def get_article_by_url(self, url: str) -> Optional[Article]:
        """根据URL获取文章"""
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT * FROM articles WHERE url = ?', (url,))
            row = cursor.fetchone()
            if row:
                return Article.from_dict(dict(row))
            return None

    def get_all_articles(self, status: Optional[ReadStatus] = None,
                         limit: int = 100) -> List[Article]:
        """获取所有文章"""
        with self._get_connection() as conn:
            if status:
                cursor = conn.execute(
                    'SELECT * FROM articles WHERE status = ? ORDER BY priority DESC, created_at DESC LIMIT ?',
                    (status.value, limit)
                )
            else:
                cursor = conn.execute(
                    'SELECT * FROM articles ORDER BY priority DESC, created_at DESC LIMIT ?',
                    (limit,)
                )
            return [Article.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_unread_articles(self, limit: int = 100) -> List[Article]:
        """获取未读文章"""
        return self.get_all_articles(status=ReadStatus.UNREAD, limit=limit)

    def get_articles_for_reminder(self, hours_since_last_reminder: int = 24) -> List[Article]:
        """获取需要提醒的文章"""
        cutoff_time = (datetime.now() - timedelta(hours=hours_since_last_reminder)).isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM articles
                WHERE status IN ('unread', 'reading')
                AND (last_reminded_at IS NULL OR last_reminded_at < ?)
                ORDER BY priority DESC, created_at ASC
            ''', (cutoff_time,))
            return [Article.from_dict(dict(row)) for row in cursor.fetchall()]

    def update_article(self, article: Article) -> bool:
        """更新文章"""
        article.updated_at = datetime.now()
        with self._get_connection() as conn:
            cursor = conn.execute('''
                UPDATE articles SET
                    title = ?, summary = ?, content = ?, status = ?,
                    priority = ?, tags = ?, updated_at = ?, read_at = ?,
                    reminder_count = ?, last_reminded_at = ?, notes = ?
                WHERE id = ?
            ''', (
                article.title,
                article.summary,
                article.content,
                article.status.value,
                article.priority.value,
                ','.join(article.tags) if article.tags else '',
                article.updated_at.isoformat(),
                article.read_at.isoformat() if article.read_at else None,
                article.reminder_count,
                article.last_reminded_at.isoformat() if article.last_reminded_at else None,
                article.notes,
                article.id
            ))
            return cursor.rowcount > 0

    def update_reminder(self, article_id: int) -> bool:
        """更新提醒状态"""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute('''
                UPDATE articles SET
                    reminder_count = reminder_count + 1,
                    last_reminded_at = ?
                WHERE id = ?
            ''', (now, article_id))
            return cursor.rowcount > 0

    def mark_as_read(self, article_id: int) -> bool:
        """标记为已读"""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute('''
                UPDATE articles SET
                    status = ?, read_at = ?, updated_at = ?
                WHERE id = ?
            ''', (ReadStatus.FINISHED.value, now, now, article_id))
            return cursor.rowcount > 0

    def delete_article(self, article_id: int) -> bool:
        """删除文章"""
        with self._get_connection() as conn:
            cursor = conn.execute('DELETE FROM articles WHERE id = ?', (article_id,))
            return cursor.rowcount > 0

    def search_articles(self, keyword: str) -> List[Article]:
        """搜索文章"""
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM articles
                WHERE title LIKE ? OR summary LIKE ? OR content LIKE ? OR tags LIKE ?
                ORDER BY priority DESC, created_at DESC
            ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
            return [Article.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_statistics(self) -> dict:
        """获取统计信息"""
        with self._get_connection() as conn:
            stats = {}

            # 总数
            cursor = conn.execute('SELECT COUNT(*) FROM articles')
            stats['total'] = cursor.fetchone()[0]

            # 各状态数量
            for status in ReadStatus:
                cursor = conn.execute(
                    'SELECT COUNT(*) FROM articles WHERE status = ?',
                    (status.value,)
                )
                stats[status.value] = cursor.fetchone()[0]

            # 本周添加数量
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor = conn.execute(
                'SELECT COUNT(*) FROM articles WHERE created_at > ?',
                (week_ago,)
            )
            stats['added_this_week'] = cursor.fetchone()[0]

            # 本周阅读数量
            cursor = conn.execute(
                'SELECT COUNT(*) FROM articles WHERE read_at > ?',
                (week_ago,)
            )
            stats['read_this_week'] = cursor.fetchone()[0]

            return stats
