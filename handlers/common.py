from __future__ import annotations

from datetime import datetime
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from database.models import Role
from handlers.common_utils import ensure_actor, role_label
from locales import t
from services import Service
from utils import export_csv, export_pdf, export_xlsx, language_kb, main_menu, stats_export_kb

router = Router(name="common")


@router.message(Command("start"))
async def start_handler(message: Message, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, message.from_user, settings)
    if not actor.active and actor.role != Role.ADMIN:
        await message.answer(t(actor.language, "no_access"))
        return

    lang = actor.language or settings.default_language
    role = role_label(actor.role)
    await message.answer(
        f"{t(lang, 'welcome')}\n\nВаша роль: <b>{role}</b>",
        reply_markup=main_menu(role),
    )


@router.message(Command("menu"))
async def menu_cmd(message: Message, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, message.from_user, settings)
    await message.answer("Главное меню", reply_markup=main_menu(role_label(actor.role)))


@router.callback_query(F.data == "menu")
async def menu_cb(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, callback.from_user, settings)
    await callback.message.edit_text("Главное меню", reply_markup=main_menu(role_label(actor.role)))
    await callback.answer()


@router.message(Command("lang"))
async def lang_cmd(message: Message) -> None:
    await message.answer("Выберите язык / Choose language", reply_markup=language_kb())


@router.callback_query(F.data.startswith("lang:"))
async def set_lang(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    lang = callback.data.split(":", 1)[1]
    service = Service(session)
    actor = await ensure_actor(session, callback.from_user, settings)
    actor.language = lang
    await session.commit()
    await service.log(actor.telegram_id, "set_lang", lang)
    await callback.answer("Язык обновлен")
    await callback.message.answer("Главное меню", reply_markup=main_menu(role_label(actor.role)))


@router.message(Command("stats"))
async def stats_cmd(message: Message, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, message.from_user, settings)
    service = Service(session)
    manager_id = actor.id if actor.role == Role.MANAGER else None
    stats = await service.stats_summary(manager_id=manager_id)

    await message.answer(
        "\n".join(
            [
                "📊 Статистика:",
                f"Всего: {stats['total']}",
                f"Новые: {stats['new']}",
                f"В работе: {stats['accepted']}",
                f"Выполнены: {stats['done']}",
                f"Оплачены: {stats['paid']}",
                f"Оборот: {stats['revenue']:.2f}",
            ]
        ),
        reply_markup=stats_export_kb("manager" if actor.role == Role.MANAGER else "admin"),
    )


@router.callback_query(F.data.startswith("stats:"))
async def stats_cb(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, callback.from_user, settings)
    service = Service(session)
    scope = callback.data.split(":", 1)[1]
    manager_id = actor.id if scope == "manager" else None
    if scope == "admin" and actor.role != Role.ADMIN:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    stats = await service.stats_summary(manager_id=manager_id)
    await callback.message.answer(
        f"📊 {scope.upper()}\nВсего: {stats['total']}\nНовые: {stats['new']}\nВ работе: {stats['accepted']}\n"
        f"Выполнены: {stats['done']}\nОплачены: {stats['paid']}\nОборот: {stats['revenue']:.2f}",
        reply_markup=stats_export_kb(scope),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("export:"))
async def export_cb(callback: CallbackQuery, session: AsyncSession, settings: Settings, state: FSMContext) -> None:
    actor = await ensure_actor(session, callback.from_user, settings)
    _, scope, fmt = callback.data.split(":")

    if scope == "admin" and actor.role != Role.ADMIN:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    service = Service(session)
    manager_id = actor.id if scope == "manager" else None
    rows = await service.export_orders(manager_id=manager_id)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if fmt == "csv":
        path = export_csv(rows, settings.export_dir / f"orders_{scope}_{ts}.csv")
        mime = "text/csv"
    elif fmt == "xlsx":
        path = export_xlsx(rows, settings.export_dir / f"orders_{scope}_{ts}.xlsx")
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        path = export_pdf(rows, settings.export_dir / f"orders_{scope}_{ts}.pdf")
        mime = "application/pdf"

    data = path.read_bytes()
    await callback.message.answer_document(BufferedInputFile(data, filename=Path(path).name), caption=f"Экспорт {fmt.upper()}")
    await callback.answer("Файл готов")
