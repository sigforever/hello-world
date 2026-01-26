#!/usr/bin/env python3
"""
ReadLater - 稍后阅读应用
一个帮助你保存、总结和管理待阅读链接的命令行工具
"""

import sys
import argparse
from datetime import datetime
from typing import Optional

from models import Article, ReadStatus, Priority
from storage import Storage
from summarizer import process_url, ContentExtractor
from reminder import ReminderService, ConsoleNotifier, DesktopNotifier, WebhookNotifier, create_cron_script
from config import Config


class ReadLaterApp:
    """稍后阅读应用主类"""

    def __init__(self):
        self.config = Config()
        self.storage = Storage(self.config.get_db_path())
        self.reminder_service = ReminderService(self.storage, self.config)

    def add_url(self, url: str, priority: int = 2, tags: str = "") -> bool:
        """添加新链接"""
        # 检查是否已存在
        existing = self.storage.get_article_by_url(url)
        if existing:
            print(f"⚠️  该链接已存在: [{existing.id}] {existing.title}")
            return False

        print(f"🔄 正在处理链接: {url}")

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

            print(f"\n✅ 已添加到稍后阅读列表!")
            print(f"   ID: {article_id}")
            print(f"   标题: {title}")
            print(f"   优先级: {'🔴高' if priority == 3 else '🟡中' if priority == 2 else '🔵低'}")
            if tags:
                print(f"   标签: {tags}")
            print(f"\n📝 摘要:")
            print(f"   {summary[:200]}..." if len(summary) > 200 else f"   {summary}")
            print()

            return True

        except Exception as e:
            print(f"❌ 添加失败: {str(e)}")
            return False

    def list_articles(self, status: str = None, limit: int = 20):
        """列出文章"""
        status_filter = None
        if status:
            try:
                status_filter = ReadStatus(status)
            except ValueError:
                print(f"⚠️  无效的状态: {status}")
                print(f"   可用状态: unread, reading, finished, archived")
                return

        articles = self.storage.get_all_articles(status=status_filter, limit=limit)

        if not articles:
            print("📭 没有找到文章")
            return

        print(f"\n📚 文章列表 ({len(articles)} 篇)")
        print("=" * 70)

        for article in articles:
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

            print(f"\n{status_emoji[article.status]} {priority_emoji[article.priority]} [{article.id}] {article.title[:55]}")
            print(f"   🔗 {article.url[:60]}...")

            days_old = (datetime.now() - article.created_at).days
            print(f"   ⏰ {days_old}天前添加", end="")

            if article.tags:
                print(f" | 🏷️  {', '.join(article.tags)}", end="")
            print()

        print("\n" + "=" * 70)

    def show_article(self, article_id: int):
        """显示文章详情"""
        article = self.storage.get_article(article_id)

        if not article:
            print(f"❌ 找不到文章 ID: {article_id}")
            return

        print(f"\n{'=' * 70}")
        print(f"📄 {article.title}")
        print(f"{'=' * 70}")
        print(f"\n🔗 链接: {article.url}")
        print(f"📊 状态: {article.status.value}")
        print(f"⭐ 优先级: {article.priority.name}")
        print(f"⏰ 添加时间: {article.created_at.strftime('%Y-%m-%d %H:%M')}")

        if article.tags:
            print(f"🏷️  标签: {', '.join(article.tags)}")

        if article.read_at:
            print(f"✅ 阅读时间: {article.read_at.strftime('%Y-%m-%d %H:%M')}")

        print(f"\n{'─' * 70}")
        print("📝 摘要:")
        print(f"{'─' * 70}")
        print(article.summary or "无摘要")

        if article.notes:
            print(f"\n{'─' * 70}")
            print("📓 笔记:")
            print(f"{'─' * 70}")
            print(article.notes)

        print(f"\n{'=' * 70}\n")

    def mark_status(self, article_id: int, status: str) -> bool:
        """标记文章状态"""
        article = self.storage.get_article(article_id)

        if not article:
            print(f"❌ 找不到文章 ID: {article_id}")
            return False

        try:
            new_status = ReadStatus(status)
        except ValueError:
            print(f"⚠️  无效的状态: {status}")
            return False

        article.status = new_status
        if new_status == ReadStatus.FINISHED:
            article.read_at = datetime.now()

        self.storage.update_article(article)
        print(f"✅ 已将 [{article_id}] 标记为 {status}")
        return True

    def delete_article(self, article_id: int) -> bool:
        """删除文章"""
        article = self.storage.get_article(article_id)

        if not article:
            print(f"❌ 找不到文章 ID: {article_id}")
            return False

        self.storage.delete_article(article_id)
        print(f"🗑️  已删除: [{article_id}] {article.title[:40]}")
        return True

    def search(self, keyword: str):
        """搜索文章"""
        articles = self.storage.search_articles(keyword)

        if not articles:
            print(f"🔍 没有找到包含 '{keyword}' 的文章")
            return

        print(f"\n🔍 搜索结果: '{keyword}' ({len(articles)} 篇)")
        print("=" * 70)

        for article in articles:
            print(f"\n📌 [{article.id}] {article.title[:55]}")
            print(f"   🔗 {article.url[:60]}")

        print("\n" + "=" * 70)

    def show_stats(self):
        """显示统计信息"""
        stats = self.storage.get_statistics()

        print(f"""
╔══════════════════════════════════════════════════════════╗
║                    📊 阅读统计                             ║
╠══════════════════════════════════════════════════════════╣
║  总文章数:        {stats['total']:<38} ║
║  ────────────────────────────────────────────────────── ║
║  📌 未读:         {stats.get('unread', 0):<38} ║
║  📖 阅读中:       {stats.get('reading', 0):<38} ║
║  ✅ 已完成:       {stats.get('finished', 0):<38} ║
║  📦 已归档:       {stats.get('archived', 0):<38} ║
║  ────────────────────────────────────────────────────── ║
║  本周添加:        {stats.get('added_this_week', 0):<38} ║
║  本周阅读:        {stats.get('read_this_week', 0):<38} ║
╚══════════════════════════════════════════════════════════╝
""")

    def trigger_reminder(self):
        """触发提醒"""
        count = self.reminder_service.check_and_remind()
        if count == 0:
            print("📭 暂无需要提醒的文章")

    def show_config(self):
        """显示配置"""
        print(self.config.show_config())

    def setup_reminder(self):
        """设置定时提醒"""
        print(create_cron_script(self.config))


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        prog='readlater',
        description='📚 ReadLater - 稍后阅读应用',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s add https://example.com/article
  %(prog)s add https://example.com/article -p 3 -t "tech,python"
  %(prog)s list
  %(prog)s list -s unread
  %(prog)s show 1
  %(prog)s read 1
  %(prog)s done 1
  %(prog)s search "python"
  %(prog)s remind
  %(prog)s stats
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # add 命令
    add_parser = subparsers.add_parser('add', help='添加新链接')
    add_parser.add_argument('url', help='要添加的链接')
    add_parser.add_argument('-p', '--priority', type=int, choices=[1, 2, 3],
                           default=2, help='优先级 (1=低, 2=中, 3=高)')
    add_parser.add_argument('-t', '--tags', default='', help='标签，逗号分隔')

    # list 命令
    list_parser = subparsers.add_parser('list', help='列出文章')
    list_parser.add_argument('-s', '--status', choices=['unread', 'reading', 'finished', 'archived'],
                            help='按状态筛选')
    list_parser.add_argument('-n', '--limit', type=int, default=20, help='显示数量')

    # show 命令
    show_parser = subparsers.add_parser('show', help='显示文章详情')
    show_parser.add_argument('id', type=int, help='文章ID')

    # read 命令 (标记为阅读中)
    read_parser = subparsers.add_parser('read', help='标记为阅读中')
    read_parser.add_argument('id', type=int, help='文章ID')

    # done 命令 (标记为已完成)
    done_parser = subparsers.add_parser('done', help='标记为已完成')
    done_parser.add_argument('id', type=int, help='文章ID')

    # archive 命令
    archive_parser = subparsers.add_parser('archive', help='归档文章')
    archive_parser.add_argument('id', type=int, help='文章ID')

    # delete 命令
    delete_parser = subparsers.add_parser('delete', help='删除文章')
    delete_parser.add_argument('id', type=int, help='文章ID')

    # search 命令
    search_parser = subparsers.add_parser('search', help='搜索文章')
    search_parser.add_argument('keyword', help='搜索关键词')

    # remind 命令
    subparsers.add_parser('remind', help='触发阅读提醒')

    # stats 命令
    subparsers.add_parser('stats', help='显示统计信息')

    # config 命令
    subparsers.add_parser('config', help='显示当前配置')

    # setup-reminder 命令
    subparsers.add_parser('setup-reminder', help='生成定时提醒脚本')

    args = parser.parse_args()

    # 如果没有命令，显示帮助
    if not args.command:
        parser.print_help()
        return

    app = ReadLaterApp()

    # 执行命令
    if args.command == 'add':
        app.add_url(args.url, args.priority, args.tags)

    elif args.command == 'list':
        app.list_articles(args.status, args.limit)

    elif args.command == 'show':
        app.show_article(args.id)

    elif args.command == 'read':
        app.mark_status(args.id, 'reading')

    elif args.command == 'done':
        app.mark_status(args.id, 'finished')

    elif args.command == 'archive':
        app.mark_status(args.id, 'archived')

    elif args.command == 'delete':
        app.delete_article(args.id)

    elif args.command == 'search':
        app.search(args.keyword)

    elif args.command == 'remind':
        app.trigger_reminder()

    elif args.command == 'stats':
        app.show_stats()

    elif args.command == 'config':
        app.show_config()

    elif args.command == 'setup-reminder':
        app.setup_reminder()


if __name__ == '__main__':
    main()
