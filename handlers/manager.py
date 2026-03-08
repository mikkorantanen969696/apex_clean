from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from database.models import City, OrderStatus, Role
from handlers.common_utils import ensure_actor, role_label
from locales import t
from services import Service, verify_password
from states import ManagerAuthState, ManagerOrderState
from utils import cities_kb, create_invoice_pdf, main_menu, order_actions_kb

router = Router(name="manager")


@router.message(Command("login"))
async def manager_login_start(message: Message, session: AsyncSession, settings: Settings, state: FSMContext) -> None:
    actor = await ensure_actor(session, message.from_user, settings)
    if actor.role != Role.MANAGER:
        await message.answer("Эта команда только для менеджеров")
        return
    await state.set_state(ManagerAuthState.waiting_password)
    await message.answer(t(actor.language, "ask_password"))


@router.message(ManagerAuthState.waiting_password)
async def manager_login_finish(message: Message, session: AsyncSession, settings: Settings, state: FSMContext) -> None:
    actor = await ensure_actor(session, message.from_user, settings)
    if verify_password(message.text.strip(), actor.password_hash):
        actor.active = True
        await session.commit()
        await state.clear()
        await message.answer(t(actor.language, "auth_ok"), reply_markup=main_menu(role_label(actor.role)))
        return
    await message.answer(t(actor.language, "auth_fail"))


@router.callback_query(F.data == "manager:create_order")
async def create_order_start(callback: CallbackQuery, session: AsyncSession, settings: Settings, state: FSMContext) -> None:
    actor = await ensure_actor(session, callback.from_user, settings)
    if actor.role not in (Role.MANAGER, Role.ADMIN):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    service = Service(session)
    cities = await service.list_cities()
    if not cities:
        await callback.message.answer("Сначала добавьте города в админке")
        await callback.answer()
        return

    await state.set_state(ManagerOrderState.city)
    await callback.message.answer(
        "Выберите город для заявки:",
        reply_markup=cities_kb([(city.id, city.name) for city in cities], prefix="order_city"),
    )
    await callback.answer()


@router.callback_query(ManagerOrderState.city, F.data.startswith("order_city:"))
async def create_order_city(callback: CallbackQuery, state: FSMContext) -> None:
    city_id = int(callback.data.split(":", 1)[1])
    await state.update_data(city_id=city_id)
    await state.set_state(ManagerOrderState.client_name)
    await callback.message.answer("Введите имя клиента:")
    await callback.answer()


@router.message(ManagerOrderState.client_name)
async def create_order_client_name(message: Message, state: FSMContext) -> None:
    await state.update_data(client_name=message.text.strip())
    await state.set_state(ManagerOrderState.client_phone)
    await message.answer("Введите телефон клиента:")


@router.message(ManagerOrderState.client_phone)
async def create_order_client_phone(message: Message, state: FSMContext) -> None:
    await state.update_data(client_phone=message.text.strip())
    await state.set_state(ManagerOrderState.address)
    await message.answer("Введите адрес:")


@router.message(ManagerOrderState.address)
async def create_order_address(message: Message, state: FSMContext) -> None:
    await state.update_data(address=message.text.strip())
    await state.set_state(ManagerOrderState.service_type)
    await message.answer("Введите тип услуги:")


@router.message(ManagerOrderState.service_type)
async def create_order_service_type(message: Message, state: FSMContext) -> None:
    await state.update_data(service_type=message.text.strip())
    await state.set_state(ManagerOrderState.price)
    await message.answer("Введите стоимость (число):")


@router.message(ManagerOrderState.price)
async def create_order_price(message: Message, state: FSMContext) -> None:
    try:
        price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Неверный формат цены")
        return
    await state.update_data(price=price)
    await state.set_state(ManagerOrderState.date)
    await message.answer("Введите дату (YYYY-MM-DD):")


