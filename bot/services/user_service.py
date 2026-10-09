import logging

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Badge, GameHistory, User

logger = logging.getLogger(__name__)

LEVELS = [(0, "Стажёр времени"), (100, "Хронист"), (250, "Архивариус"),
          (500, "Хранитель эпох"), (1000, "Мастер времени")]

BADGES = {
    "traveler":         {"emoji": "🧳", "title": "Путешественник"},
    "time_keeper":      {"emoji": "⏳", "title": "Хранитель времени"},
    "perfect":          {"emoji": "💎", "title": "Безупречный"},
    "antiquity_expert": {"emoji": "🏛", "title": "Знаток Древнего мира"},
    "medieval_expert":  {"emoji": "🏰", "title": "Знаток Средневековья"},
    "modern_expert":    {"emoji": "⚙️", "title": "Знаток Нового времени"},
    "xx_expert":        {"emoji": "🚀", "title": "Знаток XX века"},
}


def level_title(xp: int) -> str:
    title = LEVELS[0][1]
    for threshold, name in LEVELS:
        if xp >= threshold:
            title = name
    return title


async def get_or_create_user(session: AsyncSession, tg_id: int,
                             username: str | None, first_name: str | None) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == tg_id))
    if user is None:
        user = User(telegram_id=tg_id,
                    username=(username or "")[:64] or None,
                    first_name=(first_name or "")[:128] or None)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("Новый пользователь: tg_id=%s", tg_id)
    return user


async def add_xp(session: AsyncSession, user: User, amount: int) -> tuple[int, bool]:
    old_level = user.level
    user.xp += amount
    user.level = user.xp // 100 + 1
    await session.commit()
    return user.level, user.level > old_level


async def award_badge(session: AsyncSession, user: User, code: str) -> bool:
    """Выдаёт бейдж. Возвращает True, если он новый."""
    exists = await session.scalar(select(Badge).where(Badge.user_id == user.id, Badge.code == code))
    if exists:
        return False
    session.add(Badge(user_id=user.id, code=code))
    await session.commit()
    logger.info("Бейдж выдан: tg_id=%s code=%s", user.telegram_id, code)
    return True


async def save_game(session: AsyncSession, user: User, mode: str, epoch: str,
                    correct: int, total: int, xp_gained: int) -> None:
    session.add(GameHistory(user_id=user.id, mode=mode, epoch=epoch,
                            correct=correct, total=total, xp_gained=xp_gained))
    await session.commit()


async def epochs_played(session: AsyncSession, user_id: int) -> set[str]:
    rows = await session.scalars(select(GameHistory.epoch).where(GameHistory.user_id == user_id))
    return set(rows)


async def games_count(session: AsyncSession, user_id: int) -> int:
    return await session.scalar(
        select(func.count()).select_from(GameHistory).where(GameHistory.user_id == user_id)) or 0


async def user_badges(session: AsyncSession, user_id: int) -> list[str]:
    rows = await session.scalars(select(Badge.code).where(Badge.user_id == user_id))
    return [c for c in rows if c in BADGES]


async def top_users(session: AsyncSession, limit: int = 10) -> list[User]:
    result = await session.scalars(select(User).order_by(User.xp.desc()).limit(limit))
    return list(result)


async def reset_progress(session: AsyncSession, user: User) -> None:
    await session.execute(delete(Badge).where(Badge.user_id == user.id))
    await session.execute(delete(GameHistory).where(GameHistory.user_id == user.id))
    user.xp, user.level = 0, 1
    await session.commit()
    logger.info("Прогресс сброшен: tg_id=%s", user.telegram_id)