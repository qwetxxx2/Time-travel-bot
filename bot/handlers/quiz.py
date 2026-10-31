import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.data.questions import build_quiz
from bot.services import quiz_service, user_service

router = Router(name="quiz")
logger = logging.getLogger(__name__)

QUESTIONS_PER_QUIZ = 5   
XP_PER_CORRECT = 10      
PERFECT_BONUS = 25       
MIN_FOR_EXPERT = 4       
EPOCH_TITLES = {
    "antiquity": "🏛 Античность",
    "medieval": "🏰 Средневековье",
    "modern": "⚙️ Новое время",
    "xx": "🎬 XX век",
}

ENTRY_CALLBACKS = {"menu:quiz", "quiz:start", "quiz"}


# клавиатуры

def epochs_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=title, callback_data=f"quiz:epoch:{code}")]
        for code, title in EPOCH_TITLES.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def answers_kb(question: dict, q_index: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=option,
                    callback_data=f"quiz:ans:{q_index}:{option_index}",
                )
            ]
            for option_index, option in enumerate(question["options"])
        ]
    )


def results_kb(epoch: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Ещё раз", callback_data=f"quiz:epoch:{epoch}")],
            [InlineKeyboardButton(text="🗂 Другая эпоха", callback_data="quiz:menu")],
        ]
    )


# логика

async def add_bonus_question(quiz: list[dict], epoch: str) -> list[dict]:

    try:
        bonus = await quiz_service.build_bonus_question(epoch)
    except Exception:
        logger.warning("Бонусный фото-вопрос недоступен, пропускаем")
        return quiz
    if not bonus:
        return quiz
    options = list(bonus.get("options") or [])
    if len(options) < 2:
        return quiz
    quiz.append(
        {
            "q": bonus.get("q") or bonus.get("question") or "Что изображено на фотографии?",
            "options": options,
            "correct": int(bonus.get("correct", 0)),
            "photo": bonus.get("photo") or bonus.get("image"),
            "bonus": True,
        }
    )
    return quiz


def question_text(quiz: list[dict], q_index: int) -> str:
    q = quiz[q_index]
    if q.get("bonus"):
        header = "🎁 <b>Бонусный вопрос — фото из музеев Европы!</b>"
    else:
        total = sum(1 for item in quiz if not item.get("bonus"))
        header = f"<b>Вопрос {q_index + 1} из {total}</b>"
    options = "\n".join(
        f"{i + 1}. {option}" for i, option in enumerate(q["options"])
    )
    return f"{header}\n\n{q['q']}\n\n{options}"


async def edit_question(
    cb: CallbackQuery, text: str, kb: InlineKeyboardMarkup | None
) -> None:
    """Обновляет сообщение с вопросом (учитывая и фото-сообщения)."""
    message = cb.message
    if message is None:
        return
    try:
        if message.photo:
            await message.edit_caption(caption=text, reply_markup=kb)
        else:
            await message.edit_text(text=text, reply_markup=kb)
    except TelegramBadRequest:
        await message.answer(text, reply_markup=kb)


# хендлеры

@router.message(Command("quiz"))
async def cmd_quiz(message: Message, state: FSMContext) -> None:
    """Точка входа командой /quiz."""
    await state.clear()
    await message.answer(
        "🧠 <b>Квиз «Что существовало тогда?»</b>\n\n"
        f"В раунде {QUESTIONS_PER_QUIZ} вопросов"
        " и бонусный фото-вопрос из музеев Европы.\n"
        "Выбирай эпоху:",
        reply_markup=epochs_kb(),
    )


@router.callback_query(F.data.in_(ENTRY_CALLBACKS))
async def cb_quiz_entry(cb: CallbackQuery, state: FSMContext) -> None:
    """Точка входа кнопкой из главного меню."""
    await state.clear()
    await cb.answer()
    await cb.message.answer(
        "🧠 <b>Квиз «Что существовало тогда?»</b>\n\nВыбирай эпоху:",
        reply_markup=epochs_kb(),
    )


@router.callback_query(F.data == "quiz:menu")
async def cb_quiz_menu(cb: CallbackQuery, state: FSMContext) -> None:
    """Возврат к выбору эпохи после финиша."""
    await state.clear()
    await cb.answer()
    await edit_question(cb, "🧠 <b>Квиз</b>\n\nВыбирай эпоху:", epochs_kb())


@router.callback_query(F.data.startswith("quiz:epoch:"))
async def start_quiz(cb: CallbackQuery, state: FSMContext) -> None:
    """Игрок выбрал эпоху — собираем и начинаем раунд."""
    epoch = cb.data.split(":")[2]
    if epoch not in EPOCH_TITLES:
        await cb.answer("Неизвестная эпоха", show_alert=True)
        return
    await cb.answer()

    quiz = await add_bonus_question(build_quiz(epoch, QUESTIONS_PER_QUIZ), epoch)
    await state.update_data(
        quiz=quiz,
        index=0,
        correct=0,
        epoch=epoch,
        answered_index=None,
    )
    await edit_question(cb, question_text(quiz, 0), answers_kb(quiz[0], 0))


