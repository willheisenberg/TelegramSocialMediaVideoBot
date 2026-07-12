from __future__ import annotations

import logging
import os
from dataclasses import dataclass

LOGGER = logging.getLogger(__name__)

# Harte Obergrenze der Telegram-Bot-API fuer per Upload gesendete Dateien (50 MB).
# Alles darueber quittiert Telegram mit HTTP 413. Da jede heruntergeladene Datei
# anschliessend hochgeladen wird, darf das Download-Limit dieses Maximum nie
# ueberschreiten. Ein Puffer laesst Platz fuer Container-/Multipart-Overhead.
TELEGRAM_UPLOAD_LIMIT_MB = 50


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

    # HTTP client timeouts
    http_connect_timeout: float = 20.0
    http_read_timeout: float = 20.0
    http_write_timeout: float = 20.0
    http_pool_timeout: float = 20.0
    http_media_write_timeout: float = 180.0

    @property
    def max_download_size_bytes(self) -> int:
        return self.max_download_size_mb * 1024 * 1024


def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    max_download_size_mb = int(os.getenv("MAX_DOWNLOAD_SIZE_MB", "49"))
    if max_download_size_mb > TELEGRAM_UPLOAD_LIMIT_MB:
        LOGGER.warning(
            "MAX_DOWNLOAD_SIZE_MB=%d ueberschreitet das Telegram-Upload-Limit (%d MB) "
            "und wird darauf begrenzt, um HTTP-413-Fehler zu vermeiden.",
            max_download_size_mb,
            TELEGRAM_UPLOAD_LIMIT_MB,
        )
        max_download_size_mb = TELEGRAM_UPLOAD_LIMIT_MB
    download_dir = os.getenv("DOWNLOAD_DIR", "/tmp/telegram-social-bot").strip()

    # Cookie-Datei: immer einen Pfad liefern (auch wenn die Datei noch nicht
    # existiert), damit der Bot vom User gesendete Cookies dort anlegen/aktualisieren
    # kann. Verwendet wird sie nur, wenn sie tatsaechlich existiert (siehe Downloader).
    cookies_file_path = os.getenv("COOKIES_FILE_PATH", "").strip()
    if not cookies_file_path:
        cookies_file_path = os.path.join(os.getcwd(), "cookies.txt")

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

    http_connect_timeout = float(os.getenv("HTTP_CONNECT_TIMEOUT", "20.0"))
    http_read_timeout = float(os.getenv("HTTP_READ_TIMEOUT", "20.0"))
    http_write_timeout = float(os.getenv("HTTP_WRITE_TIMEOUT", "20.0"))
    http_pool_timeout = float(os.getenv("HTTP_POOL_TIMEOUT", "20.0"))
    http_media_write_timeout = float(os.getenv("HTTP_MEDIA_WRITE_TIMEOUT", "180.0"))

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
        http_connect_timeout=http_connect_timeout,
        http_read_timeout=http_read_timeout,
        http_write_timeout=http_write_timeout,
        http_pool_timeout=http_pool_timeout,
        http_media_write_timeout=http_media_write_timeout,
    )
