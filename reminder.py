"""
定期提醒模块 - 支持多种提醒方式
"""

import os
import sys
import time
import signal
import threading
from datetime import datetime, timedelta
from typing import List, Optional, Callable
import json

from models import Article, ReadStatus
from storage import Storage
from config import Config


class ReminderNotifier:
    """提醒通知器基类"""

    def notify(self, articles: List[Article]) -> bool:
        """发送提醒通知"""
        raise NotImplementedError


class ConsoleNotifier(ReminderNotifier):
    """控制台提醒"""

    def notify(self, articles: List[Article]) -> bool:
        print("\n" + "=" * 60)
        print(f"📚 阅读提醒 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 60)
        print(f"\n您有 {len(articles)} 篇文章等待阅读：\n")

        for i, article in enumerate(articles, 1):
            days_old = (datetime.now() - article.created_at).days
            print(f"{i}. [{article.id}] {article.title[:50]}")
            print(f"   📎 {article.url[:60]}...")
            print(f"   ⏰ 添加于 {days_old} 天前 | 已提醒 {article.reminder_count} 次")
            if article.summary:
                summary_preview = article.summary[:100].replace('\n', ' ')
                print(f"   📝 {summary_preview}...")
            print()

        print("=" * 60)
        print("💡 提示: 使用 'readlater read <id>' 开始阅读")
        print("=" * 60 + "\n")
        return True


class DesktopNotifier(ReminderNotifier):
    """桌面通知（跨平台）"""

    def notify(self, articles: List[Article]) -> bool:
        try:
            # 尝试使用 plyer 库发送桌面通知
            from plyer import notification

            title = f"📚 阅读提醒 - {len(articles)} 篇待读"
            message = "\n".join([
                f"• {a.title[:30]}..." for a in articles[:3]
            ])
            if len(articles) > 3:
                message += f"\n...还有 {len(articles) - 3} 篇"

            notification.notify(
                title=title,
                message=message,
                app_name="ReadLater",
                timeout=10
            )
            return True
        except ImportError:
            # plyer 未安装，尝试系统命令
            return self._fallback_notify(articles)
        except Exception as e:
            print(f"桌面通知失败: {e}")
            return False

    def _fallback_notify(self, articles: List[Article]) -> bool:
        """备用通知方法"""
        title = f"阅读提醒 - {len(articles)} 篇待读"
        message = f"您有 {len(articles)} 篇文章等待阅读"

        system = sys.platform
        try:
            if system == "darwin":  # macOS
                os.system(f'''osascript -e 'display notification "{message}" with title "{title}"' ''')
            elif system == "linux":
                os.system(f'notify-send "{title}" "{message}"')
            elif system == "win32":
                # Windows 使用 PowerShell
                os.system(f'powershell -Command "& {{Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show(\'{message}\', \'{title}\')}}"')
            return True
        except:
            return False


class WebhookNotifier(ReminderNotifier):
    """Webhook 通知（可对接钉钉、企业微信、Slack等）"""

    def __init__(self, webhook_url: str, config: Config = None):
        self.webhook_url = webhook_url
        self.config = config or Config()

    def notify(self, articles: List[Article]) -> bool:
        import requests

        # 构建消息
        article_list = "\n".join([
            f"• [{a.id}] {a.title[:40]}" for a in articles[:5]
        ])

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": "📚 阅读提醒",
                "text": f"""## 📚 阅读提醒

您有 **{len(articles)}** 篇文章等待阅读：

{article_list}

---
*{datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
            }
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Webhook通知失败: {e}")
            return False


class ReminderService:
    """提醒服务"""

    def __init__(self, storage: Storage, config: Config = None):
        self.storage = storage
        self.config = config or Config()
        self.notifiers: List[ReminderNotifier] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # 默认添加控制台通知
        self.add_notifier(ConsoleNotifier())

    def add_notifier(self, notifier: ReminderNotifier):
        """添加通知器"""
        self.notifiers.append(notifier)

    def check_and_remind(self) -> int:
        """检查并发送提醒，返回提醒的文章数量"""
        # 获取需要提醒的文章
        articles = self.storage.get_articles_for_reminder(
            hours_since_last_reminder=self.config.REMINDER_INTERVAL_HOURS
        )

        if not articles:
            return 0

        # 限制每次提醒的数量
        articles = articles[:self.config.MAX_REMINDER_ARTICLES]

        # 发送通知
        for notifier in self.notifiers:
            try:
                notifier.notify(articles)
            except Exception as e:
                print(f"通知发送失败: {e}")

        # 更新提醒状态
        for article in articles:
            self.storage.update_reminder(article.id)

        return len(articles)

    def start_daemon(self, interval_seconds: int = None):
        """启动后台提醒守护进程"""
        if self._running:
            print("提醒服务已在运行")
            return

        interval = interval_seconds or (self.config.REMINDER_INTERVAL_HOURS * 3600)
        self._running = True

        def run():
            print(f"📢 提醒服务已启动，间隔: {interval}秒")
            while self._running:
                try:
                    count = self.check_and_remind()
                    if count > 0:
                        print(f"已发送 {count} 条提醒")
                except Exception as e:
                    print(f"提醒服务错误: {e}")

                # 等待下一次检查
                for _ in range(interval):
                    if not self._running:
                        break
                    time.sleep(1)

            print("📢 提醒服务已停止")

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop_daemon(self):
        """停止后台提醒"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def get_pending_reminders(self) -> List[Article]:
        """获取待提醒的文章列表"""
        return self.storage.get_articles_for_reminder(
            hours_since_last_reminder=self.config.REMINDER_INTERVAL_HOURS
        )


def create_cron_script(config: Config = None) -> str:
    """生成 cron 定时任务脚本"""
    config = config or Config()
    app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'app.py'))

    cron_line = f"0 */{config.REMINDER_INTERVAL_HOURS} * * * cd {os.path.dirname(app_path)} && python {app_path} remind"

    script = f"""#!/bin/bash
# ReadLater 定时提醒脚本
# 将以下行添加到 crontab (使用 crontab -e 编辑):

{cron_line}

# 或者运行以下命令自动添加:
# (crontab -l 2>/dev/null; echo "{cron_line}") | crontab -
"""
    return script


def setup_systemd_timer(config: Config = None) -> str:
    """生成 systemd timer 配置"""
    config = config or Config()
    app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'app.py'))
    work_dir = os.path.dirname(app_path)

    service_content = f"""[Unit]
Description=ReadLater 阅读提醒服务

[Service]
Type=oneshot
WorkingDirectory={work_dir}
ExecStart=/usr/bin/python3 {app_path} remind
"""

    timer_content = f"""[Unit]
Description=ReadLater 定时提醒

[Timer]
OnCalendar=*:0/{config.REMINDER_INTERVAL_HOURS * 60}
Persistent=true

[Install]
WantedBy=timers.target
"""

    return f"""# ReadLater Systemd Timer 配置
# 保存为 ~/.config/systemd/user/readlater.service
{service_content}
---
# 保存为 ~/.config/systemd/user/readlater.timer
{timer_content}
---
# 启用命令:
# systemctl --user enable readlater.timer
# systemctl --user start readlater.timer
"""
