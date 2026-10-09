import html

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.media_group import MediaGroupBuilder

from bot.data.epochs import EPOCHS
from bot.db.engine import SessionFactory
from bot.keyboards.inline import EpochCB, MenuCB, SectionCB, epochs_kb, sections_kb
from bot.services import europeana, wikipedia
from bot.services.user_service import award_badge, get_or_create_user
from bot.states import TravelStates

router = Router()


@router.message(Command("travel"))
async def cmd_travel(message: Message, state: FSMContext):
    await state.set_state(TravelStates.choosing_epoch)
    await message.answer("🌍 <b>Выбери эпоху:</b>", reply_markup=epochs_kb("travel"))


@router.callback_query(MenuCB.filter(F.action == "travel"))
async def menu_travel(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.choosing_epoch)
    await callback.message.answer("🌍 <b>Выбери эпоху для путешествия:</b>", reply_markup=epochs_kb("travel"))
    await callback.answer()


@router.callback_query(EpochCB.filter(F.action == "travel"))
async def show_epoch(callback: CallbackQuery, callback_data: EpochCB, state: FSMContext):
    epoch = EPOCHS[callback_data.epoch]
    text = (f"{epoch['name']} <i>({epoch['years']})</i>\n\n"
            f"{html.escape(epoch['intro'])}")

    # Живое дополнение из Википедии; при сбое — просто пропускаем блок
    summary = await wikipedia.get_summary(epoch["wiki_titles"][0])
    if summary and summary.get("extract"):
        text += f"\n\n📖 <b>Из Википедии:</b> {html.escape(summary['extract'][:400])}…"

    await state.update_data(epoch=callback_data.epoch)
    await state.set_state(None)

    async with SessionFactory() as session:
        user = await get_or_create_user(session, callback.from_user.id,
                                        callback.from_user.username, callback.from_user.first_name)
        if await award_badge(session, user, "traveler"):
            await callback.message.answer("🏅 Новое достижение: <b>🧳 Путешественник</b>!")

    await callback.message.answer(text, reply_markup=sections_kb(callback_data.epoch))
    await callback.answer()


@router.callback_query(SectionCB.filter(F.section == "events"))
async def section_events(callback: CallbackQuery, callback_data: SectionCB):
    epoch = EPOCHS[callback_data.epoch]
    lines = [f"📜 <b>Ключевые события — {epoch['plain_name']}</b>\n"]
    lines += [f"• {html.escape(e)}" for e in epoch["events"]]
    lines += ["", "🔗 <b>Подробнее в Википедии:</b>"]
    lines += [f'• <a href="https://ru.wikipedia.org/wiki/{t.replace(" ", "_")}">{html.escape(t)}</a>'
              for t in epoch["wiki_titles"]]
    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(SectionCB.filter(F.section == "fashion"))
async def section_fashion(callback: CallbackQuery, callback_data: SectionCB):
    epoch = EPOCHS[callback_data.epoch]
    await callback.message.answer(
        f"👗 <b>Мода — {epoch['plain_name']}</b>\n\n{html.escape(epoch['fashion'])}")
    await callback.answer()


@router.callback_query(SectionCB.filter(F.section == "artifacts"))
async def section_artifacts(callback: CallbackQuery, callback_data: SectionCB):
    epoch = EPOCHS[callback_data.epoch]
    await callback.answer("Ищу артефакты в музеях Европы…")
    items = await europeana.get_artifacts(epoch["artifact_query"], rows=3)

    if not items:  # graceful degradation
        lines = [f"😔 Сервис Europeana сейчас недоступен.",
                 f"Вот знаменитые артефакты эпохи «{epoch['plain_name']}» из нашего архива:"]
        lines += [f"• {a}" for a in epoch["fallback_artifacts"]]
        await callback.message.answer("\n".join(lines))
        return

    await callback.message.answer(f"🏺 <b>Артефакты — {epoch['plain_name']}</b> (данные: Europeana)")
    album = MediaGroupBuilder()
    for item in items:
        caption = f"<b>{html.escape(str(item['title'])[:100])}</b>"
        if item.get("year"):
            caption += f"\n🗓 {html.escape(str(item['year'])[:40])}"
        caption += f'\n<a href="{item["link"]}">Открыть в Europeana</a>'
        album.add_photo(media=item["image"], caption=caption)
    try:
        await callback.message.answer_media_group(media=album.build())
    except Exception:
        links = "\n".join(f'• <a href="{i["link"]}">{html.escape(str(i["title"])[:60])}</a>' for i in items)
        await callback.message.answer(f"🖼 Картинки не загрузились, вот ссылки:\n{links}")


@router.callback_query(SectionCB.filter(F.section == "links"))
async def section_links(callback: CallbackQuery, callback_data: SectionCB):
    epoch = EPOCHS[callback_data.epoch]
    text = (f"🔗 <b>Источники и виртуальные туры — {epoch['plain_name']}</b>\n\n"
            f'• <a href="{epoch["explore_link"]}">Виртуальная экскурсия (360°) — Google Arts &amp; Culture</a>\n'
            f'• <a href="{epoch["panorama_link"]}">Панорамы Google Street View</a>\n'
            f'• <a href="{epoch["europeana_link"]}">Первоисточники — Europeana</a>\n')
    text += "\n".join(f'• Википедия: <a href="https://ru.wikipedia.org/wiki/{t.replace(" ", "_")}">{html.escape(t)}</a>'
                      for t in epoch["wiki_titles"])
    await callback.message.answer(text)
    await callback.answer()