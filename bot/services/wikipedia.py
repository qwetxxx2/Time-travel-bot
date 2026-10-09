import logging
import re
from urllib.parse import quote

import httpx

from bot.config import config
from bot.utils.cache import SimpleTTLCache
from bot.utils.retry import http_retry

logger = logging.getLogger(__name__)
cache = SimpleTTLCache(maxsize=128, ttl=config.CACHE_TTL)
_client = httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "TimeTravelBot/1.0 (educational)"})


@http_retry
async def _get_json(url: str, params: dict | None = None) -> dict:
    resp = await _client.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


async def get_summary(title: str) -> dict | None:
    """Краткая выжимка статьи. None при недоступности сервиса (graceful degradation)."""

    async def _fetch() -> dict | None:
        try:
            url = f"https://{config.WIKI_LANG}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
            data = await _get_json(url)
            return data if data.get("type") == "standard" else None
        except Exception as exc:
            logger.warning("Wikipedia summary error (%s): %s", title, exc)
            return None

    return await cache.get_or_set(f"wiki:summary:{title}", _fetch)


async def search(query: str, limit: int = 3) -> list[dict]:
    """Поиск статей [{'title', 'snippet'}] с очисткой HTML-тегов."""

    async def _fetch() -> list[dict]:
        try:
            data = await _get_json(
                f"https://{config.WIKI_LANG}.wikipedia.org/w/api.php",
                params={"action": "query", "format": "json", "list": "search", "srsearch": query, "srlimit": limit},
            )
            return [
                {"title": i["title"], "snippet": re.sub(r"<[^>]+>", "", i.get("snippet", ""))}
                for i in data.get("query", {}).get("search", [])
            ]
        except Exception as exc:
            logger.warning("Wikipedia search error (%s): %s", query, exc)
            return []

    return await cache.get_or_set(f"wiki:search:{query}", _fetch)