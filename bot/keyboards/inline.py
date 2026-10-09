from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.data.epochs import EPOCHS, EPOCH_ORDER


class MenuCB(CallbackData, prefix="menu"):
    action: str  # travel | quiz | leaders | profile | settings | home


class EpochCB(CallbackData, prefix="epoch"):
    action: str  # travel | quiz
    epoch: str


class SectionCB(CallbackData, prefix="section"):
    epoch: str
    section: str  # events | fashion | artifacts | links | quiz


class QuizCB(CallbackData, prefix="quiz"):
    action: str   # answer | next | again
    value: int = 0


class SettingsCB(CallbackData, prefix="settings"):
    action: str   # toggle | reset | confirm | back


def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🏛 Путешествие по эпохам", callback_data=MenuCB(action="travel"))
    kb.button(text="❓ Квиз «Что существовало тогда?»", callback_data=MenuCB(action="quiz"))
    kb.button(text="🏆 Топ игроков", callback_data=MenuCB(action="leaders"))
    kb.button(text="👤 Профиль", callback_data=MenuCB(action="profile"))
    kb.button(text="⚙️ Настройки", callback_data=MenuCB(action="settings"))
    kb.adjust(1)
    return kb.as_markup()


def epochs_kb(action: str):
    kb = InlineKeyboardBuilder()
    for code in EPOCH_ORDER:
        kb.button(text=EPOCHS[code]["name"], callback_data=EpochCB(action=action, epoch=code))
    kb.button(text="🔙 В меню", callback_data=MenuCB(action="home"))
    kb.adjust(1)
    return kb.as_markup()


def sections_kb(epoch: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="📜 События", callback_data=SectionCB(epoch=epoch, section="events"))
    kb.button(text="👗 Мода", callback_data=SectionCB(epoch=epoch, section="fashion"))
    kb.button(text="🏺 Артефакты", callback_data=SectionCB(epoch=epoch, section="artifacts"))
    kb.button(text="🔗 Источники и туры", callback_data=SectionCB(epoch=epoch, section="links"))
    kb.button(text="✅ Квиз по эпохе", callback_data=SectionCB(epoch=epoch, section="quiz"))
    kb.button(text="🔙 Другая эпоха", callback_data=MenuCB(action="travel"))
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()


def answers_kb(n_options: int):
    kb = InlineKeyboardBuilder()
    for i in range(n_options):
        kb.button(text="①②③④"[i], callback_data=QuizCB(action="answer", value=i))
    kb.adjust(n_options)
    return kb.as_markup()