@router.callback_query(F.data.startswith("quiz:ans:"))
async def answer_quiz(cb: CallbackQuery, state: FSMContext) -> None:
    """Игрок выбрал вариант ответа.

    Колбэк несёт номер вопроса: quiz:ans:<номер вопроса>:<номер варианта>.
    Клик по старым кнопкам (чужой номер вопроса) просто игнорируется.
    """
    parts = cb.data.split(":")
    q_index, chosen = int(parts[2]), int(parts[3])

    data = await state.get_data()
    quiz = data.get("quiz")
    if not quiz:
        await cb.answer("Раунд не активен — нажми /quiz", show_alert=True)
        return

    index = data["index"]
    if q_index != index or data.get("answered_index") == index:
        await cb.answer("Этот вопрос уже пройден 👌")
        return
    await state.update_data(answered_index=index)

    is_right = chosen == quiz[index]["correct"]
    correct = data["correct"] + (1 if is_right else 0)
    await state.update_data(correct=correct)

    if is_right:
        verdict = f"✅ <b>Верно!</b> +{XP_PER_CORRECT} XP"
    else:
        right_text = quiz[index]["options"][quiz[index]["correct"]]
        verdict = f"❌ <b>Мимо.</b> Правильный ответ: <b>{right_text}</b>"
    explain = quiz[index].get("explain")
    if explain:
        verdict += f"\n\n💡 <i>{explain}</i>"

    next_index = index + 1
    await state.update_data(index=next_index)

    if next_index >= len(quiz):
        await finish_quiz(cb, state, correct)
        await cb.answer()
        return

    next_q = quiz[next_index]
    if next_q.get("bonus") and next_q.get("photo"):
        # Фотографию нельзя «вклеить» в старое сообщение — шлём новым.
        await edit_question(cb, f"{verdict}\n\n🎁 А теперь бонусный вопрос…", None)
        try:
            await cb.message.answer_photo(
                photo=next_q["photo"],
                caption=question_text(quiz, next_index),
                reply_markup=answers_kb(next_q, next_index),
            )
        except Exception:
            # Ссылка на фото не открылась — показываем вопрос текстом.
            next_q["photo"] = None
            await state.update_data(quiz=quiz)
            await cb.message.answer(
                question_text(quiz, next_index),
                reply_markup=answers_kb(next_q, next_index),
            )
    else:
        await edit_question(
            cb,
            f"{verdict}\n\n{question_text(quiz, next_index)}",
            answers_kb(next_q, next_index),
        )
    await cb.answer()


async def finish_quiz(cb: CallbackQuery, state: FSMContext, correct: int) -> None:
    """Конец раунда: XP, бейджи, запись в game_history."""
    data = await state.get_data()
    quiz = data["quiz"]
    epoch = data["epoch"]
    total = len(quiz)
    perfect = correct == total
    xp = correct * XP_PER_CORRECT + (PERFECT_BONUS if perfect else 0)
    telegram_id = cb.from_user.id

    try:
        await user_service.add_xp(telegram_id, xp)
        await user_service.record_game_result(
            telegram_id,
            mode="quiz",
            epoch=epoch,
            correct=correct,
            total=total,
            xp_gained=xp,
        )
    except Exception:
        logger.exception("Не удалось сохранить результат квиза")

    badge_lines: list[str] = []
    try:
        if correct >= MIN_FOR_EXPERT:
            await user_service.award_badge(telegram_id, f"{epoch}_expert")
            badge_lines.append(f"🏅 <b>Знаток эпохи</b> — {EPOCH_TITLES[epoch]}")
        if perfect:
            await user_service.award_badge(telegram_id, "perfect")
            badge_lines.append("🏅 <b>Идеальный раунд</b> — ни одной ошибки")
        badges = await user_service.get_user_badges(telegram_id)
        expert_count = sum(
            1 for b in badges if str(getattr(b, "code", "")).endswith("_expert")
        )
        if expert_count >= len(EPOCH_TITLES):
            await user_service.award_badge(telegram_id, "time_keeper")
            badge_lines.append("🏆 <b>Хранитель времени</b> — знаток всех эпох!")
    except Exception:
        logger.exception("Не удалось выдать бейджи")

    header = "🎉 <b>Идеальный раунд!</b>" if perfect else "🏁 <b>Раунд завершён!</b>"
    text = (
        f"{header}\n\n"
        f"Результат: <b>{correct} из {total}</b>\n"
        f"Опыт: <b>+{xp} XP</b>"
    )
    if badge_lines:
        text += "\n\nДостижения за раунд:\n" + "\n".join(badge_lines)

    await state.clear()
    await edit_question(cb, text, results_kb(epoch))