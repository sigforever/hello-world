"""
配置管理模块
"""

import os
from pathlib import Path


class Config:
    """应用配置"""

    # 数据库配置
    DB_PATH = os.environ.get('READLATER_DB_PATH', 'readlater.db')

    # AI 摘要配置
    SUMMARIZER_BACKEND = os.environ.get('READLATER_SUMMARIZER', 'local')  # local, openai, anthropic

    # OpenAI 配置
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', '')  # 可选，用于自定义端点
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')

    # Anthropic Claude 配置
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
    ANTHROPIC_MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-3-haiku-20240307')

    # 提醒配置
    REMINDER_INTERVAL_HOURS = int(os.environ.get('READLATER_REMINDER_HOURS', '24'))
    MAX_REMINDER_ARTICLES = int(os.environ.get('READLATER_MAX_REMINDERS', '5'))

    # Webhook 配置（可选）
    WEBHOOK_URL = os.environ.get('READLATER_WEBHOOK_URL', '')

    # Pushover 推送配置
    PUSHOVER_USER_KEY = os.environ.get('READLATER_PUSHOVER_USER', '')
    PUSHOVER_API_TOKEN = os.environ.get('READLATER_PUSHOVER_TOKEN', '')

    # Bark 推送配置（iOS国内推荐）
    BARK_URL = os.environ.get('READLATER_BARK_URL', '')

    # Telegram 配置
    TELEGRAM_BOT_TOKEN = os.environ.get('READLATER_TELEGRAM_BOT', '')
    TELEGRAM_CHAT_ID = os.environ.get('READLATER_TELEGRAM_CHAT', '')

    # API 服务器配置
    API_HOST = os.environ.get('READLATER_API_HOST', '0.0.0.0')
    API_PORT = int(os.environ.get('READLATER_API_PORT', '8080'))
    API_KEY = os.environ.get('READLATER_API_KEY', '')  # API密钥，留空则不验证

    # Notion 配置
    NOTION_TOKEN = os.environ.get('NOTION_TOKEN', '')  # Notion Integration Token
    NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID', '')  # 数据库ID
    NOTION_SYNC_ENABLED = os.environ.get('NOTION_SYNC_ENABLED', 'false').lower() == 'true'

    # 应用配置
    APP_NAME = "ReadLater"
    VERSION = "1.1.0"

    @classmethod
    def get_config_path(cls) -> Path:
        """获取配置文件目录"""
        config_dir = Path.home() / '.readlater'
        config_dir.mkdir(exist_ok=True)
        return config_dir

    @classmethod
    def get_db_path(cls) -> str:
        """获取数据库文件完整路径"""
        if os.path.isabs(cls.DB_PATH):
            return cls.DB_PATH
        return str(cls.get_config_path() / cls.DB_PATH)

    @classmethod
    def show_config(cls) -> str:
        """显示当前配置"""
        return f"""
╔══════════════════════════════════════════════════════════╗
║                  ReadLater 配置信息                        ║
╠══════════════════════════════════════════════════════════╣
║ 数据库路径:     {cls.get_db_path():<40} ║
║ 摘要后端:       {cls.SUMMARIZER_BACKEND:<40} ║
║ 提醒间隔:       {cls.REMINDER_INTERVAL_HOURS} 小时{' ' * 33}║
║ 每次提醒数量:   {cls.MAX_REMINDER_ARTICLES} 篇{' ' * 35}║
╠══════════════════════════════════════════════════════════╣
║ OpenAI 配置:                                              ║
║   API Key:      {'已设置' if cls.OPENAI_API_KEY else '未设置':<40} ║
║   模型:         {cls.OPENAI_MODEL:<40} ║
╠══════════════════════════════════════════════════════════╣
║ Anthropic 配置:                                           ║
║   API Key:      {'已设置' if cls.ANTHROPIC_API_KEY else '未设置':<40} ║
║   模型:         {cls.ANTHROPIC_MODEL:<40} ║
╠══════════════════════════════════════════════════════════╣
║ 推送通知:                                                  ║
║   Webhook:      {'已配置' if cls.WEBHOOK_URL else '未配置':<40} ║
║   Pushover:     {'已配置' if cls.PUSHOVER_USER_KEY else '未配置':<40} ║
║   Bark:         {'已配置' if cls.BARK_URL else '未配置':<40} ║
║   Telegram:     {'已配置' if cls.TELEGRAM_BOT_TOKEN else '未配置':<40} ║
╠══════════════════════════════════════════════════════════╣
║ API服务器:                                                 ║
║   地址:         {cls.API_HOST}:{cls.API_PORT:<33} ║
║   API密钥:      {'已设置' if cls.API_KEY else '未设置(开放访问)':<40} ║
╠══════════════════════════════════════════════════════════╣
║ Notion 配置:                                              ║
║   Token:        {'已设置' if cls.NOTION_TOKEN else '未设置':<40} ║
║   数据库ID:     {'已设置' if cls.NOTION_DATABASE_ID else '未设置':<40} ║
║   同步状态:     {'已启用' if cls.NOTION_SYNC_ENABLED else '未启用':<40} ║
╚══════════════════════════════════════════════════════════╝

环境变量设置示例:
  # AI摘要
  export READLATER_SUMMARIZER=anthropic
  export ANTHROPIC_API_KEY=sk-ant-xxx

  # 推送通知（选择一种）
  export READLATER_BARK_URL=https://api.day.app/your_key
  export READLATER_PUSHOVER_USER=xxx
  export READLATER_PUSHOVER_TOKEN=xxx

  # Notion 集成
  export NOTION_TOKEN=secret_xxx
  export NOTION_DATABASE_ID=xxx
  export NOTION_SYNC_ENABLED=true

  # API服务器
  export READLATER_API_KEY=your_secret_key
"""


# 创建全局配置实例
config = Config()
