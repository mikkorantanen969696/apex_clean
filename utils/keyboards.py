from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


ROLE_LABELS = {
    "admin": "Администратор",
    "manager": "Менеджер",
    "cleaner": "Клинер",
}


def main_menu(role: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if role == "admin":
        kb.button(text="👥 Пользователи", callback_data="admin:users")
        kb.button(text="🧾 Создать заявку", callback_data="manager:create_order")
        kb.button(text="📊 Статистика", callback_data="stats:admin")
        kb.button(text="💰 Финансы", callback_data="admin:finance")
        kb.button(text="⚙️ Настройки", callback_data="admin:settings")
    elif role == "manager":
        kb.button(text="🧾 Новая заявка", callback_data="manager:create_order")
        kb.button(text="📦 Мои заказы", callback_data="manager:orders")
        kb.button(text="📊 Моя статистика", callback_data="stats:manager")
        kb.button(text="💳 Счёт PDF + QR", callback_data="manager:invoice")
    else:
        kb.button(text="🆕 Заявки в моем городе", callback_data="cleaner:new_orders")
        kb.button(text="💼 Мои реквизиты", callback_data="cleaner:payment")
    kb.adjust(2)
    return kb.as_markup()


def cities_kb(cities: list[tuple[int, str]], prefix: str = "city") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for city_id, name in cities:
        kb.button(text=f"🏙️ {name}", callback_data=f"{prefix}:{city_id}")
    kb.adjust(1)
    return kb.as_markup()


def confirm_kb(ok: str, cancel: str = "cancel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=ok),
                InlineKeyboardButton(text="❌ Отмена", callback_data=cancel),
            ]
        ]
    )


def order_actions_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧹 Взять заказ", callback_data=f"order_take:{order_id}")],
            [InlineKeyboardButton(text="💬 Чат с менеджером", callback_data=f"chat_manager:{order_id}")],
        ]
    )


def admin_users_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить менеджера", callback_data="admin:add_manager")],
            [InlineKeyboardButton(text="➕ Добавить клинера", callback_data="admin:add_cleaner")],
            [InlineKeyboardButton(text="➖ Деактивировать", callback_data="admin:deactivate_user")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")],
        ]
    )


def stats_export_kb(scope: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 CSV", callback_data=f"export:{scope}:csv")],
            [InlineKeyboardButton(text="📗 XLSX", callback_data=f"export:{scope}:xlsx")],
            [InlineKeyboardButton(text="📕 PDF", callback_data=f"export:{scope}:pdf")],
        ]
    )


def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
            ]
        ]
    )
