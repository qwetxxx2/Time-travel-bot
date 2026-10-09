import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    DB_URL: str = os.getenv("DB_URL", "sqlite+aiosqlite:///time_travel.db")
    EUROPEANA_API_KEY: str = os.getenv("EUROPEANA_API_KEY", "")
    WIKI_LANG: str = os.getenv("WIKI_LANG", "ru")
    CACHE_TTL: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()