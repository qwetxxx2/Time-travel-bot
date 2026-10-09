import logging

import httpx

from bot.config import config
from bot.utils.cache import SimpleTTLCache
from bot.utils.retry import http_retry

logger = logging.getLogger(__name__)
cache = SimpleTTLCache(maxsize=128, ttl=6 * 3600)  # артефакты живём 6 часов
_client = httpx.AsyncClient(timeout=10.0)
BASE_URL = "https://api.europeana.eu/record/v2/search.json"


@http_retry
async def _request(query: str, rows: int) -> dict:
    resp = await _client.get(
        BASE_URL,
        params={
            "wskey": config.EUROPEANA_API_KEY,
            "query": query,
            "profile": "rich",
            "rows": rows,
            "media": "true",
            "qf": "TYPE:IMAGE",
            "reusability": "open",
        },
    )
    resp.raise_for_status()
    return resp.json()


async def _fetch(query: str, rows: int) -> list[dict] | None:
    if not config.EUROPEANA_API_KEY:
        logger.warning("EUROPEANA_API_KEY не задан")
        return None
    try:
        data = await _request(query, rows)
        if not data.get("success"):
            raise httpx.HTTPError(f"Europeana success=false")
        items = []
        for it in data.get("items", []):
            image = next(iter(it.get("edmPreview") or []), None)
            if not image:
                continue
            items.append({
                "title": next(iter(it.get("title") or []), "Артефакт"),
                "year": next(iter(it.get("dcDate") or []), None),
                "provider": next(iter(it.get("dataProvider") or []), "Europeana"),
                "image": image,
                "link": it.get("guid") or f"https://www.europeana.eu/ru/item{it.get('id', '')}",
            })
        return items or None
    except Exception as exc:
        logger.warning("Europeana error (%s): %s", query, exc)
        return None


async def get_artifacts(query: str, rows: int = 3) -> list[dict] | None:
    """Артефакты с изображениями. None — если сервис недоступен."""
    return await cache.get_or_set(f"europeana:{query}:{rows}", lambda: _fetch(query, rows))
