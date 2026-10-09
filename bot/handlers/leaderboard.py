import html

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.db.engine import SessionFactory
from bot.keyboards.inline import MenuCB, main_menu
from bot.services.user_service import level_title, top_users

router = Router()


async def _render() -> str:
    async with SessionFactory() as session:
        users = await top_users(session, 10)
    if not users:
        return "🏆 Пока нет игроков — стань первым!"
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>Топ-10 путешественников во времени</b>\n"]
    for i, u in enumerate(users):
        place = medals[i] if i < 3 else f"{i + 1}."
        name = html.escape(u.username or u.first_name or f"Игрок {u.telegram_id % 10000}")
        lines.append(f"{place} {name} — {u.xp} XP · <i>{level_title(u.xp)}</i>")
    return "\n".join(lines)


@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: Message):
    await message.answer(await _render(), reply_markup=main_menu())


@router.callback_query(MenuCB.filter(F.action == "leaders"))
async def menu_leaderboard(callback: CallbackQuery):
    await callback.message.answer(await _render())
    await callback.answer()