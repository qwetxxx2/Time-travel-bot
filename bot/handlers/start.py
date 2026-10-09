import html
import random

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.data.facts import FACTS
from bot.db.engine import SessionFactory
from bot.keyboards.inline import MenuCB, main_menu
from bot.services.user_service import get_or_create_user

router = Router()

WELCOME = (
    "⏳ <b>Путешествия во времени</b>\n\n"
    "Привет, {name}! Это интерактивный гид по эпохам.\n\n"
    "🏛 <b>Путешествие</b> — события, мода и настоящие артефакты из музеев Европы.\n"
    "❓ <b>Квиз</b> — угадай, что существовало в выбранную эпоху.\n"
    "🏆 <b>Топ игроков</b> — соревнуйся с другими путешественниками.\n\n"
    "За правильные ответы начисляются XP, уровни и достижения. В путь!"
)


@router.message(CommandStart())
async def cmd_start(message: Message):
    async with SessionFactory() as session:
        await get_or_create_user(session, message.from_user.id,
                                 message.from_user.username, message.from_user.first_name)
    name = html.escape(message.from_user.first_name or "путешественник")
    await message.answer(WELCOME.format(name=name), reply_markup=main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Команды:</b>\n"
        "/start — главное меню\n"
        "/travel — путешествие по эпохам\n"
        "/quiz — квиз\n"
        "/profile — профиль и достижения\n"
        "/leaderboard — топ-10 игроков\n"
        "/settings — настройки\n"
        "/fact — случайный исторический факт"
    )


@router.message(Command("fact"))
async def cmd_fact(message: Message):
    await message.answer(f"💡 <b>Факт дня:</b>\n{random.choice(FACTS)}")


from aiogram import F

@router.callback_query(MenuCB.filter(F.action == "home"))
async def go_home(callback):
    await callback.message.answer("⏳ Главное меню:", reply_markup=main_menu())
    await callback.answer()