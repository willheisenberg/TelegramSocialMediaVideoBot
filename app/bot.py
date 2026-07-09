from __future__ import annotations

import asyncio
import logging
import re

from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.constants import ChatAction
from telegram.error import NetworkError
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.config import Settings
from app.downloader import DownloaderError, VideoDownloader, DownloadedImage, DownloadedVideo

LOGGER = logging.getLogger(__name__)
URL_PATTERN = re.compile(r"https?://\S+")

UPLOAD_MAX_ATTEMPTS = 3
UPLOAD_RETRY_BASE_DELAY = 2.0


async def _upload_with_retry(send_coro_factory):
    """Fuehrt einen Upload aus und wiederholt ihn bei transienten Netzwerkfehlern.

    ``send_coro_factory`` muss bei jedem Aufruf eine frische Coroutine liefern und
    die Datei-Handles selbst neu oeffnen, damit der Lesezeiger nach einem
    Fehlversuch wieder am Dateianfang steht.
    """
    for attempt in range(1, UPLOAD_MAX_ATTEMPTS + 1):
        try:
            await send_coro_factory()
            return
        except NetworkError as exc:
            if attempt == UPLOAD_MAX_ATTEMPTS:
                raise
            LOGGER.warning(
                "Upload-Versuch %d/%d fehlgeschlagen (%s), neuer Versuch...",
                attempt,
                UPLOAD_MAX_ATTEMPTS,
                exc,
            )
            await asyncio.sleep(UPLOAD_RETRY_BASE_DELAY * attempt)


def build_application(settings: Settings) -> Application:
    downloader = VideoDownloader(
        download_dir=settings.download_dir,
        max_download_size_bytes=settings.max_download_size_bytes,
        cookies_file_path=settings.cookies_file_path,
        extractor_username=settings.extractor_username,
        extractor_password=settings.extractor_password,
        instagram_username=settings.instagram_username,
        instagram_password=settings.instagram_password,
        youtube_username=settings.youtube_username,
        youtube_password=settings.youtube_password,
        twitter_username=settings.twitter_username,
        twitter_password=settings.twitter_password,
        tiktok_username=settings.tiktok_username,
        tiktok_password=settings.tiktok_password,
    )

    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .connect_timeout(settings.http_connect_timeout)
        .read_timeout(settings.http_read_timeout)
        .write_timeout(settings.http_write_timeout)
        .pool_timeout(settings.http_pool_timeout)
        .media_write_timeout(settings.http_media_write_timeout)
        .build()
    )
    application.bot_data["downloader"] = downloader
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_link)
    )
    application.add_error_handler(handle_error)
    return application


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Schick mir einen Video- oder Bildlink. Ich lade das Medium herunter und sende es dir direkt im Chat zurueck."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Unterstuetzt werden Direktlinks zu Bildern (JPEG, PNG, WEBP, GIF) sowie Video-Links von Plattformen, "
        "die `yt-dlp` verarbeiten kann. Wenn die Datei zu gross ist oder die Plattform blockiert, melde ich das direkt."
    )


async def handle_video_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return

    match = URL_PATTERN.search(message.text)
    if not match:
        return

    url = match.group(0)
    downloader: VideoDownloader = context.application.bot_data["downloader"]

    status_message = await message.reply_text("Download gestartet...")

    # Determine chat action based on whether it is an image or video
    is_image, is_gif = await asyncio.to_thread(downloader._check_if_image, url)
    if is_image:
        action = ChatAction.UPLOAD_VIDEO if is_gif else ChatAction.UPLOAD_PHOTO
    else:
        action = ChatAction.UPLOAD_VIDEO

    await context.bot.send_chat_action(chat_id=message.chat_id, action=action)

    try:
        media = await downloader.download(url)
        if isinstance(media, list):
            # Send all downloaded items as a native Telegram Media Group (Album).
            # Die Datei-Handles werden bei jedem Versuch neu geoeffnet, damit ein
            # Retry nach einem Netzwerkfehler die Dateien von vorne liest.
            async def _send_media_group() -> None:
                files = []
                media_group = []
                try:
                    for idx, item in enumerate(media):
                        f = item.file_path.open("rb")
                        files.append(f)

                        caption = ""
                        if idx == 0:
                            caption_parts = [item.title]
                            if item.uploader:
                                caption_parts.append(f"Quelle: {item.uploader}")
                            caption = "\n".join(caption_parts)[:1024]

                        if isinstance(item, DownloadedImage):
                            media_group.append(InputMediaPhoto(media=f, caption=caption))
                        elif isinstance(item, DownloadedVideo):
                            media_group.append(InputMediaVideo(media=f, caption=caption))

                    await message.reply_media_group(media=media_group)
                finally:
                    for f in files:
                        f.close()

            await _upload_with_retry(_send_media_group)
            await status_message.edit_text("Fertig.")
        elif isinstance(media, DownloadedImage):
            caption_parts = [media.title]
            if media.uploader:
                caption_parts.append(f"Quelle: {media.uploader}")
            caption = "\n".join(caption_parts)[:1024]

            async def _send_image() -> None:
                with media.file_path.open("rb") as file_handle:
                    if media.is_gif:
                        await message.reply_animation(
                            animation=file_handle,
                            caption=caption,
                        )
                    else:
                        await message.reply_photo(
                            photo=file_handle,
                            caption=caption,
                        )

            await _upload_with_retry(_send_image)
            await status_message.edit_text("Fertig.")
        else:
            caption_parts = [media.title]
            if media.uploader:
                caption_parts.append(f"Quelle: {media.uploader}")
            caption = "\n".join(caption_parts)

            async def _send_video() -> None:
                with media.file_path.open("rb") as file_handle:
                    await message.reply_video(
                        video=file_handle,
                        caption=caption[:1024],
                        supports_streaming=True,
                    )

            await _upload_with_retry(_send_video)
            await status_message.edit_text("Fertig.")
    except DownloaderError as exc:
        LOGGER.warning("Downloader error for %s: %s", url, exc)
        await status_message.edit_text(f"Download fehlgeschlagen: {exc}")
    except NetworkError as exc:
        LOGGER.warning("Network error while uploading %s: %s", url, exc)
        await status_message.edit_text(
            "Der Upload zu Telegram ist an einem Netzwerkfehler gescheitert. "
            "Bitte versuch es gleich noch einmal."
        )
    finally:
        if "media" in locals():
            if isinstance(media, list):
                for item in media:
                    downloader.cleanup(item.file_path)
            else:
                downloader.cleanup(media.file_path)


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.exception("Unhandled exception while processing Telegram update", exc_info=context.error)
