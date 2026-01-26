"""
数据模型 - 稍后阅读应用
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class ReadStatus(Enum):
    """阅读状态"""
    UNREAD = "unread"           # 未读
    READING = "reading"         # 阅读中
    FINISHED = "finished"       # 已完成
    ARCHIVED = "archived"       # 已归档


class Priority(Enum):
    """优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class Article:
    """文章/链接模型"""
    id: Optional[int] = None
    url: str = ""
    title: str = ""
    summary: str = ""                           # AI生成的摘要
    content: str = ""                           # 提取的正文内容
    status: ReadStatus = ReadStatus.UNREAD
    priority: Priority = Priority.MEDIUM
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    read_at: Optional[datetime] = None          # 阅读完成时间
    reminder_count: int = 0                     # 已提醒次数
    last_reminded_at: Optional[datetime] = None # 上次提醒时间
    notes: str = ""                             # 用户笔记

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'summary': self.summary,
            'content': self.content,
            'status': self.status.value,
            'priority': self.priority.value,
            'tags': ','.join(self.tags) if self.tags else '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'reminder_count': self.reminder_count,
            'last_reminded_at': self.last_reminded_at.isoformat() if self.last_reminded_at else None,
            'notes': self.notes
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Article':
        """从字典创建实例"""
        return cls(
            id=data.get('id'),
            url=data.get('url', ''),
            title=data.get('title', ''),
            summary=data.get('summary', ''),
            content=data.get('content', ''),
            status=ReadStatus(data.get('status', 'unread')),
            priority=Priority(data.get('priority', 2)),
            tags=data.get('tags', '').split(',') if data.get('tags') else [],
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now(),
            read_at=datetime.fromisoformat(data['read_at']) if data.get('read_at') else None,
            reminder_count=data.get('reminder_count', 0),
            last_reminded_at=datetime.fromisoformat(data['last_reminded_at']) if data.get('last_reminded_at') else None,
            notes=data.get('notes', '')
        )

    def __str__(self) -> str:
        status_emoji = {
            ReadStatus.UNREAD: "📌",
            ReadStatus.READING: "📖",
            ReadStatus.FINISHED: "✅",
            ReadStatus.ARCHIVED: "📦"
        }
        priority_emoji = {
            Priority.LOW: "🔵",
            Priority.MEDIUM: "🟡",
            Priority.HIGH: "🔴"
        }
        return f"{status_emoji[self.status]} {priority_emoji[self.priority]} [{self.id}] {self.title[:50]}"
