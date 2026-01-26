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

    # 应用配置
    APP_NAME = "ReadLater"
    VERSION = "1.0.0"

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
║ Webhook:        {'已配置' if cls.WEBHOOK_URL else '未配置':<40} ║
╚══════════════════════════════════════════════════════════╝

环境变量设置示例:
  export READLATER_SUMMARIZER=openai
  export OPENAI_API_KEY=sk-xxx
  export READLATER_REMINDER_HOURS=12
"""


# 创建全局配置实例
config = Config()
