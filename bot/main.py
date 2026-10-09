import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import config
from bot.db.engine import init_db
from bot.handlers import common, leaderboard, profile, quiz, start, travel
from bot.services.facts import daily_fact_task


async def main() -> None:
    logging.basicConfig(level=config.LOG_LEVEL,
                        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    await init_db()

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_routers(start.router, travel.router, quiz.router,
                       profile.router, leaderboard.router, common.router)
    dp.error.register(on_error) 

    asyncio.create_task(daily_fact_task(bot))
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())