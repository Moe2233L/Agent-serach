from __future__ import annotations

import asyncio
import re
import time
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

_USER_AGENT = "ResearchAgent/1.0 (research assistant; +https://github.com)"
_MAX_CONTENT_SIZE = 50000
_REQUEST_TIMEOUT = 15
_REQUEST_DELAY = 1.0
_last_fetch_time = 0.0
_fetch_lock = asyncio.Lock()

_BLOCKED_DOMAINS: set[str] = set()

_RE_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_RE_MENU = re.compile(
    r"^(navigation|menu|navbar|sidebar|footer|header|breadcrumb)$", re.I
)

_ROBOTS_CACHE: dict[str, bool] = {}
_RESTRICTIVE_DOMAINS = {
    "medium.com", "twitter.com", "x.com", "facebook.com",
    "linkedin.com", "instagram.com", "reddit.com",
}

def _get_domain(url: str) -> str:
    return urlparse(url).hostname or ""

async def _check_robots(url: str) -> bool:
    domain = _get_domain(url)
    if not domain:
        return False
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
        _ROBOTS_CACHE[domain] = True
        return True

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

async def fetch_page_content(url: str) -> str | None:
    global _last_fetch_time

    if not url or not url.startswith("http"):
        return None

    domain = _get_domain(url)
    if domain in _BLOCKED_DOMAINS or domain in _RESTRICTIVE_DOMAINS:
        return None

    if _is_likely_binary(url):
        return None

    if not await _check_robots(url):
        return None

    async with _fetch_lock:
        now = time.monotonic()
        elapsed = now - _last_fetch_time
        if elapsed < _REQUEST_DELAY:
            await asyncio.sleep(_REQUEST_DELAY - elapsed)
        _last_fetch_time = time.monotonic()

    try:
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

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return None

            raw = response.text
            if len(raw) > _MAX_CONTENT_SIZE:
                raw = raw[:_MAX_CONTENT_SIZE]

            soup = BeautifulSoup(raw, "lxml")

            for tag in soup(["script", "style", "noscript", "iframe", "nav",
                             "footer", "header", "form", "aside", "svg",
                             "button", "input", "select", "textarea"]):
                tag.decompose()

            for tag in soup.find_all(True):
                if tag.name in ("div", "section", "article", "main") and tag.get("class"):
                    classes = [c for c in tag.get("class", []) if isinstance(c, str)]
                    if any(_RE_MENU.match(c) for c in classes):
                        tag.decompose()

            for tag in soup.find_all(["div", "section", "article", "main", "p", "li"]):
                text_len = len(tag.get_text(strip=True))
                if text_len < 15:
                    tag.decompose()

            main = (
                soup.find("article")
                or soup.find("main")
                or soup.find(class_=re.compile(r"content|article|post|entry|main", re.I))
            )

            root = main or soup

            text = root.get_text(separator="\n", strip=True)
            lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 20]
            text = "\n".join(lines)

            text = _RE_EMAIL.sub("[email]", text)

            if len(text) < 50:
                return None

            return text

    except Exception:
        return None
