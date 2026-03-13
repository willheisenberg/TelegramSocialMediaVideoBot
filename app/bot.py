from __future__ import annotations

import logging
import re

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.config import Settings
from app.downloader import DownloaderError, VideoDownloader

LOGGER = logging.getLogger(__name__)
URL_PATTERN = re.compile(r"https?://\S+")


def build_application(settings: Settings) -> Application:
    downloader = VideoDownloader(
        download_dir=settings.download_dir,
        max_download_size_bytes=settings.max_download_size_bytes,
    )

    application = Application.builder().token(settings.telegram_bot_token).build()
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
        "Schick mir einen Videolink. Ich lade das Video herunter und sende es dir direkt im Chat zurueck."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Unterstuetzt werden Links von Plattformen, die `yt-dlp` verarbeiten kann. "
        "Wenn das Video zu gross ist oder die Plattform blockiert, melde ich das direkt."
    )


async def handle_video_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return

    match = URL_PATTERN.search(message.text)
    if not match:
        await message.reply_text("Ich habe keinen gueltigen Link gefunden.")
        return

    url = match.group(0)
    downloader: VideoDownloader = context.application.bot_data["downloader"]

    status_message = await message.reply_text("Download gestartet...")
    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.UPLOAD_VIDEO)

    try:
        video = await downloader.download(url)
        caption_parts = [video.title]
        if video.uploader:
            caption_parts.append(f"Quelle: {video.uploader}")
        caption = "\n".join(caption_parts)

        with video.file_path.open("rb") as file_handle:
            await message.reply_video(
                video=file_handle,
                caption=caption[:1024],
                supports_streaming=True,
            )
        await status_message.edit_text("Fertig.")
    except DownloaderError as exc:
        LOGGER.warning("Downloader error for %s: %s", url, exc)
        await status_message.edit_text(f"Download fehlgeschlagen: {exc}")
    finally:
        if "video" in locals():
            downloader.cleanup(video.file_path)


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.exception("Unhandled exception while processing Telegram update", exc_info=context.error)
