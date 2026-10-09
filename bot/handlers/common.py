import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, ErrorEvent, Message

from bot.keyboards.inline import main_menu

logger = logging.getLogger(__name__)
router = Router()


@router.message()  # валидация «всего остального» — подключается ПОСЛЕДНИМ
async def fallback(message: Message):
    logger.info("Необработанный ввод: tg_id=%s, type=%s", message.from_user.id, message.content_type)
    await message.answer("🤖 Я понимаю кнопки и команды из /help", reply_markup=main_menu())


@router.callback_query()
async def stale_callback(callback: CallbackQuery):
    await callback.answer("⌛ Кнопка неактуальна, откройте меню заново")


@router.error()
async def on_error(event: ErrorEvent):
    logger.exception("Ошибка обработки: %s", event.exception)
    try:
        cb = event.update.callback_query
        if cb is not None:
            await cb.answer("⚠️ Сбой сети — попробуй ещё раз через пару секунд", show_alert=True)
        elif event.update.message is not None:
            await event.update.message.answer("⚠️ Что-то пошло не так. Попробуй ещё раз позже.")
    except Exception:
        pass