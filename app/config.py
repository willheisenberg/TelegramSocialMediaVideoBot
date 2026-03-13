from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    max_download_size_mb: int = 49
    download_dir: str = "/tmp/telegram-social-bot"

    @property
    def max_download_size_bytes(self) -> int:
        return self.max_download_size_mb * 1024 * 1024


def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    max_download_size_mb = int(os.getenv("MAX_DOWNLOAD_SIZE_MB", "49"))
    download_dir = os.getenv("DOWNLOAD_DIR", "/tmp/telegram-social-bot").strip()

    return Settings(
        telegram_bot_token=token,
        max_download_size_mb=max_download_size_mb,
        download_dir=download_dir,
    )
