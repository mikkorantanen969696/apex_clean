from __future__ import annotations

from aiogram.types import User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from database.models import Role, User
from services import Service


async def ensure_actor(session: AsyncSession, tg_user: TgUser, settings: Settings) -> User:
    service = Service(session)
    user = await service.upsert_telegram_user(
        telegram_id=tg_user.id,
        username=tg_user.username,
        full_name=tg_user.full_name,
    )

    if tg_user.id in settings.admin_ids and user.role != Role.ADMIN:
        user = await service.create_or_update_user(
            telegram_id=tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name,
            role=Role.ADMIN,
            active=True,
        )
    return user


def role_label(role: Role) -> str:
    return {
        Role.ADMIN: "admin",
        Role.MANAGER: "manager",
        Role.CLEANER: "cleaner",
    }[role]
