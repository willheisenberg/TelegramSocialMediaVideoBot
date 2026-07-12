from __future__ import annotations

import asyncio
import logging
import re

from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.constants import ChatAction
from telegram.error import NetworkError
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.config import Settings
from app.downloader import (
    DownloaderError,
    VideoDownloader,
    DownloadedImage,
    DownloadedVideo,
    looks_like_auth_error,
    looks_like_cookies,
)

# Obergrenze fuer hochgeladene Cookie-Dateien (grosszuegig; echte cookies.txt sind klein).
MAX_COOKIES_BYTES = 1_000_000

LOGGER = logging.getLogger(__name__)
URL_PATTERN = re.compile(r"https?://\S+")

UPLOAD_MAX_ATTEMPTS = 3
UPLOAD_RETRY_BASE_DELAY = 2.0


def _is_too_large_error(exc: Exception) -> bool:
    """Erkennt den Telegram-Fehler ``413 Request Entity Too Large``.

    Dieser Fehler ist nicht transient (die Datei wird durch Wiederholen nicht
    kleiner), daher darf er weder wiederholt noch als Netzwerkfehler behandelt
    werden.
    """
    message = str(exc).lower()
    return "413" in message or "too large" in message or "entity too large" in message


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
            # 413 ist dauerhaft: nicht wiederholen, sondern direkt weiterreichen.
            if _is_too_large_error(exc) or attempt == UPLOAD_MAX_ATTEMPTS:
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
    application.add_handler(CommandHandler("cookies", cookies_command))
    application.add_handler(
        MessageHandler(filters.Document.ALL, handle_cookies_document)
    )
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
        "die `yt-dlp` verarbeiten kann. Wenn die Datei zu gross ist oder die Plattform blockiert, melde ich das direkt.\n\n"
        "Braucht ein Video einen Login (z.B. private oder altersbeschraenkte Inhalte), kannst du mir mit /cookies "
        "eine cookies.txt hinterlegen."
    )


COOKIES_INSTRUCTIONS = (
    "Manche Videos brauchen einen Login (private, altersbeschraenkte oder regionale Inhalte). "
    "Dafuer kannst du mir deine Cookies hinterlegen:\n\n"
    "1. Installiere eine Browser-Erweiterung wie \"Get cookies.txt LOCALLY\" (Chrome/Firefox).\n"
    "2. Oeffne die Plattform (z.B. TikTok/Instagram) eingeloggt im Browser und exportiere die Cookies "
    "im Netscape-Format (cookies.txt).\n"
    "3. Schick mir diese Datei einfach hier als Dokument – oder fuege den Inhalt als Textnachricht ein.\n\n"
    "Ich speichere die Cookies dauerhaft und nutze sie ab dann fuer alle Downloads."
)


async def cookies_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(COOKIES_INSTRUCTIONS)


async def _store_cookies(update: Update, context: ContextTypes.DEFAULT_TYPE, content: str) -> None:
    """Validiert und speichert vom User gelieferte Cookies, meldet das Ergebnis zurueck."""
    message = update.effective_message
    if not looks_like_cookies(content):
        await message.reply_text(
            "Das sieht nicht nach einer cookies.txt im Netscape-Format aus. "
            "Bitte exportiere die Cookies erneut – /cookies zeigt die Anleitung."
        )
        return
    downloader: VideoDownloader = context.application.bot_data["downloader"]
    try:
        await asyncio.to_thread(downloader.save_cookies, content)
    except DownloaderError as exc:
        LOGGER.warning("Cookies konnten nicht gespeichert werden: %s", exc)
        await message.reply_text("Die Cookies konnten nicht gespeichert werden.")
        return
    LOGGER.info("Cookies aktualisiert (%d Bytes)", len(content.encode("utf-8")))
    await message.reply_text(
        "Cookies gespeichert. Ab jetzt nutze ich sie fuer Downloads – "
        "schick den Link einfach nochmal."
    )


async def handle_cookies_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    document = message.document if message else None
    if document is None:
        return
    if document.file_size and document.file_size > MAX_COOKIES_BYTES:
        await message.reply_text("Diese Datei ist zu gross fuer eine cookies.txt.")
        return
    tg_file = await document.get_file()
    raw = await tg_file.download_as_bytearray()
    content = bytes(raw).decode("utf-8", errors="replace")
    await _store_cookies(update, context, content)


async def handle_video_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return

    # Eingefuegte Cookies (Netscape-Format) direkt speichern statt als Link behandeln.
    if looks_like_cookies(message.text):
        await _store_cookies(update, context, message.text)
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
        text = f"Download fehlgeschlagen: {exc}"
        if looks_like_auth_error(str(exc)):
            text += (
                "\n\nDieses Video braucht offenbar einen Login. Hinterlege mir mit "
                "/cookies eine cookies.txt, dann kann ich es laden."
            )
        await status_message.edit_text(text)
    except NetworkError as exc:
        if _is_too_large_error(exc):
            LOGGER.warning("Upload too large for %s: %s", url, exc)
            await status_message.edit_text(
                "Das Video ist zu gross fuer den Telegram-Upload (max. 50 MB) "
                "und konnte nicht gesendet werden."
            )
        else:
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
