import html
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import CallbackQuery, Message

from bot.data.epochs import EPOCHS, EPOCH_ORDER
from bot.data.questions import build_quiz
from bot.db.engine import SessionFactory
from bot.keyboards.inline import EpochCB, MenuCB, QuizCB, SectionCB, answers_kb, epochs_kb, main_menu
from bot.services import quiz_service
from bot.services.user_service import (add_xp, award_badge, epochs_played, get_or_create_user,
                                       save_game, BADGES)
from bot.states import QuizStates

logger = logging.getLogger(__name__)
router = Router()

XP_PER_CORRECT = 10
PERFECT_BONUS = 25


@router.message(Command("quiz"))
async def cmd_quiz(message: Message):
    await message.answer("❓ <b>Квиз «Что существовало тогда?»</b>\nВыбери эпоху:", reply_markup=epochs_kb("quiz"))


@router.callback_query(MenuCB.filter(F.action == "quiz"))
async def menu_quiz(callback: CallbackQuery):
    await callback.message.answer("❓ <b>Квиз «Что существовало тогда?»</b>\nВыбери эпоху:",
                                  reply_markup=epochs_kb("quiz"))
    await callback.answer()


@router.callback_query(EpochCB.filter(F.action == "quiz"))
async def start_from_epoch(callback: CallbackQuery, callback_data: EpochCB, state: FSMContext):
    await _start_quiz(callback, callback_data.epoch, state)


@router.callback_query(SectionCB.filter(F.section == "quiz"))
async def start_from_section(callback: CallbackQuery, callback_data: SectionCB, state: FSMContext):
    await _start_quiz(callback, callback_data.epoch, state)


@router.callback_query(QuizCB.filter(F.action == "again"))
async def quiz_again(callback: CallbackQuery, callback_data: QuizCB, state: FSMContext):
    await _start_quiz(callback, EPOCH_ORDER[callback_data.value], state)


async def _start_quiz(callback: CallbackQuery, epoch_code: str, state: FSMContext):
    questions = build_quiz(epoch_code, count=5)
    bonus = await quiz_service.build_bonus_question()   # None, если Europeana недоступна
    if bonus:
        questions.append(bonus)
    await state.set_state(QuizStates.answering)
    await state.update_data(quiz=questions, index=0, correct=0, streak=0, epoch=epoch_code)
    await callback.answer("Квиз начинается!")
    await _send_question(callback.message, questions[0], 0, len(questions))


async def _send_question(message: Message, question: dict, index: int, total: int):
    header = f"❓ <b>Вопрос {index + 1}/{total}</b>\n\n{html.escape(question['q'])}"
    kb = answers_kb(len(question["options"]))
    if "artifact" in question:  # бонусный вопрос с фото из Europeana
        a = question["artifact"]
        caption = header + f"\n\n<b>{html.escape(str(a['title'])[:100])}</b>"
        if a.get("year"):
            caption += f"\n🗓 {html.escape(str(a['year'])[:40])}"
        try:
            await message.answer_photo(photo=a["image"], caption=caption, reply_markup=kb)
            return
        except Exception:
            caption += f'\n\n<a href="{a["link"]}">Ссылка на артефакт</a>'
    options = "\n".join(f"{'①②③④'[i]} {html.escape(o)}" for i, o in enumerate(question["options"]))
    await message.answer(f"{header}\n\n{options}", reply_markup=kb)


@router.callback_query(QuizStates.answering, QuizCB.filter(F.action == "answer"))
async def answer(callback: CallbackQuery, callback_data: QuizCB, state: FSMContext):
        data = await state.get_data()
    quiz, index = data["quiz"], data["index"]
    if index >= len(quiz):
        await callback.answer()
        return
    if data.get("answered_index") == index:          
        await callback.answer("Этот вопрос уже учтён ✅")
        return

    question = quiz[index]
    is_correct = callback_data.value == question["correct"]

    await state.update_data(correct=data["correct"] + int(is_correct),
                            streak=data["streak"] + 1 if is_correct else 0,
                            answered_index=index)    

    if is_correct:
        text = "✅ <b>Верно!</b>"
    else:
        right = question["options"][question["correct"]]
        text = f"❌ <b>Неверно.</b> Правильный ответ: <b>{html.escape(right)}</b>"
    text += f"\n\n💡 {html.escape(question['explain'])}"

    gained = XP_PER_CORRECT if is_correct else 0
    async with SessionFactory() as session:
        user = await get_or_create_user(session, callback.from_user.id,
                                        callback.from_user.username, callback.from_user.first_name)
        new_level, leveled_up = await add_xp(session, user, gained)
    if leveled_up:
        text += f"\n\n🎉 Новый уровень: <b>{new_level}</b>!"

    kb = InlineKeyboardBuilder()
    label = "➡️ Дальше" if index + 1 < len(quiz) else "🏁 Итоги"
    kb.button(text=label, callback_data=QuizCB(action="next", value=index + 1))
    kb.adjust(1)
    await callback.message.answer(text, reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(QuizStates.answering, QuizCB.filter(F.action == "next"))
async def next_question(callback: CallbackQuery, callback_data: QuizCB, state: FSMContext):
    data = await state.get_data()
    quiz = data["quiz"]
    index = callback_data.value
    if index < len(quiz):
        await state.update_data(index=index)
        await _send_question(callback.message, quiz[index], index, len(quiz))
        await callback.answer()
        return

    # ─── Итоги квиза ───
    await state.clear()
    correct, total, epoch = data["correct"], len(quiz), data["epoch"]
    perfect = correct == total
    xp_total = correct * XP_PER_CORRECT + (PERFECT_BONUS if perfect else 0)
    logger.info("Квиз завершён: tg_id=%s epoch=%s %s/%s", callback.from_user.id, epoch, correct, total)

    new_badges: list[str] = []
    async with SessionFactory() as session:
        user = await get_or_create_user(session, callback.from_user.id,
                                        callback.from_user.username, callback.from_user.first_name)
        if perfect:
            if await award_badge(session, user, "perfect"):
                new_badges.append("perfect")
            await add_xp(session, user, PERFECT_BONUS)
        if correct >= round(total * 0.8):
            code = f"{epoch}_expert"
            if await award_badge(session, user, code):
                new_badges.append(code)
        await save_game(session, user, "quiz", epoch, correct, total, xp_total)
        if set(EPOCH_ORDER) <= await epochs_played(session, user.id) \
                and await award_badge(session, user, "time_keeper"):
            new_badges.append("time_keeper")

    text = (f"🏁 <b>Квиз завершён!</b>\n\n"
            f"Эпоха: <b>{EPOCHS[epoch]['plain_name']}</b>\n"
            f"Правильных ответов: <b>{correct}</b> из <b>{total}</b>\n"
            f"Заработано XP: <b>+{xp_total}</b>")
    if new_badges:
        text += "\n\n🏅 <b>Новые достижения:</b>\n" + \
                "\n".join(f"{BADGES[c]['emoji']} {BADGES[c]['title']}" for c in new_badges)

    kb = InlineKeyboardBuilder()
    kb.button(text="🔁 Ещё раз", callback_data=QuizCB(action="again", value=EPOCH_ORDER.index(epoch)))
    kb.button(text="🌍 Другая эпоха", callback_data=MenuCB(action="quiz"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1)
    await callback.message.answer(text, reply_markup=kb.as_markup())
    await callback.answer()