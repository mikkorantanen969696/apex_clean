from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from database.models import Order, Photo, Role, User
from handlers.common_utils import ensure_actor
from services import Service
from states import CleanerPaymentState
from utils import order_actions_kb

router = Router(name="cleaner")


@router.callback_query(F.data == "cleaner:new_orders")
async def cleaner_new_orders(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, callback.from_user, settings)
    if actor.role != Role.CLEANER:
        await callback.answer("Только для клинеров", show_alert=True)
        return
    if not actor.city_id:
        await callback.message.answer("Администратор должен назначить вам город")
        await callback.answer()
        return

    service = Service(session)
    orders = await service.list_new_orders_for_city(actor.city_id)
    if not orders:
        await callback.message.answer("Новых заказов нет")
        await callback.answer()
        return

    for order in orders[:10]:
        await callback.message.answer(
            f"🆕 Заказ #{order.id}\nАдрес: {order.address}\nУслуга: {order.service_type}\n"
            f"Цена: {order.price}\nВремя: {order.scheduled_at:%Y-%m-%d %H:%M}",
            reply_markup=order_actions_kb(order.id),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("order_take:"))
async def cleaner_take_order(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, callback.from_user, settings)
    if actor.role != Role.CLEANER:
        await callback.answer("Только для клинеров", show_alert=True)
        return

    order_id = int(callback.data.split(":", 1)[1])
    service = Service(session)
    order = await service.assign_cleaner(order_id=order_id, cleaner_id=actor.id)
    if not order:
        await callback.answer("Заказ уже занят", show_alert=True)
        return

    manager = await session.get(User, order.manager_id)
    if manager:
        await callback.bot.send_message(
            manager.telegram_id,
            f"✅ Заказ #{order.id} взят клинером {actor.full_name} (@{actor.username or 'no_username'})",
        )

    await callback.message.answer(
        f"Вы взяли заказ #{order.id}.\nКонтакт менеджера: {manager.full_name if manager else '-'}"
    )
    await callback.answer("Заказ закреплён")


@router.message(F.photo)
async def cleaner_upload_photo(message: Message, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, message.from_user, settings)
    if actor.role != Role.CLEANER:
        return

    caption = (message.caption or "").strip().lower()
    if not caption.startswith("order:"):
        return

    try:
        order_id, kind = caption.replace(" ", "").split(":")[1].split("|")
        order_id = int(order_id)
        if kind not in {"before", "after"}:
            raise ValueError
    except ValueError:
        await message.answer("Подпись должна быть: order:<id>|before или order:<id>|after")
        return

    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    dest = settings.media_dir / f"order_{order_id}_{kind}_{photo.file_unique_id}.jpg"
    await message.bot.download_file(file.file_path, destination=dest)

    result = await session.execute(select(Photo).where(Photo.order_id == order_id))
    obj = result.scalar_one_or_none()
    if not obj:
        obj = Photo(order_id=order_id)
        session.add(obj)

    if kind == "before":
        obj.photo_before = str(dest)
    else:
        obj.photo_after = str(dest)

    await session.commit()
    await message.answer(f"Фото {kind} сохранено для заказа #{order_id}")


@router.callback_query(F.data == "cleaner:payment")
async def cleaner_payment_start(callback: CallbackQuery, session: AsyncSession, settings: Settings, state) -> None:
    actor = await ensure_actor(session, callback.from_user, settings)
    if actor.role != Role.CLEANER:
        await callback.answer("Только для клинеров", show_alert=True)
        return
    await state.set_state(CleanerPaymentState.waiting_requisites)
    await callback.message.answer("Введите реквизиты для выплат:")
    await callback.answer()


@router.message(CleanerPaymentState.waiting_requisites)
async def cleaner_payment_finish(message: Message, session: AsyncSession, settings: Settings, state) -> None:
    actor = await ensure_actor(session, message.from_user, settings)
    actor.payment_details = message.text.strip()
    await session.commit()
    await state.clear()
    await message.answer("Реквизиты сохранены ✅")


@router.callback_query(F.data.startswith("chat_manager:"))
async def chat_manager_hint(callback: CallbackQuery) -> None:
    order_id = int(callback.data.split(":", 1)[1])
    await callback.message.answer(
        f"Для заказа #{order_id} используйте reply на системные сообщения или личный чат по полученному контакту менеджера."
    )
    await callback.answer()
