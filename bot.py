from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import get_settings
from database import Database
from handlers import admin_router, cleaner_router, common_router, manager_router
from middlewares import DBSessionMiddleware


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler("logs/bot.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    db = Database(settings)
    await db.create_all()

    dp.update.middleware(DBSessionMiddleware(db))
    dp["settings"] = settings

    dp.include_router(common_router)
    dp.include_router(admin_router)
    dp.include_router(manager_router)
    dp.include_router(cleaner_router)

    try:
        await dp.start_polling(bot)
    finally:
        await db.dispose()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
