from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    max_download_size_mb: int = 49
    download_dir: str = "/tmp/telegram-social-bot"
    cookies_file_path: str | None = None
    extractor_username: str | None = None
    extractor_password: str | None = None
    
    instagram_username: str | None = None
    instagram_password: str | None = None
    youtube_username: str | None = None
    youtube_password: str | None = None
    twitter_username: str | None = None
    twitter_password: str | None = None
    tiktok_username: str | None = None
    tiktok_password: str | None = None

    @property
    def max_download_size_bytes(self) -> int:
        return self.max_download_size_mb * 1024 * 1024


def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    max_download_size_mb = int(os.getenv("MAX_DOWNLOAD_SIZE_MB", "49"))
    download_dir = os.getenv("DOWNLOAD_DIR", "/tmp/telegram-social-bot").strip()

    cookies_file_path = os.getenv("COOKIES_FILE_PATH", "").strip()
    if not cookies_file_path:
        # Fallback to local cookies.txt in workspace root if it exists
        local_cookies = os.path.join(os.getcwd(), "cookies.txt")
        if os.path.exists(local_cookies):
            cookies_file_path = local_cookies
        else:
            cookies_file_path = None

    extractor_username = os.getenv("EXTRACTOR_USERNAME", "").strip() or None
    extractor_password = os.getenv("EXTRACTOR_PASSWORD", "").strip() or None

    instagram_username = os.getenv("INSTAGRAM_USERNAME", "").strip() or None
    instagram_password = os.getenv("INSTAGRAM_PASSWORD", "").strip() or None
    youtube_username = os.getenv("YOUTUBE_USERNAME", "").strip() or None
    youtube_password = os.getenv("YOUTUBE_PASSWORD", "").strip() or None
    twitter_username = os.getenv("TWITTER_USERNAME", "").strip() or None
    twitter_password = os.getenv("TWITTER_PASSWORD", "").strip() or None
    tiktok_username = os.getenv("TIKTOK_USERNAME", "").strip() or None
    tiktok_password = os.getenv("TIKTOK_PASSWORD", "").strip() or None

    return Settings(
        telegram_bot_token=token,
        max_download_size_mb=max_download_size_mb,
        download_dir=download_dir,
        cookies_file_path=cookies_file_path,
        extractor_username=extractor_username,
        extractor_password=extractor_password,
        instagram_username=instagram_username,
        instagram_password=instagram_password,
        youtube_username=youtube_username,
        youtube_password=youtube_password,
        twitter_username=twitter_username,
        twitter_password=twitter_password,
        tiktok_username=tiktok_username,
        tiktok_password=tiktok_password,
    )