@router.message(ManagerOrderState.date)
async def create_order_date(message: Message, state: FSMContext) -> None:
    try:
        datetime.strptime(message.text.strip(), "%Y-%m-%d")
    except ValueError:
        await message.answer("Неверная дата. Формат: YYYY-MM-DD")
        return
    await state.update_data(date=message.text.strip())
    await state.set_state(ManagerOrderState.time)
    await message.answer("Введите время (HH:MM):")


@router.message(ManagerOrderState.time)
async def create_order_time(message: Message, session: AsyncSession, settings: Settings, state: FSMContext) -> None:
    try:
        datetime.strptime(message.text.strip(), "%H:%M")
    except ValueError:
        await message.answer("Неверное время. Формат: HH:MM")
        return

    data = await state.get_data()
    actor = await ensure_actor(session, message.from_user, settings)
    service = Service(session)

    scheduled_at = datetime.strptime(f"{data['date']} {message.text.strip()}", "%Y-%m-%d %H:%M")
    order = await service.create_order(
        city_id=int(data["city_id"]),
        manager_id=actor.id,
        client_name=data["client_name"],
        client_phone=data["client_phone"],
        address=data["address"],
        service_type=data["service_type"],
        price=float(data["price"]),
        scheduled_at=scheduled_at,
    )

    city = await session.get(City, int(data["city_id"]))
    text = (
        f"🧾 Новый заказ #{order.id}\n"
        f"Город: {city.name if city else data['city_id']}\n"
        f"Адрес: {order.address}\n"
        f"Услуга: {order.service_type}\n"
        f"Цена: {order.price}\n"
        f"Дата/время: {order.scheduled_at:%Y-%m-%d %H:%M}\n"
        f"Контакт: {order.client_name}, {order.client_phone}"
    )

    if settings.support_chat_id:
        sent = await message.bot.send_message(
            chat_id=settings.support_chat_id,
            text=text,
            message_thread_id=city.topic_id if city and city.topic_id else None,
            reply_markup=order_actions_kb(order.id),
        )
        order.chat_message_id = sent.message_id
        await session.commit()

    await state.clear()
    await message.answer(f"Заказ #{order.id} создан ✅", reply_markup=main_menu(role_label(actor.role)))


@router.callback_query(F.data == "manager:orders")
async def list_my_orders(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, callback.from_user, settings)
    if actor.role not in (Role.MANAGER, Role.ADMIN):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    service = Service(session)
    orders = await service.list_manager_orders(actor.id)
    if not orders:
        await callback.message.answer("У вас пока нет заказов")
        await callback.answer()
        return

    lines = ["📦 Мои заказы:"]
    for order in orders[:20]:
        lines.append(
            f"#{order.id} | {order.service_type} | {order.price} | {order.status.value} | {order.scheduled_at:%Y-%m-%d %H:%M}"
        )
    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data == "manager:invoice")
async def manager_invoice(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, callback.from_user, settings)
    if actor.role not in (Role.MANAGER, Role.ADMIN):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    service = Service(session)
    orders = await service.list_manager_orders(actor.id)
    target = next((o for o in orders if o.status in (OrderStatus.NEW, OrderStatus.ACCEPTED)), None)
    if not target:
        await callback.message.answer("Нет активного заказа для счёта")
        await callback.answer()
        return

    pdf_path = settings.export_dir / f"invoice_{target.id}.pdf"
    qr_path = settings.export_dir / f"invoice_{target.id}.png"
    create_invoice_pdf(
        output_path=pdf_path,
        qr_path=qr_path,
        order_id=target.id,
        client_name=target.client_name,
        service_type=target.service_type,
        amount=target.price,
        payment_link=f"https://example-pay.local/pay?order={target.id}&amount={target.price}",
    )

    await callback.message.answer_document(
        BufferedInputFile(pdf_path.read_bytes(), filename=pdf_path.name),
        caption=f"Счёт по заказу #{target.id}",
    )
    await callback.answer("Счёт сформирован")
