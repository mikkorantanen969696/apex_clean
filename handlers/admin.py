from __future__ import annotations

import secrets

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from database.models import Order, Role, User
from handlers.common_utils import ensure_actor
from services import Service, hash_password
from states import AdminCreateUserState
from utils import admin_users_kb, cities_kb

router = Router(name="admin")


@router.callback_query(F.data == "admin:users")
async def admin_users(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, callback.from_user, settings)
    if actor.role != Role.ADMIN:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    await callback.message.answer("Управление пользователями", reply_markup=admin_users_kb())
    await callback.answer()


@router.callback_query(F.data.in_({"admin:add_manager", "admin:add_cleaner"}))
async def admin_add_user_start(callback: CallbackQuery, session: AsyncSession, settings: Settings, state: FSMContext) -> None:
    actor = await ensure_actor(session, callback.from_user, settings)
    if actor.role != Role.ADMIN:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    role = "manager" if callback.data.endswith("manager") else "cleaner"
    await state.set_state(AdminCreateUserState.telegram_id)
    await state.update_data(role=role)
    await callback.message.answer(f"Введите Telegram ID для роли {role}:")
    await callback.answer()


@router.message(AdminCreateUserState.telegram_id)
async def admin_add_user_tg_id(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    mode = data.get("role")
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно число")
        return

    if mode == "deactivate":
        service = Service(session)
        ok = await service.deactivate_user(tg_id)
        await state.clear()
        await message.answer("Пользователь деактивирован ✅" if ok else "Пользователь не найден")
        return

    await state.update_data(telegram_id=tg_id)
    await state.set_state(AdminCreateUserState.full_name)
    await message.answer("Введите ФИО:")


@router.message(AdminCreateUserState.full_name)
async def admin_add_user_name(message: Message, state: FSMContext) -> None:
    await state.update_data(full_name=message.text.strip())
    await state.set_state(AdminCreateUserState.username)
    await message.answer("Введите username без @ (или -):")


@router.message(AdminCreateUserState.username)
async def admin_add_user_username(message: Message, session: AsyncSession, settings: Settings, state: FSMContext) -> None:
    data = await state.get_data()
    role = data["role"]

    if role == "cleaner":
        service = Service(session)
        cities = await service.list_cities()
        if cities:
            await state.set_state(AdminCreateUserState.city)
            await state.update_data(username=None if message.text.strip() == "-" else message.text.strip())
            await message.answer("Выберите город:", reply_markup=cities_kb([(c.id, c.name) for c in cities], prefix="assign_city"))
            return

    await _save_user(message, session, settings, state, city_id=None)


@router.callback_query(AdminCreateUserState.city, F.data.startswith("assign_city:"))
async def admin_add_cleaner_city(callback: CallbackQuery, session: AsyncSession, settings: Settings, state: FSMContext) -> None:
    city_id = int(callback.data.split(":", 1)[1])
    await _save_user(callback.message, session, settings, state, city_id=city_id)
    await callback.answer()


async def _save_user(message: Message, session: AsyncSession, settings: Settings, state: FSMContext, city_id: int | None) -> None:
    data = await state.get_data()
    role = Role.MANAGER if data["role"] == "manager" else Role.CLEANER

    password = secrets.token_hex(4) if role == Role.MANAGER else None
    password_hash = hash_password(password) if password else None
    username = data.get("username")

    service = Service(session)
    user = await service.create_or_update_user(
        telegram_id=data["telegram_id"],
        username=username,
        full_name=data["full_name"],
        role=role,
        active=(role == Role.CLEANER),
        password_hash=password_hash,
        city_id=city_id,
    )

    await state.clear()
    text = f"Пользователь создан: {user.full_name} ({role.value})"
    if password:
        text += f"\nПароль менеджера: <code>{password}</code>"
    await message.answer(text)

    try:
        if password:
            await message.bot.send_message(
                user.telegram_id,
                f"Вам выдан доступ менеджера. Пароль: <code>{password}</code>\nИспользуйте /login",
            )
        else:
            await message.bot.send_message(user.telegram_id, "Вам назначена роль клинера. Используйте /start")
    except Exception:
        pass


@router.callback_query(F.data == "admin:deactivate_user")
async def admin_deactivate_ask(callback: CallbackQuery, session: AsyncSession, settings: Settings, state: FSMContext) -> None:
    actor = await ensure_actor(session, callback.from_user, settings)
    if actor.role != Role.ADMIN:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    await state.set_state(AdminCreateUserState.telegram_id)
    await state.update_data(role="deactivate")
    await callback.message.answer("Введите Telegram ID для деактивации:")
    await callback.answer()


@router.callback_query(F.data == "admin:settings")
async def admin_settings(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, callback.from_user, settings)
    if actor.role != Role.ADMIN:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    service = Service(session)
    cfg = await service.get_or_create_service_config()
    await callback.message.answer(
        f"⚙️ Настройки\nБазовая цена: {cfg.default_price}\nКомиссия клинера: {cfg.cleaner_commission_percent}%\n"
        "Изменение через команду: /set_config <price> <commission>\n"
        "Добавить город: /add_city <name> [topic_id]"
    )
    await callback.answer()


@router.message(F.text.startswith("/set_config"))
async def set_config(message: Message, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, message.from_user, settings)
    if actor.role != Role.ADMIN:
        await message.answer("Недостаточно прав")
        return

    parts = message.text.strip().split()
    if len(parts) != 3:
        await message.answer("Формат: /set_config <price> <commission>")
        return

    try:
        price = float(parts[1])
        commission = float(parts[2])
    except ValueError:
        await message.answer("Цена и комиссия должны быть числами")
        return

    service = Service(session)
    cfg = await service.update_service_config(default_price=price, commission=commission)
    await message.answer(f"Обновлено: цена={cfg.default_price}, комиссия={cfg.cleaner_commission_percent}%")


@router.message(F.text.startswith("/add_city"))
async def add_city(message: Message, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, message.from_user, settings)
    if actor.role != Role.ADMIN:
        await message.answer("Недостаточно прав")
        return

    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Формат: /add_city <name> [topic_id]")
        return

    name = parts[1]
    topic_id = int(parts[2]) if len(parts) == 3 and parts[2].isdigit() else None
    service = Service(session)
    city = await service.add_city(name=name, topic_id=topic_id)
    await message.answer(f"Город добавлен: {city.name} (topic_id={city.topic_id})")


@router.callback_query(F.data == "admin:finance")
async def admin_finance(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, callback.from_user, settings)
    if actor.role != Role.ADMIN:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    await callback.message.answer(
        "💰 Финансы\n"
        "Подтверждение оплаты клиента: /confirm_payment <order_id>\n"
        "Выплата клинеру: /pay_cleaner <order_id>"
    )
    await callback.answer()


@router.message(F.text.startswith("/confirm_payment"))
async def confirm_payment(message: Message, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, message.from_user, settings)
    if actor.role != Role.ADMIN:
        await message.answer("Недостаточно прав")
        return

    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /confirm_payment <order_id>")
        return

    service = Service(session)
    ok = await service.confirm_client_payment(int(parts[1]))
    await message.answer("Оплата клиента подтверждена ✅" if ok else "Заказ не найден")


@router.message(F.text.startswith("/pay_cleaner"))
async def pay_cleaner(message: Message, session: AsyncSession, settings: Settings) -> None:
    actor = await ensure_actor(session, message.from_user, settings)
    if actor.role != Role.ADMIN:
        await message.answer("Недостаточно прав")
        return

    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /pay_cleaner <order_id>")
        return

    order_id = int(parts[1])
    service = Service(session)
    ok = await service.mark_paid_to_cleaner(order_id)
    if not ok:
        await message.answer("Заказ не найден")
        return

    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order and order.cleaner_id:
        cleaner = await session.get(User, order.cleaner_id)
        if cleaner:
            await message.bot.send_message(cleaner.telegram_id, f"Выплата по заказу #{order_id} выполнена ✅")

    await message.answer("Выплата клинеру отмечена ✅")
