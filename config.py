from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(slots=True)
class Settings:
    bot_token: str
    database_url: str
    admin_ids: List[int]
    support_chat_id: int | None
    default_language: str
    media_dir: Path
    export_dir: Path
    log_level: str



def _parse_admin_ids(raw: str | None) -> List[int]:
    if not raw:
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip()]



def get_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    media_dir = Path(os.getenv("MEDIA_DIR", "data/media")).resolve()
    export_dir = Path(os.getenv("EXPORT_DIR", "exports")).resolve()
    media_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)

    return Settings(
        bot_token=token,
        database_url=database_url,
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS")),
        support_chat_id=int(os.getenv("SUPPORT_CHAT_ID")) if os.getenv("SUPPORT_CHAT_ID") else None,
        default_language=os.getenv("DEFAULT_LANGUAGE", "ru"),
        media_dir=media_dir,
        export_dir=export_dir,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
