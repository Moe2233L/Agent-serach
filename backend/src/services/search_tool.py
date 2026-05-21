from __future__ import annotations

from backend.src.config import settings


async def search_web(query: str) -> list[dict]:
    """使用搜索引擎搜索指定关键词，返回结构化搜索结果列表。"""
    try:
        from ddgs import DDGS

        max_results = settings.search_max_results

        def _search():
            with DDGS(proxy=settings.search_proxy) as ddgs:
                return list(ddgs.text(query=query, max_results=max_results))

        import asyncio
        results = await asyncio.get_running_loop().run_in_executor(None, _search)

        if not results:
            return []

        items: list[dict] = []
        for r in results:
            title = r.get("title", "").strip()
            href = r.get("href", r.get("link", "")).strip()
            body = r.get("body", r.get("snippet", "")).strip()
            if title or body:
                items.append({"title": title, "url": href, "body": body})

        return items

    except Exception as e:
        raise RuntimeError(f"搜索出错: {e}")
