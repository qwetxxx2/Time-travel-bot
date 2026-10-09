import html

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.engine import SessionFactory
from bot.keyboards.inline import MenuCB, SettingsCB, main_menu
from bot.services.user_service import (BADGES, games_count, get_or_create_user,
                                       level_title, reset_progress, user_badges)

router = Router()


def settings_kb(notif: bool):
    kb = InlineKeyboardBuilder()
    kb.button(text=f"🔔 Факт дня: {'вкл ✅' if notif else 'выкл ❌'}",
              callback_data=SettingsCB(action="toggle"))
    kb.button(text="🗑 Сбросить прогресс", callback_data=SettingsCB(action="reset"))
    kb.button(text="🔙 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1)
    return kb.as_markup()


async def _profile_text(tg_id: int, username: str | None, first_name: str | None) -> str:
    async with SessionFactory() as session:
        user = await get_or_create_user(session, tg_id, username, first_name)
        badges = await user_badges(session, user.id)
        games = await games_count(session, user.id)
    badge_line = "  ".join(f"{BADGES[c]['emoji']}" for c in badges) or "пока нет"
    to_next = 100 - user.xp % 100
    return (f"👤 <b>Профиль</b>\n\n"
            f"🎖 Уровень <b>{user.level}</b> — <i>{level_title(user.xp)}</i>\n"
            f"⭐ XP: <b>{user.xp}</b> (до следующего уровня: {to_next})\n"
            f"🎮 Игр сыграно: <b>{games}</b>\n"
            f"🏅 Достижения: {badge_line}\n"
            f"🔔 Уведомления: {'вкл' if user.notifications_enabled else 'выкл'}")


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    await message.answer(await _profile_text(message.from_user.id,
                                             message.from_user.username, message.from_user.first_name),
                         reply_markup=main_menu())


@router.callback_query(MenuCB.filter(F.action == "profile"))
async def menu_profile(callback: CallbackQuery):
    await callback.message.answer(await _profile_text(callback.from_user.id,
                                                      callback.from_user.username,
                                                      callback.from_user.first_name))
    await callback.answer()


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    async with SessionFactory() as session:
        user = await get_or_create_user(session, message.from_user.id,
                                        message.from_user.username, message.from_user.first_name)
    await message.answer("⚙️ <b>Настройки</b>", reply_markup=settings_kb(user.notifications_enabled))


@router.callback_query(MenuCB.filter(F.action == "settings"))
async def menu_settings(callback: CallbackQuery):
    async with SessionFactory() as session:
        user = await get_or_create_user(session, callback.from_user.id,
                                        callback.from_user.username, callback.from_user.first_name)
    await callback.message.answer("⚙️ <b>Настройки</b>", reply_markup=settings_kb(user.notifications_enabled))
    await callback.answer()


@router.callback_query(SettingsCB.filter(F.action == "toggle"))
async def toggle_notifications(callback: CallbackQuery):
    async with SessionFactory() as session:
        user = await get_or_create_user(session, callback.from_user.id,
                                        callback.from_user.username, callback.from_user.first_name)
        user.notifications_enabled = not user.notifications_enabled
        await session.commit()
    await callback.message.edit_reply_markup(reply_markup=settings_kb(user.notifications_enabled))
    await callback.answer("Сохранено ✅")


@router.callback_query(SettingsCB.filter(F.action == "reset"))
async def ask_reset(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="⚠️ Да, удалить всё!", callback_data=SettingsCB(action="confirm"))
    kb.button(text="↩️ Отмена", callback_data=SettingsCB(action="back"))
    kb.adjust(1)
    await callback.message.answer("🗑 Точно сбросить прогресс? Будут удалены XP, "
                                  "достижения и история игр.", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(SettingsCB.filter(F.action == "confirm"))
async def do_reset(callback: CallbackQuery):
    async with SessionFactory() as session:
        user = await get_or_create_user(session, callback.from_user.id,
                                        callback.from_user.username, callback.from_user.first_name)
        await reset_progress(session, user)
    await callback.message.answer("✅ Прогресс сброшен. С чистого листа!")
    await callback.answer()


@router.callback_query(SettingsCB.filter(F.action == "back"))
async def cancel_reset(callback: CallbackQuery):
    await callback.message.answer("⚙️ <b>Настройки</b>")
    await callback.answer("Отменено")