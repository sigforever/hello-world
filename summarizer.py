"""
网页内容提取与智能总结模块
"""

import re
import json
from typing import Tuple, Optional
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

from config import Config


class ContentExtractor:
    """网页内容提取器"""

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """验证URL是否有效"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    @staticmethod
    def fetch_page(url: str, timeout: int = 10) -> Tuple[str, int]:
        """获取网页内容"""
        try:
            response = requests.get(
                url,
                headers=ContentExtractor.HEADERS,
                timeout=timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text, response.status_code
        except requests.RequestException as e:
            raise Exception(f"获取网页失败: {str(e)}")

    @staticmethod
    def extract_content(html: str, url: str) -> Tuple[str, str]:
        """从HTML中提取标题和正文"""
        soup = BeautifulSoup(html, 'html.parser')

        # 移除不需要的标签
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
            tag.decompose()

        # 提取标题
        title = ""
        if soup.title:
            title = soup.title.string or ""
        if not title:
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content', '')

        # 清理标题
        title = re.sub(r'\s+', ' ', title).strip()

        # 提取正文 - 尝试多种策略
        content = ""

        # 策略1: 尝试找 article 标签
        article = soup.find('article')
        if article:
            content = article.get_text(separator='\n', strip=True)

        # 策略2: 尝试找 main 标签
        if not content or len(content) < 200:
            main = soup.find('main')
            if main:
                content = main.get_text(separator='\n', strip=True)

        # 策略3: 尝试找特定class的div
        if not content or len(content) < 200:
            for class_name in ['content', 'article', 'post', 'entry', 'main-content', 'post-content']:
                div = soup.find('div', class_=re.compile(class_name, re.I))
                if div:
                    text = div.get_text(separator='\n', strip=True)
                    if len(text) > len(content):
                        content = text

        # 策略4: 获取body全部内容
        if not content or len(content) < 200:
            body = soup.find('body')
            if body:
                content = body.get_text(separator='\n', strip=True)

        # 清理正文
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r' {2,}', ' ', content)

        # 限制内容长度（为了总结）
        if len(content) > 10000:
            content = content[:10000] + "..."

        return title, content


class Summarizer:
    """智能总结器 - 支持多种AI后端"""

    def __init__(self, config: Config = None):
        self.config = config or Config()

    def summarize_with_openai(self, content: str, title: str) -> str:
        """使用 OpenAI API 生成摘要"""
        import openai

        openai.api_key = self.config.OPENAI_API_KEY
        if self.config.OPENAI_BASE_URL:
            openai.api_base = self.config.OPENAI_BASE_URL

        prompt = f"""请为以下文章生成一个简洁的中文摘要（100-200字），包含核心观点和关键信息：

标题：{title}

内容：
{content[:5000]}

摘要："""

        try:
            response = openai.ChatCompletion.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个专业的文章摘要助手，擅长提炼文章的核心内容。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"AI摘要生成失败: {str(e)}"

    def summarize_with_anthropic(self, content: str, title: str) -> str:
        """使用 Anthropic Claude API 生成摘要"""
        import anthropic

        client = anthropic.Anthropic(api_key=self.config.ANTHROPIC_API_KEY)

        prompt = f"""请为以下文章生成一个简洁的中文摘要（100-200字），包含核心观点和关键信息：

标题：{title}

内容：
{content[:5000]}

摘要："""

        try:
            response = client.messages.create(
                model=self.config.ANTHROPIC_MODEL,
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text.strip()
        except Exception as e:
            return f"AI摘要生成失败: {str(e)}"

    def summarize_local(self, content: str, title: str) -> str:
        """本地简单摘要（不依赖AI API）"""
        # 简单的提取策略：取前几段
        paragraphs = [p.strip() for p in content.split('\n') if len(p.strip()) > 50]

        if not paragraphs:
            return "无法生成摘要：内容过短"

        # 取前3段作为摘要
        summary_parts = paragraphs[:3]
        summary = '\n'.join(summary_parts)

        # 限制长度
        if len(summary) > 500:
            summary = summary[:500] + "..."

        return f"【自动提取】\n{summary}"

    def summarize(self, content: str, title: str) -> str:
        """生成摘要 - 根据配置选择后端"""
        if not content or len(content) < 100:
            return "内容过短，无法生成摘要"

        backend = self.config.SUMMARIZER_BACKEND

        if backend == "openai" and self.config.OPENAI_API_KEY:
            return self.summarize_with_openai(content, title)
        elif backend == "anthropic" and self.config.ANTHROPIC_API_KEY:
            return self.summarize_with_anthropic(content, title)
        else:
            # 默认使用本地摘要
            return self.summarize_local(content, title)


def process_url(url: str, config: Config = None) -> Tuple[str, str, str]:
    """
    处理URL，提取内容并生成摘要

    返回: (title, content, summary)
    """
    extractor = ContentExtractor()
    summarizer = Summarizer(config)

    # 验证URL
    if not extractor.is_valid_url(url):
        raise ValueError(f"无效的URL: {url}")

    # 获取网页
    html, _ = extractor.fetch_page(url)

    # 提取内容
    title, content = extractor.extract_content(html, url)

    if not title:
        title = url

    # 生成摘要
    summary = summarizer.summarize(content, title)

    return title, content, summary
