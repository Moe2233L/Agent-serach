from __future__ import annotations

import asyncio
import re
import time
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


# HTTP 请求 User-Agent 标识
_USER_AGENT = "ResearchAgent/1.0 (research assistant; +https://github.com)"
# 最大抓取内容大小（字节）
_MAX_CONTENT_SIZE = 50000
# 单次请求超时（秒）
_REQUEST_TIMEOUT = 15
# 每次请求之间的最小间隔（秒），避免被目标网站限流
_REQUEST_DELAY = 1.0
# 上次请求时间戳，用于速率控制
_last_fetch_time = 0.0
# 全局限流锁
_fetch_lock = asyncio.Lock()

# 邮箱正则
_RE_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# 导航/菜单类名正则
_RE_MENU = re.compile(
    r"^(navigation|menu|navbar|sidebar|footer|header|breadcrumb)$", re.I
)

# robots.txt 检查缓存
_ROBOTS_CACHE: dict[str, bool] = {}
# 限制性域名列表（拒绝抓取这些网站的内容）
_RESTRICTIVE_DOMAINS = {
    "medium.com", "twitter.com", "x.com", "facebook.com",
    "linkedin.com", "instagram.com", "reddit.com",
}


# 提取 URL 的域名部分
def _get_domain(url: str) -> str:
    return urlparse(url).hostname or ""


# 检查目标域的 robots.txt 是否允许爬取
# 若明确禁止（Disallow: /），返回 False
async def _check_robots(url: str) -> bool:
    domain = _get_domain(url)
    if not domain:
        return False
    # 命中缓存直接返回
    if domain in _ROBOTS_CACHE:
        return _ROBOTS_CACHE[domain]
    robots_url = f"https://{domain}/robots.txt"
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            resp = await client.get(robots_url, headers={"User-Agent": _USER_AGENT})
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    line = line.strip().lower()
                    if line == "disallow: /":
                        _ROBOTS_CACHE[domain] = False
                        return False
        _ROBOTS_CACHE[domain] = True
        return True
    except Exception:
        # 无法访问 robots.txt 默认允许
        _ROBOTS_CACHE[domain] = True
        return True


# 判断 URL 是否为二进制文件（不抓取）
def _is_likely_binary(url: str) -> bool:
    ext = urlparse(url).path.lower()
    binary_exts = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
                   ".zip", ".rar", ".tar", ".gz", ".mp3", ".mp4", ".avi",
                   ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico"}
    for e in binary_exts:
        if ext.endswith(e):
            return True
    ext_no_query = ext.split(";")[0]
    for e in binary_exts:
        if ext_no_query.endswith(e):
            return True
    return False


# 抓取指定 URL 的网页全文内容（HTML 净化 + 文本提取）
async def fetch_page_content(url: str) -> str | None:
    global _last_fetch_time

    # 校验 URL 格式
    if not url or not url.startswith("http"):
        return None

    # 跳过限制性域名
    domain = _get_domain(url)
    if domain in _RESTRICTIVE_DOMAINS:
        return None

    # 跳过二进制文件
    if _is_likely_binary(url):
        return None

    # 遵守 robots.txt
    if not await _check_robots(url):
        return None

    # 速率控制：确保每次请求间隔至少 _REQUEST_DELAY 秒
    async with _fetch_lock:
        now = time.monotonic()
        elapsed = now - _last_fetch_time
        if elapsed < _REQUEST_DELAY:
            await asyncio.sleep(_REQUEST_DELAY - elapsed)
        _last_fetch_time = time.monotonic()

    try:
        # 发送 HTTP 请求获取页面
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": _USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                },
            )
            response.raise_for_status()

            # 仅处理 HTML 内容
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return None

            # 截断超大内容
            raw = response.text
            if len(raw) > _MAX_CONTENT_SIZE:
                raw = raw[:_MAX_CONTENT_SIZE]

            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(raw, "lxml")

            # 移除无意义的标签（脚本、样式、导航、页脚等）
            for tag in soup(["script", "style", "noscript", "iframe", "nav",
                             "footer", "header", "form", "aside", "svg",
                             "button", "input", "select", "textarea"]):
                tag.decompose()

            # 移除包含导航/菜单类名的容器
            for tag in soup.find_all(True):
                if tag.name in ("div", "section", "article", "main") and tag.get("class"):
                    classes = [c for c in tag.get("class", []) if isinstance(c, str)]
                    if any(_RE_MENU.match(c) for c in classes):
                        tag.decompose()

            # 移除过短的内容块（小于 15 字符）
            for tag in soup.find_all(["div", "section", "article", "main", "p", "li"]):
                text_len = len(tag.get_text(strip=True))
                if text_len < 15:
                    tag.decompose()

            # 优先使用 article / main 等语义标签
            main = (
                soup.find("article")
                or soup.find("main")
                or soup.find(class_=re.compile(r"content|article|post|entry|main", re.I))
            )

            root = main or soup

            # 提取纯文本，过滤过短行（< 20 字符）
            text = root.get_text(separator="\n", strip=True)
            lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 20]
            text = "\n".join(lines)

            # 脱敏邮箱
            text = _RE_EMAIL.sub("[email]", text)

            # 内容过短则丢弃
            if len(text) < 50:
                return None

            return text

    except Exception:
        return None
