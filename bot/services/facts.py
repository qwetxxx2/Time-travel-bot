import asyncio
import logging
import random
from datetime import datetime, timedelta

from sqlalchemy import select

from bot.data.facts import FACTS
from bot.db.engine import SessionFactory
from bot.db.models import User

logger = logging.getLogger(__name__)


async def daily_fact_task(bot) -> None:
    """Рассылка «Факта дня» каждый день в 12:00 UTC подписчикам."""
    while True:
        try:
            now = datetime.utcnow()
            target = now.replace(hour=12, minute=0, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            await asyncio.sleep((target - now).total_seconds())
            text = f"💡 <b>Факт дня:</b>\n{random.choice(FACTS)}"
            async with SessionFactory() as session:
                users = list(await session.scalars(
                    select(User).where(User.notifications_enabled == True)))  # noqa: E712
            for user in users:
                try:
                    await bot.send_message(user.telegram_id, text)
                except Exception:
                    pass  # пользователь мог заблокировать бота
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Ошибка задачи «Факт дня»")
            await asyncio.sleep(60)